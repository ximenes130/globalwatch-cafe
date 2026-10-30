"""Áreas: kit = 2.621,44 ha e somas fechadas (T2.7, R2.12, R2.14, R2.15)."""

import numpy as np
import pytest

from app.processing.classification import CODES, POTENTIAL, Classification, classify
from app.processing.indices import ndvi
from app.processing.masking import quality_mask
from app.processing.params import Params
from app.processing.reader import read_image
from app.processing.vectorization import build_stats, patch_polygons, vectorize
from tests.rasters import KIT_IMAGE, KIT_SCL, make_tiff


@pytest.fixture(scope="module")
def kit():
    image = read_image(KIT_IMAGE.read_bytes())
    params = Params()
    index = ndvi(image.red, image.nir, image.valid)
    classification = classify(
        image, quality_mask(image, params, KIT_SCL.read_bytes()), index, params
    )
    geojson = vectorize(image, classification, index, params)
    stats = build_stats(image, classification, index, len(geojson["features"]))
    return image, params, classification, geojson, stats


def test_kit_total_area(kit):
    _, _, _, _, stats = kit

    assert stats["total_area_ha"] == 2621.44
    assert stats["valid_area_ha"] == 2621.44
    assert stats["masked_area_ha"] == 0


def test_kit_areas_close_with_total(kit):
    _, _, _, _, stats = kit

    excluded = sum(stats["excluded_area_ha"].values())
    assert stats["potential_area_ha"] + excluded == pytest.approx(stats["total_area_ha"], abs=1e-6)


def test_feature_areas_add_up_to_potential_area(kit):
    _, _, classification, geojson, stats = kit

    feature_total = sum(f["properties"]["area_ha"] for f in geojson["features"])
    assert feature_total == pytest.approx(stats["potential_area_ha"], abs=1e-6)
    assert stats["potential_area_ha"] == pytest.approx(classification.potential.sum() * 0.01)
    assert stats["polygon_count"] == len(geojson["features"]) > 0


def test_half_pixel_simplification_keeps_the_pixel_area(kit):
    # Com 0,5 pixel só saem vértices colineares: o contorno em escada fica e a
    # área desenhada é a da contagem de pixels (medido em 30/10: −31% de
    # vértices no kit). Tolerância maior já distorce manchas pequenas.
    image, params, classification, _, _ = kit

    patches = patch_polygons(image, classification, params)

    for patch in patches:
        assert patch.polygon.area == pytest.approx(patch.pixels * 100, rel=1e-9)


def test_stats_with_nodata_and_mask():
    dn = np.full((4, 10, 10), 2000)
    dn[:, 0, :] = 0  # primeira linha sem dado
    image = read_image(make_tiff(dn))
    levels = np.full(image.shape, CODES["low_vegetation"], dtype=np.uint8)
    levels[0, :] = CODES["no_data"]
    levels[1, :5] = CODES["quality_mask"]
    classification = Classification(levels=levels, pixel_area_ha=image.pixel_area_ha)
    index = np.full(image.shape, 0.3, dtype=np.float32)

    stats = build_stats(image, classification, index, polygon_count=0)

    assert stats["total_area_ha"] == 1.0
    assert stats["valid_area_ha"] == 0.9
    assert stats["masked_area_ha"] == 0.05
    assert stats["potential_area_ha"] == 0
    assert stats["excluded_area_ha"]["no_data"] == 0.1


def test_area_is_measured_in_the_projected_grid():
    # Bloco de 10 x 10 pixels de 10 m = 1 ha, qualquer que seja a latitude.
    image = read_image(make_tiff(np.full((4, 20, 20), 2000)))
    levels = np.full(image.shape, CODES["low_vegetation"], dtype=np.uint8)
    levels[5:15, 5:15] = POTENTIAL
    classification = Classification(levels=levels, pixel_area_ha=image.pixel_area_ha)
    index = np.full(image.shape, 0.6, dtype=np.float32)

    geojson = vectorize(image, classification, index, Params())

    assert [f["properties"]["area_ha"] for f in geojson["features"]] == [1.0]
