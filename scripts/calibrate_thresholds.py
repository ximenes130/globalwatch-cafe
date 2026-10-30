"""Calibração dos limiares de NDVI (e decisão sobre o GNDVI) com o kit (T2.5).

Gera em `docs/evidencias/calibracao/`:
- `histogramas.png`: NDVI e GNDVI dos pixels válidos, com os limiares, e a
  densidade NDVI x GNDVI (mostra se o GNDVI separa algo que o NDVI não separa);
- `rgb.jpg`: composição de cor verdadeira realçada (p2–p98);
- `mascara-<rotulo>.jpg`: RGB ao lado do RGB com as faixas de NDVI sobrepostas;
- `resumo-<rotulo>.txt`: hectares por faixa e fração de candidato em amostras
  de mata e de talhões, delimitadas por inspeção visual do RGB;
- com `--mapbiomas`, `mapbiomas-<rotulo>.jpg` e uma tabela no resumo: classes do
  MapBiomas 2024 no recorte, fração de candidato e NDVI em cada uma.

O MapBiomas é **conferência**, não alvo: os limiares não são ajustados para
concordar com ele, senão a comparação da spec 007 deixa de ser independente.
Ele tem 30 m (Landsat), é de 2024 e tem erros próprios; não é gabarito.

Usa o mesmo leitor, índices e máscara do backend, para a calibração ver
exatamente o que o pipeline vai ver. Ainda sem morfologia (T2.6): aqui só
importam as faixas de NDVI.

Uso (da raiz do repositório):
    backend/.venv/bin/python scripts/calibrate_thresholds.py --label inicial
    backend/.venv/bin/python scripts/calibrate_thresholds.py --ndvi-min 0.6 --label ajuste
    backend/.venv/bin/python scripts/calibrate_thresholds.py --label final --mapbiomas
"""

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from rasterio.warp import Resampling, reproject, transform_bounds  # noqa: E402
from rasterio.windows import Window, from_bounds  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.processing.classification import classify  # noqa: E402
from app.processing.indices import ndvi, normalized_difference  # noqa: E402
from app.processing.masking import quality_mask  # noqa: E402
from app.processing.params import Params  # noqa: E402
from app.processing.reader import read_image  # noqa: E402

KIT = ROOT / "data" / "exemplo"
OUT = ROOT / "docs" / "evidencias" / "calibracao"

# Cores da identidade do front (frontend/src/index.css).
CHERRY = (0xB3 / 255, 0x12 / 255, 0x2E / 255)
CANOPY = (0x1E / 255, 0x4A / 255, 0x2A / 255)
STRAW = (0xD8 / 255, 0xC2 / 255, 0x7A / 255)
INK_RGB = (0x14 / 255, 0x20 / 255, 0x1A / 255)

# Amostras (linha inicial, linha final, coluna inicial, coluna final) escolhidas
# olhando o RGB. Interpretação visual, não verdade de campo: o kit não tem
# rótulos. "Talhões" são áreas em curva de nível com aparência de café; servem
# para comparar limiares, não para medir acerto.
SAMPLES = {
    "mata (núcleo)": (180, 240, 380, 450),
    "mata (sudoeste, mais clara)": (240, 270, 345, 400),
    "mata (fragmento)": (380, 420, 200, 240),
    "talhões A": (320, 350, 300, 340),
    "talhões B": (365, 390, 265, 320),
}

# MapBiomas Brasil, Coleção 10, ano 2024: cópia em COG no Source Cooperative
# (hospedagem; o produtor é o MapBiomas). Só a janela do recorte é baixada.
MAPBIOMAS_URL = (
    "https://data.source.coop/tristangruppwri/mapbiomas/mapbiomas-brazil/"
    "mapbiomas_brazil_2024/mapbiomas_brazil_2024.tif"
)
MAPBIOMAS_ATTRIBUTION = (
    "Projeto MapBiomas – Coleção 10 da Série Anual de Mapas de Cobertura e Uso da Terra "
    "do Brasil, ano 2024, acessado em 30/10/2026 (CC BY 4.0) através de " + MAPBIOMAS_URL
)
# Nomes da legenda da Coleção 10 para as classes que aparecem no recorte.
MAPBIOMAS_CLASSES = {
    3: "Formação Florestal",
    9: "Silvicultura",
    15: "Pastagem",
    20: "Cana",
    21: "Mosaico de Usos",
    24: "Área Urbanizada",
    25: "Outras Áreas não Vegetadas",
    33: "Rio, Lago e Oceano",
    41: "Outras Lavouras Temporárias",
    46: "Café",
    48: "Outras Lavouras Perenes",
}
MAPBIOMAS_COFFEE, MAPBIOMAS_FOREST, MAPBIOMAS_MOSAIC = 46, 3, 21
LILAC = (0xD6 / 255, 0x8F / 255, 0xE2 / 255)  # cor do café na legenda do MapBiomas
YELLOW = (1.0, 0.9, 0.4)


