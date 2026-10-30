"""Imagens da análise: cor verdadeira, classificação e polígonos (R2.16).

`rgb.png` e `classification.png` têm o tamanho do raster e vão para o mapa
como overlay pelos 4 cantos. `polygons.png` é a imagem para download.
"""

import io
import math
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.processing.classification import CODES, POTENTIAL, Classification
from app.processing.reader import ImageData
from app.processing.vectorization import PatchPolygon

# Cores da identidade do front (frontend/src/index.css).
CHERRY = (0xB3, 0x12, 0x2E)
MASK_GREY = (0x6B, 0x72, 0x80)
INK = (0x14, 0x20, 0x1A)
PAPER = (0xF2, 0xF4, 0xEF)
MASK_ALPHA = 160
FILL_ALPHA = 60

MIN_DOWNLOAD_SIDE = 1024
MAX_SCALE = 4
DEFAULT_ATTRIBUTION = "Contém dados Copernicus Sentinel modificados"
# A fonte embutida do Pillow não tem acentos ("Áreas", "não"); Public Sans tem.
FONT_PATH = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "PublicSans.ttf"


@lru_cache
def font(size: int, weight: str = "Medium") -> ImageFont.FreeTypeFont:
    loaded = ImageFont.truetype(FONT_PATH, size)
    loaded.set_variation_by_name(weight)  # fonte variável: o padrão é Thin
    return loaded


def stretch(band: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Realce linear p2–p98 para 0–1, calculado só nos pixels válidos."""
    values = band[valid]
    if values.size == 0:
        return np.zeros(band.shape, dtype=np.float32)
    low, high = np.percentile(values, [2, 98])
    if high <= low:  # banda constante: sem contraste a realçar
        return np.where(valid, 0.5, 0.0).astype(np.float32)
    return np.clip((np.nan_to_num(band) - low) / (high - low), 0, 1).astype(np.float32)


def true_color(image: ImageData) -> np.ndarray:
    """RGB uint8 (altura, largura, 3) com realce p2–p98 por banda."""
    bands = [stretch(b, image.valid) for b in (image.red, image.green, image.blue)]
    return np.round(np.dstack(bands) * 255).astype(np.uint8)


def rgb_png(image: ImageData) -> bytes:
    alpha = np.where(image.valid, 255, 0).astype(np.uint8)
    return _png(Image.fromarray(np.dstack([true_color(image), alpha]), mode="RGBA"))


def classification_png(classification: Classification) -> bytes:
    """Área potencial opaca, máscara de qualidade em cinza, resto transparente."""
    levels = classification.levels
    rgba = np.zeros((*levels.shape, 4), dtype=np.uint8)
    rgba[levels == POTENTIAL] = (*CHERRY, 255)
    rgba[levels == CODES["quality_mask"]] = (*MASK_GREY, MASK_ALPHA)
    return _png(Image.fromarray(rgba, mode="RGBA"))


def download_scale(image: ImageData) -> int:
    """Fator inteiro para o lado maior chegar a ~1024 px (entre 1 e 4)."""
    return max(1, min(MAX_SCALE, math.ceil(MIN_DOWNLOAD_SIDE / max(image.shape))))


def polygons_png(image: ImageData, patches: list[PatchPolygon]) -> bytes:
    """RGB ampliado com os polígonos, o `id` de cada um e um rodapé com atribuição.

    `patches` na ordem de `patch_polygons`: o `id` é a posição + 1, o mesmo do
    GeoJSON.
    """
    scale = download_scale(image)
    height, width = image.shape
    base = Image.fromarray(true_color(image), mode="RGB").resize(
        (width * scale, height * scale), Image.Resampling.NEAREST
    )

    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    to_pixel = ~image.transform

    def ring_xy(ring) -> list[tuple[float, float]]:
        """Coordenadas do CRS para pixels da imagem ampliada, todas de uma vez."""
        x, y = np.asarray(ring.coords).T
        cols = to_pixel.a * x + to_pixel.b * y + to_pixel.c
        rows = to_pixel.d * x + to_pixel.e * y + to_pixel.f
        return list(zip(cols * scale, rows * scale, strict=True))

    for patch in patches:
        draw.polygon(ring_xy(patch.polygon.exterior), fill=(*CHERRY, FILL_ALPHA))
        # Desenhar com alfa 0 numa camada RGBA substitui o pixel: abre o buraco.
        for hole in patch.polygon.interiors:
            draw.polygon(ring_xy(hole), fill=(0, 0, 0, 0))
    for patch in patches:
        for ring in (patch.polygon.exterior, *patch.polygon.interiors):
            draw.line(ring_xy(ring), fill=(*CHERRY, 255), width=scale)

    label_font = font(6 * scale + 4, "Bold")
    for feature_id, patch in enumerate(patches, start=1):
        point = patch.polygon.representative_point()
        col, row = to_pixel @ (point.x, point.y)
        text = str(feature_id)
        # Mantém o rótulo inteiro dentro da imagem (polígonos na borda do recorte).
        left, top, right, bottom = label_font.getbbox(text, stroke_width=2)
        half_w, half_h = (right - left) / 2, (bottom - top) / 2
        x = min(max(col * scale, half_w), base.width - half_w)
        y = min(max(row * scale, half_h), base.height - half_h)
        draw.text(
            (x, y),
            text,
            font=label_font,
            anchor="mm",
            fill=(255, 255, 255, 255),
            stroke_width=2,
            stroke_fill=(*INK, 255),
        )

    picture = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    return _png(_with_footer(picture, image.acquired_at, image.attribution, scale))


def _with_footer(
    picture: Image.Image, acquired_at: datetime | None, attribution: str | None, scale: int
) -> Image.Image:
    footer_font = font(7 * scale + 2)
    line_height = footer_font.size + 6
    date = acquired_at.strftime("%d/%m/%Y") if acquired_at else "data não informada"
    lines = [
        f"Áreas potenciais de café (não validadas) · imagem de {date}",
        attribution or DEFAULT_ATTRIBUTION,
    ]
    footer_height = line_height * len(lines) + 12
    canvas = Image.new("RGB", (picture.width, picture.height + footer_height), PAPER)
    canvas.paste(picture, (0, 0))
    draw = ImageDraw.Draw(canvas)
    for i, text in enumerate(lines):
        draw.text((10, picture.height + 6 + i * line_height), text, font=footer_font, fill=INK)
    return canvas


def _png(picture: Image.Image) -> bytes:
    buffer = io.BytesIO()
    picture.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
