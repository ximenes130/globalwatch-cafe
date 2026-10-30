"""Imagens da análise (T2.8, R2.16)."""

import io

import numpy as np
import pytest
from PIL import Image

from app.processing.classification import CODES, POTENTIAL, Classification, classify
from app.processing.indices import ndvi
from app.processing.masking import quality_mask
from app.processing.params import Params
from app.processing.reader import read_image
from app.processing.render import (
    CHERRY,
    MASK_ALPHA,
    MASK_GREY,
    PAPER,
    classification_png,
    download_scale,
    polygons_png,
    rgb_png,
    stretch,
)
from app.processing.vectorization import patch_polygons
from tests.rasters import KIT_IMAGE, KIT_SCL, make_tiff

GREY = (128, 128, 128)  # banda constante realçada para 0,5


def open_png(data: bytes) -> np.ndarray:
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return np.asarray(Image.open(io.BytesIO(data)))


def uniform_image(size: int, nodata: np.ndarray | None = None):
    dn = np.full((4, size, size), 2000)
    if nodata is not None:
        dn[:, nodata] = 0
    return read_image(make_tiff(dn))


def test_rgb_png_has_raster_size_and_transparent_nodata():
    nodata = np.zeros((10, 10), dtype=bool)
    nodata[0, :] = True

    pixels = open_png(rgb_png(uniform_image(10, nodata)))

    assert pixels.shape == (10, 10, 4)
    assert (pixels[0, :, 3] == 0).all()
    assert (pixels[1:, :, 3] == 255).all()


def test_stretch_maps_p2_and_p98_to_the_ends():
    band = np.arange(100, dtype=np.float32).reshape(10, 10)
    valid = np.ones((10, 10), dtype=bool)

    result = stretch(band, valid)

    assert result.min() == 0 and result.max() == 1
    assert result[0, 1] == 0  # 1 < p2 (1,98)
    assert result[9, 9] == 1  # 99 > p98 (97,02)
    assert np.all(np.diff(result.ravel()) >= 0)


def test_stretch_ignores_invalid_pixels_and_constant_bands():
    band = np.full((4, 4), 0.2, dtype=np.float32)
    band[0, 0] = np.nan

    valid = ~np.isnan(band)
    assert (stretch(band, valid)[valid] == 0.5).all()
    assert (stretch(band, np.zeros((4, 4), dtype=bool)) == 0).all()


def test_classification_png_colors():
    levels = np.full((4, 4), CODES["low_vegetation"], dtype=np.uint8)
    levels[0, 0] = POTENTIAL
    levels[1, 1] = CODES["quality_mask"]
    levels[2, 2] = CODES["no_data"]
    levels[3, 3] = CODES["dense_canopy"]

    pixels = open_png(classification_png(Classification(levels=levels, pixel_area_ha=0.01)))

    assert pixels.shape == (4, 4, 4)
    assert tuple(pixels[0, 0]) == (*CHERRY, 255)
    assert tuple(pixels[1, 1]) == (*MASK_GREY, MASK_ALPHA)
    # Fora da área potencial e da máscara: totalmente transparente.
    others = np.ones((4, 4), dtype=bool)
    others[0, 0] = others[1, 1] = False
    assert (pixels[others][:, 3] == 0).all()


@pytest.mark.parametrize(("size", "scale"), [(512, 2), (1024, 1), (2048, 1), (100, 4)])
def test_download_scale(size, scale):
    class Shape:
        shape = (size, size)

    assert download_scale(Shape()) == scale


def test_polygons_png_draws_outline_fill_hole_and_footer():
    image = uniform_image(40)
    levels = np.full(image.shape, CODES["low_vegetation"], dtype=np.uint8)
    levels[5:35, 5:35] = POTENTIAL
    levels[15:25, 15:25] = CODES["low_vegetation"]  # clareira
    classification = Classification(levels=levels, pixel_area_ha=image.pixel_area_ha)
    patches = patch_polygons(image, classification, Params())

    pixels = open_png(polygons_png(image, patches))

    scale = 4  # ceil(1024 / 40) limitado a 4
    assert pixels.shape[1] == 40 * scale
    assert pixels.shape[0] > 40 * scale  # rodapé abaixo da imagem
    assert tuple(pixels[5 * scale, 20 * scale]) == CHERRY  # contorno na borda superior
    assert tuple(pixels[2 * scale, 2 * scale]) == GREY  # longe de tudo: imagem original
    assert tuple(pixels[20 * scale, 20 * scale]) == GREY  # buraco sem preenchimento
    inside = pixels[30 * scale, 30 * scale]
    assert tuple(inside) != GREY and inside[0] > inside[1]  # preenchimento translúcido
    assert tuple(pixels[-1, -1]) == PAPER


def test_kit_images():
    image = read_image(KIT_IMAGE.read_bytes())
    params = Params()
    index = ndvi(image.red, image.nir, image.valid)
    classification = classify(
        image, quality_mask(image, params, KIT_SCL.read_bytes()), index, params
    )

    rgb = open_png(rgb_png(image))
    classes = open_png(classification_png(classification))
    polygons = open_png(polygons_png(image, patch_polygons(image, classification, params)))

    assert rgb.shape == (512, 512, 4)
    assert classes.shape == (512, 512, 4)
    assert (classes[..., 3] == 255).sum() == classification.potential.sum()
    assert polygons.shape[1] == 1024
