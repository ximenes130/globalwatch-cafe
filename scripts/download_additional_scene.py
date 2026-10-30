"""Baixa a cena adicional da estação chuvosa no mesmo formato do kit (T3.1, T3.2).

Busca no Earth Search as cenas do mesmo tile MGRS do kit (23KLS) entre
dezembro e março, mede a fração de pixels com problema de aquisição na SCL
**dentro do recorte do kit** e escolhe a menor (desempate pela nuvem da cena). Depois lê as
bandas B02, B03, B04 e B08 e a SCL só na janela do kit, sem reamostrar, e grava
em `data/adicional/<item_id>/` os mesmos arquivos do kit: imagem, SCL,
atribuição, metadados, item STAC e SHA256.

Antes de gravar, confere que a cena está no CRS do kit e que a janela cai em
pixels inteiros da grade dela (R3.5). Depois de gravar, reabre a imagem com o
leitor do backend: se a app não aceitar o arquivo, o erro aparece aqui.

Uso (da raiz do repositório; padrão: dez/2025 a mar/2026):
    backend/.venv/bin/python scripts/download_additional_scene.py
    backend/.venv/bin/python scripts/download_additional_scene.py --start 2024-12-01 \\
        --end 2025-03-31
    backend/.venv/bin/python scripts/download_additional_scene.py --item <id do item STAC>
"""

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import urllib.request
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine
from rasterio.windows import Window, from_bounds

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.processing.params import SCL_EXCLUDE  # noqa: E402
from app.processing.reader import read_image  # noqa: E402

KIT = ROOT / "data" / "exemplo"
OUT = ROOT / "data" / "adicional"

STAC = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-c1-l2a"
TILE = "MGRS-23KLS"
WET_MONTHS = {12, 1, 2, 3}
# Problemas de aquisição: as classes que a app exclui menos a água (6). A água
# também sai da análise, mas é cobertura do solo e está nas duas datas; contá-la
# deixaria um açude decidir entre duas cenas sem nuvem.
SCENE_PROBLEMS = tuple(code for code in SCL_EXCLUDE if code != 6)

# Chave do asset no Earth Search → descrição da banda no kit (o leitor da app
# acha a ordem por estas descrições).
BANDS = {"blue": "B02_blue", "green": "B03_green", "red": "B04_red", "nir": "B08_nir"}
FILES = [
    "imagem_multiespectral.tif",
    "qualidade_scl.tif",
    "ATRIBUICAO.txt",
    "metadados.json",
    "fonte_stac.json",
]
# Os COGs são públicos; sem isto o GDAL lista o bucket a cada abertura.
GDAL_ENV = {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "AWS_NO_SIGN_REQUEST": "YES"}


class SceneError(Exception):
    """Cena que não serve para o recorte do kit; nada é gravado."""


