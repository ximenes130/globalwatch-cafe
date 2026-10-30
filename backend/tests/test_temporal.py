"""Segunda data e regra de amplitude (T3.5, R3.10, R3.11)."""

import json

import numpy as np
import pytest
from rasterio.transform import from_origin

from app.processing.errors import ProcessingError
from app.processing.masking import QualityMask
from app.processing.params import Params
from app.processing.pipeline import run_pipeline
from app.processing.reader import read_image
from app.processing.temporal import (
    GRID_MISMATCH,
    combined_quality,
    ndvi_amplitude,
    read_second_date,
)
from tests.rasters import (
    ADDITIONAL_IMAGE,
    ADDITIONAL_SCL,
    KIT_IMAGE,
    KIT_ORIGIN,
    KIT_SCL,
    make_scl,
    make_tiff,
    reflectance_to_dn,
)

# Reflectâncias (azul, verde, vermelho, NIR) com o NDVI indicado.
FIELD = (0.03, 0.06, 0.05, 0.28)  # ≈ 0,70: na faixa de área potencial
DRY_FIELD = (0.03, 0.06, 0.08, 0.32)  # 0,60: na faixa na seca
GREEN_FIELD = (0.03, 0.06, 0.03, 0.57)  # 0,90: o mesmo talhão verde na chuva (+0,30)
PASTURE = (0.06, 0.09, 0.12, 0.22)  # ≈ 0,29


def tiff(*blocks, size: int = 60, transform=None, crs: str = "EPSG:32723") -> bytes:
    """Imagem `size` x `size` de pasto, com blocos (linhas, colunas, reflectâncias)."""
    dn = np.empty((4, size, size), dtype=int)
    dn[:] = np.array([reflectance_to_dn(r) for r in PASTURE])[:, None, None]
    for rows, cols, reflectance in blocks:
        dn[:, rows, cols] = np.array([reflectance_to_dn(r) for r in reflectance])[:, None, None]
    return make_tiff(dn, transform=transform, crs=crs)


FIELDS = [(slice(10, 30), slice(10, 50), FIELD), (slice(35, 55), slice(10, 50), FIELD)]


@pytest.fixture(scope="module")
def kit_two_dates():
    return run_pipeline(
        KIT_IMAGE.read_bytes(),
        KIT_SCL.read_bytes(),
        Params(),
        ADDITIONAL_IMAGE.read_bytes(),
        ADDITIONAL_SCL.read_bytes(),
    )


def test_amplitude_is_absolute_and_symmetric():
    a = np.array([0.6, 0.7, np.nan], dtype=np.float32)
    b = np.array([0.9, 0.5, 0.6], dtype=np.float32)

    assert ndvi_amplitude(a, b)[:2] == pytest.approx([0.3, 0.2])
    assert np.isnan(ndvi_amplitude(a, b)[2])
    assert np.array_equal(ndvi_amplitude(a, b), ndvi_amplitude(b, a), equal_nan=True)


def test_field_that_greens_up_leaves_and_stable_field_stays():
    # Dois talhões na faixa na seca; na chuva, o de cima dispara (pasto/lavoura
    # anual), o de baixo fica parecido (perene).
    dry = tiff((slice(10, 30), slice(10, 50), DRY_FIELD), FIELDS[1])
    wet = tiff((slice(10, 30), slice(10, 50), GREEN_FIELD), FIELDS[1])

    one = run_pipeline(dry, None, Params())
    two = run_pipeline(dry, None, Params(), wet, None)

    # 800 pixels por talhão; a abertura com a cruz arredonda os 4 cantos de cada um.
    assert one.stats["potential_area_ha"] == 15.92
    assert two.stats["potential_area_ha"] == 7.96
    assert two.stats["excluded_area_ha"]["high_amplitude"] == 8.0
    assert one.stats["excluded_area_ha"]["high_amplitude"] == 0


@pytest.mark.parametrize(
    ("transform", "crs", "size"),
    [
        (from_origin(KIT_ORIGIN[0] + 10, KIT_ORIGIN[1], 10, 10), "EPSG:32723", 60),
        (from_origin(*KIT_ORIGIN, 20, 20), "EPSG:32723", 60),
        (None, "EPSG:32722", 60),
        (None, "EPSG:32723", 50),
    ],
    ids=["deslocada", "outra-resolucao", "outro-crs", "outro-tamanho"],
)
def test_second_image_on_another_grid_fails_with_message(transform, crs, size):
    second = tiff(size=size, transform=transform, crs=crs)

    with pytest.raises(ProcessingError) as error:
        run_pipeline(tiff(*FIELDS), None, Params(), second, None)

    assert str(error.value) == GRID_MISMATCH


