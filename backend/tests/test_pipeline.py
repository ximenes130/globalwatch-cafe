"""Pipeline completo como função pura (T2.9, R2.1, R2.17, R2.19, R2.20)."""

import json

import numpy as np
import pytest

from app.processing.errors import ProcessingError
from app.processing.params import METHOD_VERSION, Params
from app.processing.pipeline import run_pipeline
from tests.rasters import KIT_IMAGE, KIT_SCL, make_tiff, reflectance_to_dn

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@pytest.fixture(scope="module")
def kit_result():
    return run_pipeline(KIT_IMAGE.read_bytes(), KIT_SCL.read_bytes(), Params())


def synthetic_tiff(ndvi_like: str) -> bytes:
    """Imagem 60 x 60: toda pasto seco ou com um talhão de vigor intermediário."""
    pasture = [reflectance_to_dn(r) for r in (0.06, 0.09, 0.12, 0.22)]  # NDVI ≈ 0,29
    field = [reflectance_to_dn(r) for r in (0.03, 0.06, 0.05, 0.28)]  # NDVI ≈ 0,70
    dn = np.empty((4, 60, 60), dtype=int)
    dn[:] = np.array(pasture)[:, None, None]
    if ndvi_like == "field":
        dn[:, 10:40, 10:40] = np.array(field)[:, None, None]
    return make_tiff(dn)


def test_kit_is_processed_end_to_end(kit_result):
    result = kit_result

    assert result.crs == "EPSG:32723"
    assert result.acquired_at.isoformat() == "2025-08-16T13:28:10.823000+00:00"
    assert result.stats["total_area_ha"] == 2621.44
    assert result.stats["polygon_count"] == len(result.geojson["features"]) > 0
    assert result.method_version == METHOD_VERSION
    assert len(result.bounds_wgs84) == 4
    assert set(result.images) == {"rgb.png", "classification.png", "polygons.png"}
    assert all(png.startswith(PNG_SIGNATURE) for png in result.images.values())
    assert result.stats["gndvi"] is not None  # GNDVI sempre calculado (R2.9)


def test_params_record_is_json_and_describes_what_was_read(kit_result):
    record = kit_result.params

    assert json.loads(json.dumps(record)) == record
    assert record["method_version"] == METHOD_VERSION
    assert record["radiometry"]["source"] == "file_tags"
    assert record["bands"] == {"indexes": [1, 2, 3, 4], "source": "descriptions"}
    assert record["ndvi_min"] == 0.55 and record["ndvi_max"] == 0.72
    assert record["scl_exclude"] == [0, 1, 3, 6, 8, 9, 10, 11]


def test_everything_saved_is_json(kit_result):
    for value in (kit_result.stats, kit_result.rationale, kit_result.geojson):
        json.dumps(value)


def test_same_input_same_result(kit_result):
    again = run_pipeline(KIT_IMAGE.read_bytes(), KIT_SCL.read_bytes(), Params())

    assert again.stats == kit_result.stats
    assert again.geojson == kit_result.geojson
    assert again.rationale == kit_result.rationale
    assert again.images == kit_result.images


def test_different_file_gives_different_result(kit_result):
    other = run_pipeline(synthetic_tiff("field"), None, Params())

    assert other.stats != kit_result.stats
    assert other.stats["total_area_ha"] == 36.0
    assert other.stats["polygon_count"] == 1
    assert other.stats["potential_area_ha"] == pytest.approx(9.0, abs=0.1)
    assert other.rationale["masks"]["source"] == "ndwi"


def test_no_vegetation_is_completed_with_zero_polygons():
    result = run_pipeline(synthetic_tiff("pasture"), None, Params())

    assert result.geojson == {"type": "FeatureCollection", "features": []}
    assert result.stats["polygon_count"] == 0
    assert result.stats["potential_area_ha"] == 0
    assert "nenhuma área" in result.rationale["summary"]
    assert result.images["polygons.png"].startswith(PNG_SIGNATURE)


@pytest.mark.parametrize(
    "data",
    [b"isto nao e um tiff", b"II*\x00" + b"\x00" * 64],
    ids=["texto", "cabecalho-tiff-truncado"],
)
def test_corrupted_file_is_a_readable_processing_error(data):
    with pytest.raises(ProcessingError) as excinfo:
        run_pipeline(data, None, Params())

    message = str(excinfo.value)
    assert message == "Não foi possível ler a imagem enviada como GeoTIFF."
    assert "Traceback" not in message and "/" not in message


def test_three_band_file_is_a_readable_processing_error():
    tiff = make_tiff(np.full((3, 4, 4), 2000), scales=None, offsets=None, descriptions=None)

    with pytest.raises(ProcessingError, match="são necessárias 4"):
        run_pipeline(tiff, None, Params())
