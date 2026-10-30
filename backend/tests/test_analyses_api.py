"""Rotas `/analyses` com banco, Storage e usuário substituídos (T2.11).

O `TestClient` roda as background tasks logo depois da resposta, então o GET
seguinte ao POST já vê a análise terminada.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.auth import CurrentUser, current_user
from app.config import get_settings
from app.main import app
from app.ratelimit import get_usage
from app.repository import STALE_MESSAGE
from app.routes.analyses import get_repository, get_storage
from tests.fakes import FakeRepository, FakeStorage, FakeUsage
from tests.rasters import ADDITIONAL_IMAGE, ADDITIONAL_SCL, KIT_IMAGE, KIT_SCL

OWNER = CurrentUser(id=UUID("11111111-1111-1111-1111-111111111111"), email="dono@test")
OTHER = CurrentUser(id=UUID("22222222-2222-2222-2222-222222222222"), email="outro@test")


@pytest.fixture
def api():
    repository = FakeRepository()
    storage = FakeStorage()
    state = {"user": OWNER}
    app.dependency_overrides[current_user] = lambda: state["user"]
    app.dependency_overrides[get_repository] = lambda: repository
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_usage] = FakeUsage
    with TestClient(app) as client:
        yield client, repository, storage, state
    app.dependency_overrides.clear()


def post_kit(client, scl: bool = True):
    files = {"image": ("imagem_multiespectral.tif", KIT_IMAGE.read_bytes(), "image/tiff")}
    if scl:
        files["scl"] = ("qualidade_scl.tif", KIT_SCL.read_bytes(), "image/tiff")
    return client.post("/analyses", files=files)


def test_post_answers_202_and_processes_in_background(api):
    client, repository, storage, _ = api

    response = post_kit(client)

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "processing"
    assert response.headers["location"] == f"/analyses/{body['id']}"

    detail = client.get(f"/analyses/{body['id']}").json()
    assert detail["status"] == "completed"
    assert detail["filename"] == "imagem_multiespectral.tif"
    assert detail["stats"]["total_area_ha"] == 2621.44
    assert detail["rationale"]["summary"].startswith("Regras espectrais")
    assert set(detail["urls"]) == {"rgb_png", "classification_png", "polygons_png", "geojson"}
    assert "user_id" not in detail
    assert len(storage.objects) == 6


def test_post_with_second_date_applies_amplitude_rule(api):
    client, _, storage, _ = api
    files = {
        "image": ("imagem_multiespectral.tif", KIT_IMAGE.read_bytes(), "image/tiff"),
        "scl": ("qualidade_scl.tif", KIT_SCL.read_bytes(), "image/tiff"),
        "image_2": ("chuva.tif", ADDITIONAL_IMAGE.read_bytes(), "image/tiff"),
        "scl_2": ("chuva_scl.tif", ADDITIONAL_SCL.read_bytes(), "image/tiff"),
    }

    analysis_id = client.post("/analyses", files=files).json()["id"]

    detail = client.get(f"/analyses/{analysis_id}").json()
    assert detail["status"] == "completed"
    assert detail["filename"] == "imagem_multiespectral.tif"
    assert detail["stats"]["potential_area_ha"] == 103.04
    assert detail["params"]["second_image"]["acquired_at"].startswith("2026-01-10")
    assert "high_amplitude" in [step["name"] for step in detail["rationale"]["steps"]]
    assert len(storage.objects) == 8

    assert client.delete(f"/analyses/{analysis_id}").status_code == 204
    assert storage.objects == {}


def test_second_scl_without_second_image_is_422(api):
    client, repository, _, _ = api
    files = {
        "image": ("k.tif", KIT_IMAGE.read_bytes(), "image/tiff"),
        "scl_2": ("s.tif", KIT_SCL.read_bytes(), "image/tiff"),
    }

    response = client.post("/analyses", files=files)

    assert response.status_code == 422
    assert response.json()["detail"] == "Envie a segunda imagem junto da SCL dela."
    assert repository.rows == {}


def test_second_image_on_another_grid_fails_with_message(api):
    client, _, _, _ = api
    files = {
        "image": ("k.tif", KIT_IMAGE.read_bytes(), "image/tiff"),
        "image_2": ("x.tif", KIT_SCL.read_bytes(), "image/tiff"),
    }

    analysis_id = client.post("/analyses", files=files).json()["id"]

    detail = client.get(f"/analyses/{analysis_id}").json()
    assert detail["status"] == "failed"
    assert detail["error"].startswith("Segunda imagem:")


def test_second_image_over_the_limit_is_413(api, monkeypatch):
    client, repository, _, _ = api
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    get_settings.cache_clear()
    files = {
        "image": ("k.tif", b"0", "image/tiff"),
        "image_2": ("big.tif", b"0" * (1024 * 1024 + 1), "image/tiff"),
    }

    assert client.post("/analyses", files=files).status_code == 413
    assert repository.rows == {}


def test_processing_analysis_has_no_result_yet(api):
    client, repository, _, _ = api
    analysis_id = repository.create(OWNER.id, "kit.tif")

    detail = client.get(f"/analyses/{analysis_id}").json()

    assert detail["status"] == "processing"
    assert detail["stats"] is None and detail["urls"] is None
    assert detail["created_at"]


def test_unreadable_file_ends_as_failed_with_message(api):
    client, _, _, _ = api

    response = client.post("/analyses", files={"image": ("x.tif", b"nao e tiff", "image/tiff")})

    detail = client.get(f"/analyses/{response.json()['id']}").json()
    assert detail["status"] == "failed"
    assert detail["error"] == "Não foi possível ler a imagem enviada como GeoTIFF."
    assert detail["urls"] is None


def test_upload_over_the_limit_is_413_and_creates_nothing(api, monkeypatch):
    client, repository, _, _ = api
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    get_settings.cache_clear()

    response = client.post(
        "/analyses", files={"image": ("big.tif", b"0" * (1024 * 1024 + 1), "image/tiff")}
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "O arquivo passa do limite de 1 MB."
    assert repository.rows == {}


def test_missing_image_is_422(api):
    client, _, _, _ = api

    assert client.post("/analyses", files={}).status_code == 422


def test_filename_keeps_only_the_name(api):
    client, repository, _, _ = api

    client.post("/analyses", files={"image": ("../../etc/kit.tif", b"x", "image/tiff")})

    assert [row["filename"] for row in repository.rows.values()] == ["kit.tif"]


def test_list_is_per_user_and_newest_first(api):
    client, repository, _, state = api
    older = repository.create(OWNER.id, "a.tif")
    repository.rows[older]["created_at"] -= timedelta(minutes=5)
    newer = repository.create(OWNER.id, "b.tif")
    repository.create(OTHER.id, "alheia.tif")

    items = client.get("/analyses").json()

    assert [item["id"] for item in items] == [str(newer), str(older)]
    assert set(items[0]) == {
        "id",
        "filename",
        "created_at",
        "status",
        "acquired_at",
        "potential_area_ha",
    }
    state["user"] = OTHER
    assert [item["filename"] for item in client.get("/analyses").json()] == ["alheia.tif"]


def test_stale_processing_becomes_failed_on_read(api):
    client, repository, _, _ = api
    stale = repository.create(OWNER.id, "velha.tif")
    repository.rows[stale]["created_at"] = datetime.now(UTC) - timedelta(minutes=20)
    fresh = repository.create(OWNER.id, "nova.tif")

    by_id = {item["id"]: item for item in client.get("/analyses").json()}

    assert by_id[str(stale)]["status"] == "failed"
    assert by_id[str(fresh)]["status"] == "processing"
    assert client.get(f"/analyses/{stale}").json()["error"] == STALE_MESSAGE


def test_other_users_analysis_is_404(api):
    client, repository, _, state = api
    analysis_id = repository.create(OWNER.id, "kit.tif")
    state["user"] = OTHER

    assert client.get(f"/analyses/{analysis_id}").status_code == 404
    assert client.delete(f"/analyses/{analysis_id}").status_code == 404
    assert client.get(f"/analyses/{uuid4()}").status_code == 404
    assert analysis_id in repository.rows


def test_delete_processing_is_409(api):
    client, repository, _, _ = api
    analysis_id = repository.create(OWNER.id, "kit.tif")

    response = client.delete(f"/analyses/{analysis_id}")

    assert response.status_code == 409
    assert analysis_id in repository.rows


def test_delete_removes_files_then_row(api):
    client, repository, storage, _ = api
    analysis_id = post_kit(client).json()["id"]
    assert storage.objects

    response = client.delete(f"/analyses/{analysis_id}")

    assert response.status_code == 204
    assert storage.objects == {}
    assert repository.rows == {}


def test_delete_keeps_row_when_storage_fails(api):
    client, repository, storage, _ = api
    analysis_id = post_kit(client, scl=False).json()["id"]
    storage.fail_remove = True

    assert client.delete(f"/analyses/{analysis_id}").status_code == 503
    assert UUID(analysis_id) in repository.rows


def test_routes_require_authentication():
    with TestClient(app) as client:
        assert client.get("/analyses").status_code == 401
        assert client.post("/analyses", files={"image": ("k.tif", b"x")}).status_code == 401
        assert client.get(f"/analyses/{uuid4()}").status_code == 401
        assert client.delete(f"/analyses/{uuid4()}").status_code == 401


def test_without_database_or_storage_key_is_503():
    app.dependency_overrides[current_user] = lambda: OWNER
    try:
        with TestClient(app) as client:
            assert client.get("/analyses").status_code == 503  # DATABASE_URL vazia nos testes
            app.dependency_overrides[get_repository] = FakeRepository
            response = client.post("/analyses", files={"image": ("k.tif", b"x")})
            assert response.status_code == 503
            assert response.json()["detail"] == "Armazenamento indisponível."
    finally:
        app.dependency_overrides.clear()