def test_unreadable_second_image_says_which_file():
    with pytest.raises(ProcessingError) as error:
        run_pipeline(tiff(*FIELDS), None, Params(), b"nao e tiff", None)

    assert str(error.value) == (
        "Segunda imagem: Não foi possível ler a imagem enviada como GeoTIFF."
    )


def test_cloud_in_either_date_goes_to_quality_mask():
    primary = read_image(tiff(*FIELDS))
    no_mask = QualityMask(
        excluded=np.zeros(primary.shape, dtype=bool), source="scl", classes_excluded=(9,)
    )
    # SCL de 20 m: nuvem (9) no canto superior esquerdo da segunda data.
    classes = np.full((30, 30), 4, dtype=np.uint8)
    classes[:10, :10] = 9
    second = read_second_date(tiff(*FIELDS), make_scl(classes), Params(), primary)

    quality = combined_quality(primary, no_mask, second)

    assert quality.excluded[:20, :20].all()
    assert quality.excluded.sum() == 400
    assert quality.source == "scl"


def test_nodata_in_second_date_is_masked_but_primary_nodata_stays_in_n0():
    dn = np.full((4, 60, 60), reflectance_to_dn(0.2))
    dn[:, :5, :] = 0  # sem dado na segunda data
    second_bytes = make_tiff(dn)
    primary_dn = dn.copy()
    primary_dn[:, :5, :] = reflectance_to_dn(0.2)
    primary_dn[:, -5:, :] = 0  # sem dado na principal

    result = run_pipeline(make_tiff(primary_dn), None, Params(), second_bytes, None)

    assert result.stats["excluded_area_ha"]["quality_mask"] == pytest.approx(3.0)
    assert result.stats["excluded_area_ha"]["no_data"] == pytest.approx(3.0)


def test_kit_with_january_scene(kit_two_dates):
    # Simulação da T3.3 registrada no design antes de implementar (103,0 ha, com
    # uma casa decimal).
    result = kit_two_dates

    assert result.stats["potential_area_ha"] == 103.04
    assert result.stats["second_acquired_at"] == "2026-01-10T13:18:10.279000+00:00"
    assert result.acquired_at.isoformat().startswith("2025-08-16")
    levels = result.stats["excluded_area_ha"]
    assert sum(levels.values()) + result.stats["potential_area_ha"] == pytest.approx(2621.44)
    assert levels["high_amplitude"] > 0


def test_two_dates_are_recorded_in_params_and_rationale(kit_two_dates):
    record = kit_two_dates.params

    assert json.loads(json.dumps(record)) == record
    assert record["ndvi_amplitude_max"] == 0.25
    assert record["second_image"] == {
        "acquired_at": "2026-01-10T13:18:10.279000+00:00",
        "radiometry": {"scale": [0.0001] * 4, "offset": [-0.1] * 4, "source": "file_tags"},
        "bands": {"indexes": [1, 2, 3, 4], "source": "descriptions"},
        "quality_source": "scl",
    }
    steps = {step["name"]: step for step in kit_two_dates.rationale["steps"]}
    excluded = kit_two_dates.stats["excluded_area_ha"]["high_amplitude"]
    assert steps["high_amplitude"]["excluded_ha"] == excluded


def test_single_date_records_no_second_image():
    result = run_pipeline(tiff(*FIELDS), None, Params())

    assert result.params["second_image"] is None
    assert result.stats["second_acquired_at"] is None


def test_combined_mask_only_marks_pixels_valid_in_the_primary():
    # Invariante do QualityMask: NoData da principal é N0, nunca N1.
    dn = np.full((4, 60, 60), reflectance_to_dn(0.2))
    dn[:, :5, :] = 0
    primary = read_image(make_tiff(dn))
    second = read_second_date(make_tiff(np.zeros((4, 60, 60))), None, Params(), primary)
    no_mask = QualityMask(
        excluded=np.zeros(primary.shape, dtype=bool), source="scl", classes_excluded=(9,)
    )

    quality = combined_quality(primary, no_mask, second)

    assert not quality.excluded[:5].any()
    assert quality.excluded[5:].all()