def stac_json(url: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def search(start: date, end: date) -> list[dict]:
    """Todas as cenas do tile no intervalo, seguindo a paginação do STAC."""
    body = {
        "collections": [COLLECTION],
        "datetime": f"{start.isoformat()}T00:00:00Z/{end.isoformat()}T23:59:59Z",
        "query": {"grid:code": {"eq": TILE}},
        "limit": 100,
    }
    url, items = f"{STAC}/search", []
    while url:
        page = stac_json(url, body)
        items += page["features"]
        following = next((link for link in page.get("links", []) if link["rel"] == "next"), None)
        url = following["href"] if following else None
        # O Earth Search manda o corpo da próxima página no próprio link (POST).
        body = following.get("body") if following and following.get("method") == "POST" else None
    return items


def get_item(item_id: str) -> dict:
    return stac_json(f"{STAC}/collections/{COLLECTION}/items/{item_id}")


def kit_grid() -> dict:
    with rasterio.open(KIT / "imagem_multiespectral.tif") as ds:
        return ds.profile


def window_on(ds, grid) -> Window:
    """Janela do recorte do kit na grade da cena; recusa o que exigiria reamostrar (R3.5)."""
    if ds.crs != grid["crs"]:
        raise SceneError(f"CRS da cena ({ds.crs}) diferente do kit ({grid['crs']}).")
    left, top = grid["transform"].c, grid["transform"].f
    right = left + grid["width"] * grid["transform"].a
    bottom = top + grid["height"] * grid["transform"].e
    window = from_bounds(left, bottom, right, top, transform=ds.transform)
    edges = [window.col_off, window.row_off, window.width, window.height]
    if any(abs(value - round(value)) > 1e-6 for value in edges):
        raise SceneError("O recorte não cai em pixels inteiros da cena; seria preciso reamostrar.")
    window = Window(*(round(value) for value in edges))
    inside = (
        window.col_off >= 0
        and window.row_off >= 0
        and window.col_off + window.width <= ds.width
        and window.row_off + window.height <= ds.height
    )
    if not inside:
        raise SceneError("O recorte do kit fica fora desta cena.")
    return window


def read_window(href: str, grid) -> tuple[np.ndarray, Window]:
    with rasterio.Env(**GDAL_ENV), rasterio.open(href) as ds:
        window = window_on(ds, grid)
        return ds.read(1, window=window), window


def problem_fraction(item: dict, grid) -> float:
    """Fração da SCL no recorte com problema de aquisição (sem dado conta como problema)."""
    scl, _ = read_window(item["assets"]["scl"]["href"], grid)
    return float(np.isin(scl, SCENE_PROBLEMS).mean())


def rank(items: list[dict], grid) -> list[dict]:
    """Candidatas da estação chuvosa, da melhor para a pior (R3.1)."""
    rows = []
    for item in items:
        if datetime.fromisoformat(item["properties"]["datetime"]).month not in WET_MONTHS:
            continue
        try:
            fraction = problem_fraction(item, grid)
        except SceneError as exc:
            print(f"  {item['id']}: descartada ({exc})")
            continue
        rows.append(
            {
                "item": item["id"],
                "problem_fraction": round(fraction, 4),
                "cloud_cover": item["properties"]["eo:cloud_cover"],
            }
        )
    return sorted(rows, key=lambda row: (row["problem_fraction"], row["cloud_cover"]))


def radiometry(asset: dict) -> tuple[float, float]:
    """Scale/offset do item STAC, não fixos: o offset muda com o processing baseline (R3.3)."""
    band = asset["raster:bands"][0]
    return band["scale"], band["offset"]


def read_scene(item: dict, grid) -> dict:
    """Lê tudo antes de gravar qualquer arquivo: se algo falhar, não sobra pasta pela metade."""
    bands, scales, offsets, sources = [], [], [], []
    for key in BANDS:
        asset = item["assets"][key]
        data, _ = read_window(asset["href"], grid)
        bands.append(data)
        scale, offset = radiometry(asset)
        scales.append(scale)
        offsets.append(offset)
        sources.append(asset["href"])
    # A SCL tem 20 m: mesma origem, pixel do dobro do tamanho, metade das linhas.
    scl_grid = {
        **grid,
        "width": grid["width"] // 2,
        "height": grid["height"] // 2,
        "transform": grid["transform"] * Affine.scale(2),
    }
    scl, _ = read_window(item["assets"]["scl"]["href"], scl_grid)
    return {
        "bands": np.stack(bands).astype(np.uint16),
        "scales": scales,
        "offsets": offsets,
        "sources": sources,
        "scl": scl.astype(np.uint8),
        "scl_grid": scl_grid,
    }


def write_image(path: Path, scene: dict, item: dict, grid) -> None:
    acquired = item["properties"]["datetime"]
    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "nodata": 0,
        "width": grid["width"],
        "height": grid["height"],
        "count": len(BANDS),
        "crs": grid["crs"],
        "transform": grid["transform"],
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
        "compress": "deflate",
        "interleave": "pixel",
    }
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(scene["bands"])
        ds.descriptions = tuple(BANDS.values())
        ds.scales = scene["scales"]
        ds.offsets = scene["offsets"]
        ds.update_tags(
            ACQUISITION_UTC=acquired,
            ATTRIBUTION=f"Contains modified Copernicus Sentinel data ({acquired[:4]})",
            MODIFICATION="Spatial crop and four-band stack; original DN preserved",
            SOURCE_ITEM=item["id"],
        )


