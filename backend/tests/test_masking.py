"""Máscara de qualidade: SCL reamostrada e NDWI sem SCL (T2.4)."""

import numpy as np
import pytest

from app.processing.errors import ProcessingError
from app.processing.masking import quality_mask, resample_scl
from app.processing.params import Params
from app.processing.reader import read_image
from tests.rasters import KIT_IMAGE, KIT_ORIGIN, KIT_SCL, make_scl, make_tiff, reflectance_to_dn

# Reflectância (azul, verde, vermelho, NIR) de alvos típicos.
VEGETATION = (0.03, 0.06, 0.04, 0.30)
WATER = (0.05, 0.08, 0.04, 0.02)


def image_from(pixels: list[list[tuple[float, ...]]]):
    """Imagem do kit em 10 m a partir de uma grade de reflectâncias por pixel."""
    dn = np.array([[[reflectance_to_dn(r) for r in px] for px in row] for row in pixels])
    return read_image(make_tiff(np.moveaxis(dn, -1, 0)))


def vegetation_image(height: int = 4, width: int = 4):
    return image_from([[VEGETATION] * width for _ in range(height)])


def test_scl_2x2_becomes_4x4_mask_with_excluded_classes():
    # 4 = vegetação, 8 = nuvem, 6 = água, 5 = solo exposto.
    scl = make_scl(np.array([[4, 8], [6, 5]]))

    mask = quality_mask(vegetation_image(), Params(), scl)

    expected = np.array(
        [
            [False, False, True, True],
            [False, False, True, True],
            [True, True, False, False],
            [True, True, False, False],
        ]
    )
    np.testing.assert_array_equal(mask.excluded, expected)
    assert mask.source == "scl"
    assert mask.classes_excluded == (0, 1, 3, 6, 8, 9, 10, 11)


def test_scl_is_resampled_by_nearest_neighbour():
    scl = make_scl(np.array([[2, 7], [4, 5]]))

    classes = resample_scl(scl, vegetation_image())

    # Vizinho mais próximo: só classes existentes, cada uma num bloco 2 x 2.
    np.testing.assert_array_equal(classes, np.repeat(np.repeat([[2, 7], [4, 5]], 2, 0), 2, 1))


@pytest.mark.parametrize("nodata", [0, None])
def test_pixels_outside_scl_coverage_are_excluded(nodata):
    # SCL de um pixel (20 m) cobre só o quadrante superior esquerdo. Sem
    # `nodata` declarado, o rasterio não tem o 0 da SCL para preencher o resto.
    scl = make_scl(np.array([[4]]), nodata=nodata)

    mask = quality_mask(vegetation_image(), Params(), scl)

    assert not mask.excluded[:2, :2].any()
    assert mask.excluded.sum() == 12


def test_scl_that_does_not_cover_the_image_is_an_error():
    far_away = (KIT_ORIGIN[0] + 100_000, KIT_ORIGIN[1])
    scl = make_scl(np.array([[4, 4], [4, 4]]), origin=far_away)

    with pytest.raises(ProcessingError, match="não cobre"):
        quality_mask(vegetation_image(), Params(), scl)


def test_scl_without_crs_is_an_error():
    scl = make_scl(np.array([[4, 4], [4, 4]]), crs=None)

    with pytest.raises(ProcessingError, match="sistema de coordenadas"):
        quality_mask(vegetation_image(), Params(), scl)


def test_unreadable_scl_is_an_error():
    with pytest.raises(ProcessingError, match="ler a SCL"):
        quality_mask(vegetation_image(), Params(), b"isto nao e um tiff")


def test_nodata_pixel_is_not_counted_again_in_the_quality_mask():
    image = image_from([[VEGETATION, VEGETATION], [VEGETATION, (0.0, 0.0, 0.0, -0.1)]])
    assert not image.valid[1, 1]  # DN 0 nas quatro bandas
    scl = make_scl(np.array([[8]]))  # nuvem em tudo

    mask = quality_mask(image, Params(), scl)

    assert mask.excluded.sum() == 3
    assert not mask.excluded[1, 1]


def test_without_scl_water_is_excluded_by_ndwi():
    image = image_from([[VEGETATION, WATER], [WATER, VEGETATION]])

    mask = quality_mask(image, Params(), None)

    np.testing.assert_array_equal(mask.excluded, [[False, True], [True, False]])
    assert mask.source == "ndwi"
    assert mask.classes_excluded is None


def test_ndwi_threshold_comes_from_params():
    image = image_from([[WATER]])  # NDWI = 0,6

    assert quality_mask(image, Params(ndwi_water_min=0.5), None).excluded[0, 0]
    assert not quality_mask(image, Params(ndwi_water_min=0.7), None).excluded[0, 0]


def test_kit_scl_excludes_nothing():
    image = read_image(KIT_IMAGE.read_bytes())

    mask = quality_mask(image, Params(), KIT_SCL.read_bytes())

    # A SCL do kit só tem as classes 2, 4, 5 e 7, nenhuma em `scl_exclude`.
    assert mask.excluded.shape == (512, 512)
    assert not mask.excluded.any()
    classes = resample_scl(KIT_SCL.read_bytes(), image)
    assert set(np.unique(classes)) == {2, 4, 5, 7}
