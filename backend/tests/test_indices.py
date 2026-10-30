"""Índices espectrais com divisão segura (T2.2)."""

import numpy as np
import pytest

from app.processing.indices import gndvi, ndvi, ndwi, normalized_difference
from app.processing.reader import read_image
from tests.rasters import KIT_IMAGE


def arr(*values: float) -> np.ndarray:
    return np.array(values, dtype=np.float32)


def all_valid(n: int) -> np.ndarray:
    return np.ones(n, dtype=bool)


def test_ndvi_known_values():
    red = arr(0.01, 0.10, 0.30)
    nir = arr(0.31, 0.10, 0.10)

    result = ndvi(red, nir, all_valid(3))

    assert result == pytest.approx([0.9375, 0.0, -0.5], abs=1e-6)
    assert result.dtype == np.float32


def test_ndwi_known_values_water_is_positive():
    green = arr(0.08, 0.06)
    nir = arr(0.02, 0.30)  # água: NIR baixo; vegetação: NIR alto

    result = ndwi(green, nir, all_valid(2))

    assert result == pytest.approx([0.6, -0.6666667], abs=1e-6)


def test_gndvi_known_values_uses_green_not_red():
    green = arr(0.06, 0.10)
    nir = arr(0.30, 0.10)

    result = gndvi(green, nir, all_valid(2))

    assert result == pytest.approx([0.6666667, 0.0], abs=1e-6)


def test_order_of_bands_matters():
    a, b = arr(0.4), arr(0.1)

    assert normalized_difference(a, b, all_valid(1))[0] == pytest.approx(0.6)
    assert normalized_difference(b, a, all_valid(1))[0] == pytest.approx(-0.6)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        (0.0, 0.0),  # denominador zero
        (-0.02, 0.02),  # soma zero com uma banda negativa
        (-0.05, -0.01),  # soma negativa: razão de sinal invertido
        (1e-8, 1e-8),  # denominador minúsculo
    ],
)
def test_zero_or_negative_denominator_in_valid_pixel_is_zero(a, b):
    result = normalized_difference(arr(a), arr(b), all_valid(1))

    assert np.isfinite(result).all()
    assert result[0] == 0.0


def test_result_is_clipped_to_unit_range():
    # Uma banda negativa com soma positiva levaria a razão para fora de [−1, 1].
    result = normalized_difference(arr(0.3, -0.05), arr(-0.05, 0.3), all_valid(2))

    assert result == pytest.approx([1.0, -1.0])


def test_invalid_pixels_are_nan_even_with_good_values():
    valid = np.array([True, False])

    result = ndvi(arr(0.05, 0.05), arr(0.4, 0.4), valid)

    assert result[0] == pytest.approx(0.7777778)
    assert np.isnan(result[1])


def test_nan_reflectance_outside_valid_does_not_warn():
    # O reader marca NoData com NaN; o índice não deve gerar RuntimeWarning.
    red = arr(0.05, np.nan)
    nir = arr(0.4, np.nan)

    with np.errstate(all="raise"):
        result = ndvi(red, nir, np.array([True, False]))

    assert np.isnan(result[1])


def test_kit_indices_are_finite_and_in_range():
    image = read_image(KIT_IMAGE.read_bytes())

    for index in (
        ndvi(image.red, image.nir, image.valid),
        ndwi(image.green, image.nir, image.valid),
    ):
        values = index[image.valid]
        assert np.isfinite(values).all()
        assert values.min() >= -1 and values.max() <= 1
    # Exploração de 30/10: NDVI do kit vai de −0,434 a 0,886.
    kit_ndvi = ndvi(image.red, image.nir, image.valid)
    assert float(kit_ndvi.min()) == pytest.approx(-0.434, abs=1e-3)
    assert float(kit_ndvi.max()) == pytest.approx(0.886, abs=1e-3)