def write_scl(path: Path, scene: dict, grid) -> None:
    scl_grid = scene["scl_grid"]
    profile = {
        "driver": "GTiff",
        "dtype": "uint8",
        "nodata": 0,
        "width": scl_grid["width"],
        "height": scl_grid["height"],
        "count": 1,
        "crs": grid["crs"],
        "transform": scl_grid["transform"],
        "compress": "deflate",
    }
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(scene["scl"], 1)
        ds.descriptions = ("Sentinel-2_SCL_20m",)


def license_url() -> str:
    collection = stac_json(f"{STAC}/collections/{COLLECTION}")
    return next(link["href"] for link in collection["links"] if link["rel"] == "license")


def attribution_text(item: dict, accessed: date, terms: str) -> str:
    acquired = item["properties"]["datetime"]
    year = acquired[:4]
    return f"""PROCEDÊNCIA DOS DADOS

Contains modified Copernicus Sentinel data ({year}).
Modificações feitas por scripts/download_additional_scene.py: recorte espacial
na grade do kit do desafio e empilhamento das bandas B02, B03, B04 e B08;
recorte da SCL sem mudança de resolução. Nenhuma reamostragem.
Nenhuma classificação de café foi adicionada.

Cena: {item["id"]}.
Aquisição: {acquired}.
Catálogo: Earth Search, Element 84, {COLLECTION}.
Acessado em {accessed.strftime("%d/%m/%Y")}:
{STAC}/collections/{COLLECTION}/items/{item["id"]}

Sentinel-2 Cloud-Optimized GeoTIFFs was accessed on {accessed.isoformat()} from:
https://registry.opendata.aws/sentinel-2-l2a-cogs/

Termos de dados Sentinel indicados pela coleção de origem:
{terms}

O aviso de atribuição e os termos de origem devem acompanhar os dados ao
redistribuir este recorte.
"""


def metadata(item: dict, scene: dict, grid, accessed: date, area_ha: float, ranking) -> dict:
    """Mesma estrutura do `metadados.json` do kit, mais a tabela da escolha da cena."""
    scl_asset = item["assets"]["scl"]["href"]
    return {
        "versao": "1.0",
        "gerado_em": accessed.isoformat(),
        "item": item["id"],
        "fonte_stac": f"{STAC}/collections/{COLLECTION}/items/{item['id']}",
        "aquisicao_utc": item["properties"]["datetime"],
        "crs": grid["crs"].to_string(),
        "shape": list(scene["bands"].shape),
        "resolucao_m": grid["transform"].a,
        "area_total_recorte_ha": area_ha,
        "nodata": 0,
        "armazenamento": "DN original; reflectancia = DN * scale + offset, exceto nodata",
        "bandas": [
            {
                "indice": index,
                "banda": description.split("_")[0],
                "nome": description.split("_")[1],
                "scale": scale,
                "offset": offset,
                "fonte": source,
            }
            for index, (description, scale, offset, source) in enumerate(
                zip(
                    BANDS.values(), scene["scales"], scene["offsets"], scene["sources"], strict=True
                ),
                start=1,
            )
        ],
        "scl": {
            "arquivo": "qualidade_scl.tif",
            "resolucao_m": scene["scl_grid"]["transform"].a,
            "nota": "Classificação de cena/qualidade do Sentinel-2, não classificação de café.",
            "fonte": scl_asset,
        },
        "alteracoes": [
            "Recorte espacial sem reamostragem, na grade do kit do desafio",
            "Empilhamento das quatro bandas nativas de 10 m",
            "Metadados radiométricos lidos do item STAC (raster:bands)",
            "SCL mantida na resolução nativa de 20 m",
        ],
        "selecao": {
            "criterio": "menor fração de pixels com problema de aquisição na SCL no recorte; "
            "desempate por eo:cloud_cover da cena",
            "classes_com_problema": list(SCENE_PROBLEMS),
            "candidatas": ranking,
        },
        "rotulos_cafe": None,
        "nota": "Imagem real de uma região produtora; presença e limites de cafezais neste "
        "recorte não foram verificados em campo.",
    }