def read_mapbiomas(image) -> np.ndarray:
    """Classes do MapBiomas 2024 na grade do kit (vizinho mais próximo: dado categórico)."""
    height, width = image.shape
    bounds = rasterio.transform.array_bounds(height, width, image.transform)
    west, south, east, north = transform_bounds(image.crs, "EPSG:4326", *bounds)
    classes = np.zeros(image.shape, dtype=np.uint8)
    # Sem listar o diretório remoto a cada abertura (só o arquivo interessa).
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        with rasterio.open("/vsicurl/" + MAPBIOMAS_URL) as ds:
            win = from_bounds(west, south, east, north, ds.transform)
            win = win.round_offsets().round_lengths()
            # Margem de 2 pixels para a reprojeção não deixar bordas sem dado.
            win = Window(win.col_off - 2, win.row_off - 2, win.width + 4, win.height + 4)
            reproject(
                ds.read(1, window=win),
                classes,
                src_transform=ds.window_transform(win),
                src_crs=ds.crs,
                src_nodata=0,
                dst_transform=image.transform,
                dst_crs=image.crs,
                dst_nodata=0,
                resampling=Resampling.nearest,
            )
    return classes


def stretch(band: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Realce linear p2–p98 para 0–1."""
    low, high = np.nanpercentile(band[valid], [2, 98])
    return np.clip((band - low) / (high - low), 0, 1)


def true_color(image) -> np.ndarray:
    rgb = np.dstack([stretch(b, image.valid) for b in (image.red, image.green, image.blue)])
    return np.nan_to_num(rgb)


def overlay(rgb: np.ndarray, layers: list[tuple[np.ndarray, tuple, float]]) -> np.ndarray:
    out = rgb.copy()
    for mask, color, alpha in layers:
        out[mask] = (1 - alpha) * out[mask] + alpha * np.array(color)
    return out


def main() -> None:
    defaults = Params()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ndvi-min", type=float, default=defaults.ndvi_min)
    parser.add_argument("--ndvi-max", type=float, default=defaults.ndvi_max)
    parser.add_argument("--gndvi-min", type=float, default=None)
    parser.add_argument(
        "--red-min",
        type=float,
        default=None,
        help="exploratório: exige reflectância no vermelho >= valor (dossel escuro sai)",
    )
    parser.add_argument("--label", default="inicial", help="sufixo do arquivo da máscara")
    parser.add_argument(
        "--mapbiomas", action="store_true", help="cruza com o MapBiomas 2024 (requer internet)"
    )
    args = parser.parse_args()

    image = read_image((KIT / "imagem_multiespectral.tif").read_bytes())
    params = Params(ndvi_min=args.ndvi_min, ndvi_max=args.ndvi_max, gndvi_min=args.gndvi_min)
    quality = quality_mask(image, params, (KIT / "qualidade_scl.tif").read_bytes())
    usable = image.valid & ~quality.excluded

    nd = ndvi(image.red, image.nir, image.valid)
    gn = normalized_difference(image.nir, image.green, image.valid)
    pixel_ha = abs(image.transform.a * image.transform.e) / 10_000

    low = usable & (nd < params.ndvi_min)
    dense = usable & (nd > params.ndvi_max)
    candidate = usable & ~low & ~dense
    dark = np.zeros_like(candidate)
    if args.red_min is not None:
        dark = candidate & (image.red < args.red_min)
        candidate &= ~dark
    low_chlorophyll = np.zeros_like(candidate)
    if params.gndvi_min is not None:
        low_chlorophyll = candidate & (gn < params.gndvi_min)
        candidate &= ~low_chlorophyll

    OUT.mkdir(parents=True, exist_ok=True)
    rgb = true_color(image)
    plt.imsave(OUT / "rgb.jpg", np.kron(rgb, np.ones((2, 2, 1))), pil_kwargs={"quality": 88})

    # Histogramas e densidade NDVI x GNDVI.
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5), constrained_layout=True)
    bins = np.linspace(-0.5, 1.0, 151)
    ax = axes[0]
    ax.hist(nd[usable], bins=bins, color=CANOPY)
    for x in (params.ndvi_min, params.ndvi_max):
        ax.axvline(x, color=CHERRY, lw=1.5)
    ax.axvspan(params.ndvi_min, params.ndvi_max, color=CHERRY, alpha=0.12)
    ax.set(title="NDVI dos pixels válidos", xlabel="NDVI", ylabel="pixels")
    ax = axes[1]
    ax.hist(gn[usable], bins=bins, color=CANOPY)
    if params.gndvi_min is not None:
        ax.axvline(params.gndvi_min, color=CHERRY, lw=1.5)
    ax.set(title="GNDVI dos pixels válidos", xlabel="GNDVI")
    ax = axes[2]
    ax.hist2d(nd[usable], gn[usable], bins=120, range=[[-0.5, 1], [-0.5, 1]], cmap="Greens", cmin=1)
    ax.axvspan(params.ndvi_min, params.ndvi_max, color=CHERRY, alpha=0.12)
    r = np.corrcoef(nd[usable], gn[usable])[0, 1]
    ax.set(title=f"NDVI x GNDVI (r = {r:.2f})", xlabel="NDVI", ylabel="GNDVI")
    fig.savefig(OUT / "histogramas.png", dpi=110)
    plt.close(fig)

    # Máscara: candidato em vermelho-cereja, dossel denso em verde-escuro, NDVI baixo em palha.
    layers = [
        (low, STRAW, 0.35),
        (dense | dark, CANOPY, 0.75),
        (low_chlorophyll, INK_RGB, 0.6),
        (candidate, CHERRY, 0.55),
    ]
    masked = overlay(rgb, layers)
    fig, axes = plt.subplots(1, 2, figsize=(16, 8.4), constrained_layout=True)
    axes[0].imshow(rgb)
    axes[0].set_title("Cor verdadeira (B04, B03, B02; realce p2–p98)")
    axes[1].imshow(masked)
    gndvi_text = "" if params.gndvi_min is None else f", GNDVI ≥ {params.gndvi_min}"
    if args.red_min is not None:
        gndvi_text += f", vermelho ≥ {args.red_min}"
    axes[1].set_title(
        f"Candidato: NDVI {params.ndvi_min}–{params.ndvi_max}{gndvi_text} (vermelho) · "
        f"NDVI > {params.ndvi_max} (verde) · NDVI < {params.ndvi_min} (palha)"
    )
    for ax in axes:
        ax.set_xticks(range(0, 513, 64))
        ax.set_yticks(range(0, 513, 64))
        ax.grid(color="white", alpha=0.25, lw=0.5)
        ax.tick_params(labelsize=7)
    # JPEG: imagem fotográfica em PNG passa de 2 MB por figura.
    fig.savefig(OUT / f"mascara-{args.label}.jpg", dpi=100, pil_kwargs={"quality": 88})
    plt.close(fig)

    rule = f"NDVI {params.ndvi_min}–{params.ndvi_max}{gndvi_text}"
    # Resultado com a regra real do pipeline (morfologia e manchas pequenas). As
    # opções exploratórias (vermelho, GNDVI) não existem no pipeline: aí só
    # vale a coluna sem morfologia.
    potential = candidate
    if args.red_min is None and params.gndvi_min is None:
        potential = classify(image, quality, nd, params).potential
    lines = [
        f"rótulo: {args.label} ({rule})",
        f"  máscara de qualidade ({quality.source}): {quality.excluded.sum() * pixel_ha:9.2f} ha",
        f"  NDVI baixo:                     {low.sum() * pixel_ha:9.2f} ha",
        f"  NDVI alto (dossel denso):       {dense.sum() * pixel_ha:9.2f} ha",
        f"  vermelho baixo (dossel escuro): {dark.sum() * pixel_ha:9.2f} ha",
        f"  GNDVI baixo:                    {low_chlorophyll.sum() * pixel_ha:9.2f} ha",
        f"  candidato (sem morfologia):     {candidate.sum() * pixel_ha:9.2f} ha",
        f"  área potencial (cascata T2.6):  {potential.sum() * pixel_ha:9.2f} ha",
        f"  r(NDVI, GNDVI) nos válidos:     {r:9.3f}",
        "  fração de candidato nas amostras:",
    ]
    for name, (r0, r1, c0, c1) in SAMPLES.items():
        lines.append(f"    {name:28} {candidate[r0:r1, c0:c1].mean():6.0%}")
    if args.mapbiomas:
        lines += mapbiomas_section(image, nd, candidate, potential, rgb, rule, args.label, pixel_ha)
    report = "\n".join(lines)
    (OUT / f"resumo-{args.label}.txt").write_text(report + "\n")
    print(report)
    print(f"  arquivos em {OUT.relative_to(ROOT)}/")


def mapbiomas_section(image, nd, candidate, potential, rgb, rule, label, pixel_ha) -> list[str]:
    classes = read_mapbiomas(image)
    lines = [
        "  MapBiomas 2024 (conferência, não gabarito):",
        f"    {'classe':28} {'área':>8} {'sem morf.':>10} {'com morf.':>10}  NDVI p5/mediana/p95",
    ]
    present = [c for c in np.unique(classes) if c != 0]
    for code in sorted(present, key=lambda c: -(classes == c).sum()):
        inside = (classes == code) & image.valid
        name = MAPBIOMAS_CLASSES.get(int(code), f"classe {code}")
        p5, p50, p95 = np.percentile(nd[inside], [5, 50, 95])
        lines.append(
            f"    {name:28} {inside.sum() * pixel_ha:6.0f} ha {candidate[inside].mean():9.0%}"
            f" {potential[inside].mean():10.0%}   {p5:.2f}/{p50:.2f}/{p95:.2f}"
        )
    coffee = classes == MAPBIOMAS_COFFEE
    for title, mask in (("sem morfologia", candidate), ("com morfologia", potential)):
        if mask.any():
            lines.append(
                f"    {title}: {(mask & coffee).sum() / mask.sum():.0%} da área marcada cai em café"
                f" do MapBiomas; {(mask & coffee).sum() / coffee.sum():.0%} do café dele marcado"
            )
    lines.append(f"    fonte: {MAPBIOMAS_ATTRIBUTION}")

    fig, axes = plt.subplots(1, 2, figsize=(16, 8.8), constrained_layout=True)
    axes[0].imshow(
        overlay(
            rgb,
            [
                (classes == MAPBIOMAS_FOREST, CANOPY, 0.6),
                (classes == MAPBIOMAS_MOSAIC, YELLOW, 0.35),
                (classes == MAPBIOMAS_COFFEE, LILAC, 0.85),
            ],
        )
    )
    axes[0].set_title("MapBiomas 2024: café (lilás), formação florestal (verde), mosaico (amarelo)")
    axes[1].imshow(overlay(rgb, [(potential, CHERRY, 0.55)]))
    stage = "sem morfologia" if potential is candidate else "com morfologia e manchas ≥ mínimo"
    axes[1].set_title(f"Área potencial {rule} ({stage})")
    for ax in axes:
        ax.set_xticks(range(0, 513, 64))
        ax.set_yticks(range(0, 513, 64))
        ax.grid(color="white", alpha=0.25, lw=0.5)
        ax.tick_params(labelsize=7)
    fig.text(0.01, 0.005, MAPBIOMAS_ATTRIBUTION, fontsize=6.5, color="#555")
    fig.savefig(OUT / f"mapbiomas-{label}.jpg", dpi=90, pil_kwargs={"quality": 85})
    plt.close(fig)
    return lines


if __name__ == "__main__":
    main()
