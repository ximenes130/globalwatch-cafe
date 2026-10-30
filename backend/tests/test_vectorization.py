"""GeoJSON RFC 7946, propriedades e cantos da imagem (T2.7, R2.13)."""

import json

import numpy as np
import pytest
from shapely.geometry import shape

from app.processing.classification import CODES, POTENTIAL, Classification, classify
from app.processing.indices import gndvi, ndvi
from app.processing.masking import quality_mask
from app.processing.params import Params
from app.processing.reader import read_image
from app.processing.vectorization import build_stats, corners_wgs84, index_summary, vectorize
from tests.rasters import KIT_DIR, KIT_IMAGE, KIT_SCL, make_tiff

STUDY_AREA = json.loads((KIT_DIR / "area_estudo.geojson").read_text())


def synthetic(potential: np.ndarray, ndvi_value: float = 0.6):
    image = read_image(make_tiff(np.full((4, *potential.shape), 2000)))
    levels = np.where(potential, POTENTIAL, CODES["low_vegetation"]).astype(np.uint8)
    classification = Classification(levels=levels, pixel_area_ha=image.pixel_area_ha)
    index = np.full(image.shape, ndvi_value, dtype=np.float32)
    return vectorize(image, classification, index, Params())


@pytest.fixture(scope="module")
def kit_geojson():
    image = read_image(KIT_IMAGE.read_bytes())
    params = Params()
    index = ndvi(image.red, image.nir, image.valid)
    classification = classify(
        image, quality_mask(image, params, KIT_SCL.read_bytes()), index, params
    )
    return vectorize(image, classification, index, params)


def test_feature_properties():
    potential = np.zeros((30, 30), dtype=bool)
    potential[2:12, 2:12] = True

    feature = synthetic(potential, ndvi_value=0.65)["features"][0]

    assert feature["type"] == "Feature"
    assert feature["id"] == 1
    assert feature["properties"] == {
        "id": 1,
        "area_ha": 1.0,
        "ndvi_mean": 0.65,
        "gndvi_mean": None,
        "class": "potential_coffee_area",
        "validated": False,
    }


def test_ids_follow_decreasing_area():
    potential = np.zeros((40, 40), dtype=bool)
    potential[1:8, 1:8] = True  # 49 px
    potential[20:35, 20:35] = True  # 225 px
    potential[1:11, 25:35] = True  # 100 px

    features = synthetic(potential)["features"]

    assert [f["id"] for f in features] == [1, 2, 3]
    assert [f["properties"]["area_ha"] for f in features] == [2.25, 1.0, 0.49]


def test_one_feature_per_patch_and_holes_kept():
    potential = np.zeros((30, 30), dtype=bool)
    potential[5:25, 5:25] = True
    potential[12:18, 12:18] = False  # clareira no meio do talhão

    features = synthetic(potential)["features"]

    assert len(features) == 1
    polygon = shape(features[0]["geometry"])
    assert polygon.is_valid
    assert len(polygon.interiors) == 1
    assert features[0]["properties"]["area_ha"] == pytest.approx((400 - 36) * 0.01)


def test_rfc7946_orientation_and_lon_lat_order():
    potential = np.zeros((30, 30), dtype=bool)
    potential[5:25, 5:25] = True
    potential[12:18, 12:18] = False

    geometry = synthetic(potential)["features"][0]["geometry"]

    polygon = shape(geometry)
    assert polygon.exterior.is_ccw
    assert all(not ring.is_ccw for ring in polygon.interiors)
    lon, lat = geometry["coordinates"][0][0]
    # Origem do kit: oeste de Guaxupé/MG.
    assert -46.8 < lon < -46.6 and -21.4 < lat < -21.2
    assert "crs" not in geometry


def test_coordinates_have_at_most_six_decimals(kit_geojson):
    for feature in kit_geojson["features"][:20]:
        for ring in feature["geometry"]["coordinates"]:
            for lon, lat in ring:
                assert lon == round(lon, 6) and lat == round(lat, 6)


def test_kit_polygons_are_valid_and_inside_study_area(kit_geojson):
    study_area = shape(STUDY_AREA["features"][0]["geometry"]).buffer(1e-6)

    assert kit_geojson["type"] == "FeatureCollection"
    for feature in kit_geojson["features"]:
        polygon = shape(feature["geometry"])
        assert polygon.is_valid
        assert study_area.contains(polygon)


