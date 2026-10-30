"""Justificativa técnica (T2.9, R2.18; C1.1, C1.2, C5.2)."""

import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.processing.classification import EXCLUSION_LEVELS
from app.processing.params import METHOD_REFERENCES, METHOD_VERSION, Params
from app.processing.rationale import br, build_rationale

DESIGN = Path(__file__).resolve().parents[2] / "specs" / "002-processamento-classificacao"
AUGUST = datetime(2025, 8, 16, tzinfo=UTC)


def stats(polygon_count: int = 124, potential: float = 214.54) -> dict:
    excluded = dict.fromkeys(EXCLUSION_LEVELS, 0.0)
    excluded.update(low_vegetation=1279.76, dense_canopy=870.46, small_patch=256.68)
    return {
        "total_area_ha": 2621.44,
        "potential_area_ha": potential,
        "polygon_count": polygon_count,
        "excluded_area_ha": excluded,
    }


def all_text(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [t for v in value.values() for t in all_text(v)]
    if isinstance(value, list):
        return [t for v in value for t in all_text(v)]
    return []


def test_steps_numbers_come_from_params_and_stats():
    params = Params()
    numbers = stats()

    rationale = build_rationale(params, numbers, "scl", AUGUST)

    steps = {s["name"]: s for s in rationale["steps"]}
    assert [s["level"] for s in rationale["steps"]] == ["N0", "N1", "N2", "N3", "N4"]
    for name, step in steps.items():
        assert step["excluded_ha"] == numbers["excluded_area_ha"][name]
    assert steps["low_vegetation"]["threshold"] == params.ndvi_min
    assert steps["low_vegetation"]["rule"] == "NDVI < 0,55"
    assert steps["dense_canopy"]["rule"] == "NDVI > 0,72"
    assert "0,5 ha" in steps["small_patch"]["rule"]
    assert rationale["method_version"] == METHOD_VERSION
    assert "214,54 ha" in rationale["summary"] and "124 polígonos" in rationale["summary"]
    assert "2.621,44 ha" in rationale["summary"]


def test_gndvi_step_only_when_threshold_is_set():
    without = build_rationale(Params(), stats(), "scl", AUGUST)
    with_gndvi = build_rationale(Params(gndvi_min=0.4), stats(), "scl", AUGUST)

    assert "N3b" not in [s["level"] for s in without["steps"]]
    step = next(s for s in with_gndvi["steps"] if s["level"] == "N3b")
    assert step["rule"] == "GNDVI < 0,4"
    assert "gitelson1996" in [r["key"] for r in with_gndvi["references"]]


def test_references_only_from_the_fixed_list():
    rationale = build_rationale(Params(gndvi_min=0.4), stats(), "ndwi", None)

    keys = [r["key"] for r in rationale["references"]]
    assert set(keys) <= set(METHOD_REFERENCES)
    assert len(keys) == len(set(keys))
    for step in rationale["steps"]:
        assert set(step["references"]) <= set(keys)


def test_fixed_references_are_checked_in_the_design():
    # C5.2: cada chave precisa estar na tabela "Referências" do design e não
    # pode estar marcada "a conferir".
    design = (DESIGN / "design.md").read_text()
    table = design[design.index("## Referências") :]
    for key in METHOD_REFERENCES:
        row = next(line for line in table.splitlines() if line.startswith(f"| {key} |"))
        assert "a conferir" not in row.lower(), key


def test_no_detection_claims_or_accuracy_numbers():
    rationale = build_rationale(Params(gndvi_min=0.4), stats(), "ndwi", None)

    for text in all_text(rationale):
        lowered = text.lower()
        assert "café detectado" not in lowered
        assert "cafezal" not in lowered
        assert "acurácia de" not in lowered
        assert not re.search(r"\d\s?%", text), text


def test_empty_result_summary():
    rationale = build_rationale(Params(), stats(polygon_count=0, potential=0), "scl", AUGUST)

    assert "nenhuma área" in rationale["summary"]
    assert "polígono" not in rationale["summary"]


def test_singular_polygon():
    rationale = build_rationale(Params(), stats(polygon_count=1, potential=0.5), "scl", AUGUST)

    assert "em 1 polígono," in rationale["summary"]


def test_scl_and_ndwi_masks():
    scl = build_rationale(Params(), stats(), "scl", AUGUST)
    ndwi = build_rationale(Params(), stats(), "ndwi", AUGUST)

    assert scl["masks"] == {
        "source": "scl",
        "classes_excluded": [0, 1, 3, 6, 8, 9, 10, 11],
        "ndwi_water_min": None,
        "second_source": None,
    }
    assert ndwi["masks"] == {
        "source": "ndwi",
        "classes_excluded": None,
        "ndwi_water_min": 0.0,
        "second_source": None,
    }
    assert ndwi["steps"][1]["rule"] == "NDWI > 0"
    assert any("Sem a SCL" in limitation for limitation in ndwi["limitations"])
    assert not any("Sem a SCL" in limitation for limitation in scl["limitations"])


@pytest.mark.parametrize(
    ("acquired_at", "extra"),
    [
        (AUGUST, None),
        (datetime(2025, 1, 10, tzinfo=UTC), "fora da estação seca"),
        (None, "não informada"),
    ],
)
def test_season_limitation(acquired_at, extra):
    limitations = build_rationale(Params(), stats(), "scl", acquired_at)["limitations"]

    seasonal = [text for text in limitations if "estação seca" in text]
    if extra is None:
        assert seasonal == []
    else:
        assert len(seasonal) == 1 and extra in seasonal[0]


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (2621.44, "2.621,44"),
        (0.55, "0,55"),
        (0.5, "0,5"),
        (0, "0"),
        (1000, "1.000"),
        (-0.1, "-0,1"),
    ],
)
def test_brazilian_number_format(value, text):
    assert br(value) == text


def test_single_date_has_no_amplitude_step():
    rationale = build_rationale(Params(), stats(), "scl", AUGUST)

    assert "high_amplitude" not in [step["name"] for step in rationale["steps"]]
    assert "uma única imagem" in rationale["summary"]
    assert rationale["limitations"][0].startswith("Uma única data")


def test_two_dates_add_amplitude_step_and_change_limitation():
    two = stats()
    two["excluded_area_ha"]["high_amplitude"] = 111.54
    rationale = build_rationale(Params(), two, "scl", AUGUST, second_quality_source="scl")

    names = [step["name"] for step in rationale["steps"]]
    # N3c depois dos níveis espectrais e antes das manchas pequenas.
    assert names[-2:] == ["high_amplitude", "small_patch"]
    step = rationale["steps"][-2]
    assert step["level"] == "N3c"
    assert step["rule"] == "|NDVI da segunda data − NDVI| ≥ 0,25"
    assert step["threshold"] == 0.25
    assert step["excluded_ha"] == 111.54
    assert step["references"] == ["souza2019"]
    assert "duas datas" in rationale["summary"]
    assert "vale para as duas" in rationale["steps"][1]["why"]
    assert rationale["limitations"][0].startswith("Duas datas, sem série temporal")
    assert not any("Uma única data" in text for text in rationale["limitations"])
    assert rationale["masks"]["second_source"] == "scl"


def test_second_image_without_scl_is_a_limitation():
    rationale = build_rationale(Params(), stats(), "scl", AUGUST, second_quality_source="ndwi")

    assert any("Sem a SCL da segunda imagem" in text for text in rationale["limitations"])
    assert not any(text.startswith("Sem a SCL, só") for text in rationale["limitations"])
