"""Pontos da inspeção visual do resultado do kit (T7.1, R7.7).

Roda as mesmas funções do pipeline do backend sobre o kit e sorteia, com
semente fixa, 15 pixels:

- 10 na área potencial;
- 3 excluídos por NDVI alto (dossel denso);
- 2 excluídos por NDVI baixo.

Para cada ponto, recorta 600 x 600 m de cor verdadeira em torno do pixel, com
a área potencial contornada em cereja e uma cruz no centro. A leitura do que
aparece em cada recorte é feita à mão em `inspecao-visual.md`. São 15 pontos:
servem para ver se o resultado faz sentido, não para estimar acurácia.

Gera em `docs/evidencias/inspecao/`:
- `prancha.jpg`: os 15 recortes numerados;
- `pontos.csv`: número, grupo, linha e coluna, coordenadas e NDVI de cada ponto.

Uso (da raiz do repositório):
    backend/.venv/bin/python scripts/inspect_points.py
"""

import csv
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from pyproj import Transformer
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.processing.classification import CODES, POTENTIAL, classify  # noqa: E402
from app.processing.indices import gndvi, ndvi  # noqa: E402
from app.processing.masking import quality_mask  # noqa: E402
from app.processing.params import Params  # noqa: E402
from app.processing.reader import read_image  # noqa: E402
from app.processing.render import CHERRY, INK, PAPER, font, true_color  # noqa: E402

KIT = ROOT / "data" / "exemplo"
OUT = ROOT / "docs" / "evidencias" / "inspecao"

SEED = 7
# Grupo → (código na classificação, quantidade).
GROUPS = {
    "potencial": (POTENTIAL, 10),
    "dossel denso": (CODES["dense_canopy"], 3),
    "NDVI baixo": (CODES["low_vegetation"], 2),
}
HALF = 30  # 30 px de cada lado a 10 m: recorte de 600 m
MIN_SPACING = 2 * HALF  # recortes sem sobreposição: cada ponto mostra um lugar novo
ZOOM = 4
COLUMNS = 5
LABEL_HEIGHT = 34


def sample_points(levels: np.ndarray, rng: np.random.Generator) -> list[tuple[str, int, int]]:
    rows, cols = levels.shape
    inner = np.zeros(levels.shape, dtype=bool)
    inner[HALF : rows - HALF, HALF : cols - HALF] = True  # recorte inteiro dentro da cena
    chosen: list[tuple[str, int, int]] = []
    for group, (code, count) in GROUPS.items():
        candidates = np.argwhere((levels == code) & inner)
        taken = 0
        for index in rng.permutation(len(candidates)):
            row, col = (int(v) for v in candidates[index])
            if all(max(abs(row - r), abs(col - c)) >= MIN_SPACING for _, r, c in chosen):
                chosen.append((group, row, col))
                taken += 1
                if taken == count:
                    break
    return chosen


def tile(rgb: np.ndarray, potential: np.ndarray, row: int, col: int) -> Image.Image:
    window = (slice(row - HALF, row + HALF), slice(col - HALF, col + HALF))
    crop = Image.fromarray(rgb[window]).resize((2 * HALF * ZOOM,) * 2, Image.Resampling.BILINEAR)
    # Contorno no tamanho ampliado, para a linha ficar fina sobre o RGB.
    mask = np.kron(potential[window], np.ones((ZOOM, ZOOM), dtype=bool))
    edge = mask & ~ndimage.binary_erosion(mask, iterations=2)  # linha de 2 px
    pixels = np.asarray(crop).copy()
    pixels[edge] = CHERRY
    picture = Image.fromarray(pixels)
    draw = ImageDraw.Draw(picture)
    center, arm = HALF * ZOOM, 10
    for width, color in ((5, PAPER), (2, INK)):
        draw.line([(center - arm, center), (center + arm, center)], fill=color, width=width)
        draw.line([(center, center - arm), (center, center + arm)], fill=color, width=width)
    return picture


def main() -> None:
    params = Params()
    image = read_image((KIT / "imagem_multiespectral.tif").read_bytes())
    quality = quality_mask(image, params, (KIT / "qualidade_scl.tif").read_bytes())
    ndvi_values = ndvi(image.red, image.nir, image.valid)
    gndvi_values = gndvi(image.green, image.nir, image.valid)
    levels = classify(image, quality, ndvi_values, params, gndvi=gndvi_values).levels

    points = sample_points(levels, np.random.default_rng(SEED))
    rgb = true_color(image)
    potential = levels == POTENTIAL
    to_wgs84 = Transformer.from_crs(image.crs, "EPSG:4326", always_xy=True)

    side = 2 * HALF * ZOOM
    sheet_rows = -(-len(points) // COLUMNS)
    sheet = Image.new("RGB", (COLUMNS * side, sheet_rows * (side + LABEL_HEIGHT)), PAPER)
    draw = ImageDraw.Draw(sheet)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "pontos.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ponto", "grupo", "linha", "coluna", "lon", "lat", "ndvi"])
        for number, (group, row, col) in enumerate(points, start=1):
            # Centro do pixel em UTM e depois em graus.
            x, y = image.transform * (col + 0.5, row + 0.5)
            lon, lat = to_wgs84.transform(x, y)
            value = float(ndvi_values[row, col])
            writer.writerow([number, group, row, col, f"{lon:.5f}", f"{lat:.5f}", f"{value:.2f}"])

            left = (number - 1) % COLUMNS * side
            top = (number - 1) // COLUMNS * (side + LABEL_HEIGHT)
            sheet.paste(tile(rgb, potential, row, col), (left, top))
            label = f"{number}  {group}  ·  NDVI {value:.2f}".replace(".", ",")
            draw.text((left + 8, top + side + 7), label, fill=INK, font=font(17))

    sheet.save(OUT / "prancha.jpg", quality=88)
    for number, (group, row, col) in enumerate(points, start=1):
        print(f"{number:2d} {group:13s} linha {row:3d} coluna {col:3d}")


if __name__ == "__main__":
    main()