def test_kit_geojson_serializes_and_is_deterministic(kit_geojson):
    image = read_image(KIT_IMAGE.read_bytes())
    params = Params()
    index = ndvi(image.red, image.nir, image.valid)
    classification = classify(
        image, quality_mask(image, params, KIT_SCL.read_bytes()), index, params
    )

    again = vectorize(image, classification, index, params)

    assert json.dumps(again) == json.dumps(kit_geojson)


def test_empty_result_is_an_empty_feature_collection():
    geojson = synthetic(np.zeros((20, 20), dtype=bool))

    assert geojson == {"type": "FeatureCollection", "features": []}


def test_kit_corners_match_study_area():
    image = read_image(KIT_IMAGE.read_bytes())

    corners = corners_wgs84(image)

    ring = STUDY_AREA["features"][0]["geometry"]["coordinates"][0][:4]
    # area_estudo.geojson começa no canto inferior esquerdo e gira anti-horário.
    bottom_left, bottom_right, top_right, top_left = ring
    expected = [top_left, top_right, bottom_right, bottom_left]
    for got, want in zip(corners, expected, strict=True):
        assert got == pytest.approx(want, abs=1e-6)


def test_kit_stats_shape():
    image = read_image(KIT_IMAGE.read_bytes())
    params = Params()
    index = ndvi(image.red, image.nir, image.valid)
    classification = classify(
        image, quality_mask(image, params, KIT_SCL.read_bytes()), index, params
    )

    stats = build_stats(image, classification, index, polygon_count=3)

    assert stats["polygon_count"] == 3
    assert stats["gndvi"] is None
    assert stats["ndvi"]["min"] == pytest.approx(-0.434, abs=1e-3)
    assert stats["ndvi"]["max"] == pytest.approx(0.886, abs=1e-3)
    assert stats["ndvi"]["p5"] < stats["ndvi"]["median"] < stats["ndvi"]["p95"]
    assert set(stats["excluded_area_ha"]) == {
        "no_data",
        "quality_mask",
        "low_vegetation",
        "dense_canopy",
        "low_chlorophyll",
        "small_patch",
    }
    json.dumps(stats)  # só tipos nativos (sem numpy) para gravar no jsonb


def test_index_summary_without_valid_pixels_is_none():
    assert index_summary(np.zeros((2, 2)), np.zeros((2, 2), dtype=bool)) is None


def test_gndvi_mean_per_feature_and_stats():
    image = read_image(make_tiff(np.full((4, 20, 20), 2000)))
    levels = np.full(image.shape, CODES["low_vegetation"], dtype=np.uint8)
    levels[2:12, 2:12] = POTENTIAL
    classification = Classification(levels=levels, pixel_area_ha=image.pixel_area_ha)
    ndvi_values = np.full(image.shape, 0.6, dtype=np.float32)
    gndvi_values = np.full(image.shape, 0.2, dtype=np.float32)
    gndvi_values[2:12, 2:12] = 0.55

    geojson = vectorize(image, classification, ndvi_values, Params(), gndvi=gndvi_values)
    stats = build_stats(image, classification, ndvi_values, 1, gndvi=gndvi_values)

    assert geojson["features"][0]["properties"]["gndvi_mean"] == 0.55
    assert stats["gndvi"]["min"] == pytest.approx(0.2)
    assert stats["gndvi"]["max"] == pytest.approx(0.55)


def test_kit_reports_gndvi():
    image = read_image(KIT_IMAGE.read_bytes())
    params = Params()
    index = ndvi(image.red, image.nir, image.valid)
    green_index = gndvi(image.green, image.nir, image.valid)
    quality = quality_mask(image, params, KIT_SCL.read_bytes())
    classification = classify(image, quality, index, params, gndvi=green_index)

    geojson = vectorize(image, classification, index, params, gndvi=green_index)
    stats = build_stats(image, classification, index, len(geojson["features"]), gndvi=green_index)

    assert all(isinstance(f["properties"]["gndvi_mean"], float) for f in geojson["features"])
    assert -1 <= stats["gndvi"]["min"] < stats["gndvi"]["median"] < stats["gndvi"]["max"] <= 1
    # Calibração (T2.5): gndvi_min = null, então o GNDVI não exclui nada no kit.
    assert stats["excluded_area_ha"]["low_chlorophyll"] == 0
