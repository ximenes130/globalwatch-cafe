"""Ferramentas do chat sobre análises reais do kit (T5.1, R5.2, R5.5, R5.11, R5.13).

O pipeline roda de verdade (kit e kit + cena de janeiro) e grava nos dublês do banco e do
Storage; as ferramentas leem dali, como a rota do chat fará.
"""

import json
from uuid import UUID

import pytest
from shapely.geometry import shape

from app.chat.tools import TOOL_DEFINITIONS, AnalysisTools, ToolError
from app.storage import object_prefix
from app.worker import run_analysis
from tests.fakes import FakeRepository, FakeStorage
from tests.rasters import ADDITIONAL_IMAGE, ADDITIONAL_SCL, KIT_IMAGE, KIT_SCL

OWNER = UUID("11111111-1111-1111-1111-111111111111")
OTHER = UUID("22222222-2222-2222-2222-222222222222")


def processed(second_date: bool = False):
    repository, storage = FakeRepository(), FakeStorage()
    analysis_id = repository.create(OWNER, "imagem_multiespectral.tif")
    extra = (
        {"image_2": ADDITIONAL_IMAGE.read_bytes(), "scl_2": ADDITIONAL_SCL.read_bytes()}
        if second_date
        else {}
    )
    run_analysis(
        analysis_id,
        OWNER,
        KIT_IMAGE.read_bytes(),
        KIT_SCL.read_bytes(),
        repository,
        storage,
        **extra,
    )
    row = repository.get(OWNER, analysis_id)
    assert row["status"] == "completed"
    return repository, storage, analysis_id, row


@pytest.fixture(scope="module")
def kit():
    return processed()


@pytest.fixture(scope="module")
def two_dates():
    return processed(second_date=True)


def tools_for(fixture) -> AnalysisTools:
    _, storage, analysis_id, row = fixture
    return AnalysisTools(row, storage, object_prefix(OWNER, analysis_id))


def geojson(fixture) -> dict:
    _, storage, analysis_id, _ = fixture
    return json.loads(storage.download(f"{object_prefix(OWNER, analysis_id)}/result.geojson"))


def test_summary_has_the_stored_numbers(kit):
    row = kit[3]

    output = tools_for(kit).run("get_analysis_summary", {})

    assert output.kind == "summary"
    data = output.data
    assert data["filename"] == "imagem_multiespectral.tif"
    assert data["acquired_at"] == row["acquired_at"].isoformat()
    assert data["second_acquired_at"] is None
    assert data["total_area_ha"] == 2621.44
    assert data["potential_area_ha"] == 214.54
    assert data["polygon_count"] == 124
    for key in ("valid_area_ha", "masked_area_ha"):
        assert data[key] == row["stats"][key]
    assert data["excluded_area_ha"] == row["stats"]["excluded_area_ha"]
    # Ordem da cascata, como no painel.
    assert list(data["excluded_area_ha"])[0] == "no_data"
    assert list(data["excluded_area_ha"])[-1] == "small_patch"
    assert data["thresholds"] == {"ndvi_min": 0.55, "ndvi_max": 0.72, "min_area_ha": 0.5}
    assert data["method_version"] == row["method_version"]


def test_summary_with_second_date_exposes_the_amplitude_rule(two_dates):
    data = tools_for(two_dates).run("get_analysis_summary", {}).data

    assert data["second_acquired_at"].startswith("2026-01-10")
    assert data["thresholds"]["ndvi_amplitude_max"] == 0.25
    assert data["excluded_area_ha"]["high_amplitude"] == 101.78
    assert data["potential_area_ha"] == 103.04
    assert data["polygon_count"] == 68


def test_polygon_matches_the_geojson(kit):
    feature = next(f for f in geojson(kit)["features"] if f["properties"]["id"] == 31)

    output = tools_for(kit).run("get_polygon", {"id": 31})

    assert output.kind == "polygon"
    data = output.data
    assert data["id"] == 31
    assert data["area_ha"] == feature["properties"]["area_ha"] == 1.73
    assert data["ndvi_mean"] == feature["properties"]["ndvi_mean"] == 0.6273
    assert data["gndvi_mean"] == feature["properties"]["gndvi_mean"]
    centroid = shape(feature["geometry"]).centroid
    assert data["centroid"] == [round(centroid.x, 6), round(centroid.y, 6)]
    # Dentro da área de estudo do kit (Guaxupé/MG).
    assert -47 < data["centroid"][0] < -46 and -22 < data["centroid"][1] < -21


def test_geojson_is_downloaded_once_per_request(kit):
    _, storage, analysis_id, row = kit
    calls = []
    original = storage.download

    def counting(path):
        calls.append(path)
        return original(path)

    tools = AnalysisTools(row, storage, object_prefix(OWNER, analysis_id))
    storage.download = counting
    try:
        tools.run("get_polygon", {"id": 1})
        tools.run("get_polygon", {"id": 2})
    finally:
        del storage.download

    assert len(calls) == 1


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"id": 999}, "Polígono 999 não existe; a análise tem 124 polígonos (de 1 a 124)."),
        ({"id": 0}, "Polígono 0 não existe; a análise tem 124 polígonos (de 1 a 124)."),
        ({"id": "31"}, "Informe o número do polígono (inteiro a partir de 1)."),
        ({"id": True}, "Informe o número do polígono (inteiro a partir de 1)."),
        ({}, "Informe o número do polígono (inteiro a partir de 1)."),
    ],
)
def test_invalid_polygon_is_a_tool_error(kit, arguments, message):
    with pytest.raises(ToolError) as error:
        tools_for(kit).run("get_polygon", arguments)

    assert str(error.value) == message


def test_unknown_tool_is_a_tool_error(kit):
    with pytest.raises(ToolError):
        tools_for(kit).run("delete_analysis", {})


def test_storage_failure_is_a_tool_error(kit):
    _, _, analysis_id, row = kit
    tools = AnalysisTools(row, FakeStorage(), object_prefix(OWNER, analysis_id))

    with pytest.raises(ToolError, match="Não foi possível ler os polígonos"):
        tools.run("get_polygon", {"id": 1})


def test_limitations_come_from_the_rationale(two_dates):
    rationale = two_dates[3]["rationale"]

    output = tools_for(two_dates).run("get_limitations", {})

    assert output.kind == "limitations"
    assert output.data["items"] == rationale["limitations"]
    assert output.data["references"] == [
        {"citation": ref["citation"], "doi": ref["doi"]} for ref in rationale["references"]
    ]


def test_tools_reach_only_the_owners_folder(kit):
    # A pasta vem do dono da linha; outra pasta não tem os arquivos desta análise.
    _, storage, analysis_id, row = kit
    tools = AnalysisTools(row, storage, object_prefix(OTHER, analysis_id))

    with pytest.raises(ToolError):
        tools.run("get_polygon", {"id": 1})


def test_no_tool_takes_an_analysis_id():
    for tool in TOOL_DEFINITIONS:
        properties = tool["input_schema"]["properties"]
        assert not any("analysis" in name or name == "user_id" for name in properties)
        assert tool["input_schema"]["additionalProperties"] is False
