"""Cascata N0–N4, morfologia e área por nível (T2.6)."""

import numpy as np
import pytest

from app.processing.classification import CODES, EXCLUSION_LEVELS, POTENTIAL, classify, min_pixels
from app.processing.indices import ndvi
from app.processing.masking import QualityMask, quality_mask
from app.processing.params import Params
from app.processing.reader import read_image
from tests.rasters import KIT_IMAGE, KIT_SCL, make_tiff

LOW, MID, HIGH = 0.30, 0.65, 0.85  # pasto seco, faixa candidata, dossel denso
NO_MORPHOLOGY = Params(morphology_iterations=0)


def image(height: int, width: int, nodata: np.ndarray | None = None):
    """Imagem do kit em 10 m; as reflectâncias não importam (o NDVI vem pronto)."""
    dn = np.full((4, height, width), 2000)
    if nodata is not None:
        dn[:, nodata] = 0
    return read_image(make_tiff(dn))


def no_quality_mask(img, excluded: np.ndarray | None = None) -> QualityMask:
    if excluded is None:
        excluded = np.zeros(img.shape, dtype=bool)
    return QualityMask(excluded=excluded, source="ndwi", classes_excluded=None)


def run(ndvi_values: np.ndarray, params: Params | None = None, nodata=None, masked=None):
    params = params or Params()
    img = image(*ndvi_values.shape, nodata=nodata)
    values = ndvi_values.astype(np.float32)
    values[~img.valid] = np.nan
    return classify(img, no_quality_mask(img, masked), values, params)


def test_synthetic_bands_fall_in_their_levels():
    # Três faixas verticais de 10 colunas que encostam nas bordas da imagem.
    values = np.repeat([[LOW] * 10 + [MID] * 10 + [HIGH] * 10], 30, axis=0)

    result = run(values)

    assert (result.levels[:, :10] == CODES["low_vegetation"]).all()
    # Abertura e fechamento não comem a borda superior e inferior da faixa.
    assert (result.levels[:, 10:20] == POTENTIAL).all()
    assert (result.levels[:, 20:] == CODES["dense_canopy"]).all()
    assert result.potential_area_ha == pytest.approx(3.0)


def test_thresholds_are_inclusive():
    params = Params(ndvi_min=0.55, ndvi_max=0.72, morphology_iterations=0, min_area_ha=0)
    values = np.array([[0.5499, 0.55, 0.72, 0.7201]])

    result = run(values, params)

    expected = [CODES["low_vegetation"], POTENTIAL, POTENTIAL, CODES["dense_canopy"]]
    np.testing.assert_array_equal(result.levels[0], expected)


@pytest.mark.parametrize(("rows", "cols", "kept"), [(7, 7, False), (5, 10, True)])
def test_patch_below_min_area_goes_to_small_patch(rows, cols, kept):
    # 0,5 ha em pixels de 10 m = 50 pixels: 7 x 7 = 49 sai, 5 x 10 = 50 fica.
    values = np.full((20, 20), LOW)
    values[2 : 2 + rows, 2 : 2 + cols] = MID

    result = run(values, NO_MORPHOLOGY)

    block = result.levels[2 : 2 + rows, 2 : 2 + cols]
    assert (block == (POTENTIAL if kept else CODES["small_patch"])).all()


def test_patches_touching_only_at_a_corner_are_separate():
    # Vizinhança 4: 25 + 25 pixels encostados pela quina não somam 50.
    values = np.full((20, 20), LOW)
    values[0:5, 0:5] = MID
    values[5:10, 5:10] = MID

    result = run(values, NO_MORPHOLOGY)

    assert result.potential_area_ha == 0
    assert result.excluded_area_ha["small_patch"] == pytest.approx(0.5)


def test_opening_removes_thin_line_of_mixed_pixels():
    # Linha de 1 pixel, como o anel de borda da mata: some na abertura.
    values = np.full((20, 80), LOW)
    values[10, :] = MID

    result = run(values)

    assert (result.levels[10] == CODES["small_patch"]).all()
    assert result.potential_area_ha == 0