def check_written(folder: Path, grid) -> float:
    """Reabre os arquivos como a app abriria; devolve a área total do recorte em ha."""
    with rasterio.open(folder / "imagem_multiespectral.tif") as ds:
        same_grid = ds.crs == grid["crs"] and ds.transform == grid["transform"]
        same_shape = (ds.count, ds.height, ds.width) == (4, grid["height"], grid["width"])
        if not (same_grid and same_shape):
            raise SceneError("A imagem gravada não tem a grade do kit.")
    with rasterio.open(folder / "qualidade_scl.tif") as ds:
        if (ds.height, ds.width) != (grid["height"] // 2, grid["width"] // 2):
            raise SceneError("A SCL gravada não tem metade da grade do kit.")
    image = read_image((folder / "imagem_multiespectral.tif").read_bytes())
    if image.bands.source != "descriptions" or image.radiometry.source != "file_tags":
        raise SceneError("O leitor da app não achou as bandas ou a radiometria nas tags.")
    return round(image.valid.size * image.pixel_area_ha, 2)


def sha256sums(folder: Path) -> str:
    lines = [
        f"{hashlib.sha256((folder / name).read_bytes()).hexdigest()}  {name}"
        for name in sorted(FILES)
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--start", type=date.fromisoformat, default=date(2025, 12, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2026, 3, 31))
    parser.add_argument("--item", help="fixa a cena em vez de escolher pela SCL")
    args = parser.parse_args()

    grid = kit_grid()
    accessed = datetime.now(UTC).date()

    if args.item:
        item = get_item(args.item)
        ranking = [
            {
                "item": item["id"],
                "problem_fraction": round(problem_fraction(item, grid), 4),
                "cloud_cover": item["properties"]["eo:cloud_cover"],
            }
        ]
    else:
        items = search(args.start, args.end)
        print(f"{len(items)} cenas do tile {TILE} entre {args.start} e {args.end}")
        ranking = rank(items, grid)
        if not ranking:
            raise SceneError("Nenhuma cena da estação chuvosa cobre o recorte.")
        item = next(i for i in items if i["id"] == ranking[0]["item"])

    print("problema no recorte | nuvem da cena | cena")
    for row in ranking:
        print(f"  {row['problem_fraction']:>7.2%} | {row['cloud_cover']:6.2f}% | {row['item']}")
    print(f"escolhida: {item['id']}")

    scene = read_scene(item, grid)
    target = OUT / item["id"]
    # Grava numa pasta temporária ao lado e só troca no fim: falha não deixa meia saída.
    OUT.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(dir=OUT, prefix=".parcial-"))
    try:
        write_image(folder / "imagem_multiespectral.tif", scene, item, grid)
        write_scl(folder / "qualidade_scl.tif", scene, grid)
        area_ha = check_written(folder, grid)
        (folder / "ATRIBUICAO.txt").write_text(attribution_text(item, accessed, license_url()))
        meta = metadata(item, scene, grid, accessed, area_ha, ranking)
        (folder / "metadados.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
        (folder / "fonte_stac.json").write_text(json.dumps(item, ensure_ascii=False, indent=2))
        (folder / "SHA256SUMS.txt").write_text(sha256sums(folder))
    except BaseException:
        shutil.rmtree(folder)
        raise
    if target.exists():
        shutil.rmtree(target)
    folder.rename(target)

    print(f"gravado em {target.relative_to(ROOT)} (área total do recorte: {area_ha} ha)")


if __name__ == "__main__":
    try:
        main()
    except SceneError as exc:
        sys.exit(f"erro: {exc}")