@pytest.mark.parametrize("iterations", [1, 2, 3])
def test_closing_fills_one_pixel_gap_inside_a_field(iterations):
    # A entrelinha cruza a imagem inteira: a borda também precisa fechar.
    values = np.full((20, 20), MID)
    values[:, 10] = LOW  # entrelinha com solo exposto

    result = run(values, Params(morphology_iterations=iterations))

    assert (result.levels == POTENTIAL).all()


def test_closing_never_reaches_nodata_or_masked_pixels():
    values = np.full((20, 20), MID)
    nodata = np.zeros((20, 20), dtype=bool)
    nodata[5, 5] = True
    masked = np.zeros((20, 20), dtype=bool)
    masked[12, 12] = True

    result = run(values, nodata=nodata, masked=masked)

    assert result.levels[5, 5] == CODES["no_data"]
    assert result.levels[12, 12] == CODES["quality_mask"]
    assert (result.levels == POTENTIAL).sum() == 400 - 2


def test_masked_pixel_filled_by_closing_does_not_count_for_patch_size():
    # Talhão 8 x 8 com um pixel mascarado no meio. Abertura e fechamento deixam
    # 60 pixels contando o buraco preenchido, 59 sem ele (a abertura em cruz
    # tira as 4 quinas). Com mínimo de 60, a mancha precisa sair.
    values = np.full((20, 20), LOW)
    values[5:13, 5:13] = MID
    masked = np.zeros((20, 20), dtype=bool)
    masked[8, 8] = True

    result = run(values, Params(min_area_ha=0.60), masked=masked)

    assert result.potential_area_ha == 0
    assert result.levels[8, 8] == CODES["quality_mask"]


def test_without_morphology_isolated_pixels_only_go_by_size():
    values = np.full((10, 10), MID)
    values[5, 5] = LOW

    result = run(values, NO_MORPHOLOGY)

    assert result.levels[5, 5] == CODES["low_vegetation"]
    assert (result.levels == POTENTIAL).sum() == 99


def test_each_pixel_counted_in_exactly_one_level():
    rng = np.random.default_rng(42)
    values = rng.uniform(0.1, 0.9, size=(40, 40))
    nodata = rng.random((40, 40)) < 0.05
    masked = rng.random((40, 40)) < 0.05

    result = run(values, Params(min_area_ha=0.05), nodata=nodata, masked=masked)

    total = sum(result.excluded_area_ha.values()) + result.potential_area_ha
    assert total == pytest.approx(40 * 40 * 0.01)
    assert set(result.excluded_area_ha) == set(EXCLUSION_LEVELS)
    # NoData conta só em `no_data`, mesmo que também esteja mascarado.
    assert result.excluded_area_ha["no_data"] == pytest.approx(nodata.sum() * 0.01)
    assert result.excluded_area_ha["quality_mask"] == pytest.approx((masked & ~nodata).sum() * 0.01)


def test_min_pixels_depends_on_pixel_size():
    assert min_pixels(0.5, image(2, 2)) == 50


def test_kit_areas_add_up_to_total():
    img = read_image(KIT_IMAGE.read_bytes())
    params = Params()
    quality = quality_mask(img, params, KIT_SCL.read_bytes())

    result = classify(img, quality, ndvi(img.red, img.nir, img.valid), params)

    total = sum(result.excluded_area_ha.values()) + result.potential_area_ha
    assert total == pytest.approx(2621.44)
    assert result.excluded_area_ha["no_data"] == 0
    assert result.excluded_area_ha["quality_mask"] == 0
    assert result.excluded_area_ha["low_chlorophyll"] == 0  # GNDVI só na T2.3
    # Sem morfologia a faixa marcava 457 ha (T2.5); a morfologia tira o ruído.
    assert 0 < result.potential_area_ha < 457
