"""Limites diários de upload e de chat (T6.4, R6.8, R6.9).

Rotas com o contador em memória; o SQL atômico é testado contra Postgres em
`test_repository.py`.
"""

from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.auth import CurrentUser, current_user
from app.config import get_settings
from app.main import app
from app.ratelimit import get_usage
from app.routes import analyses
from app.routes.analyses import get_repository, get_storage
from app.routes.chat import get_chat_client, get_chat_repository
from tests.fakes import FakeChatRepository, FakeRepository, FakeStorage, FakeUsage
from tests.rasters import KIT_IMAGE

OWNER = CurrentUser(id=UUID("11111111-1111-1111-1111-111111111111"), email="dono@test")
OTHER = CurrentUser(id=UUID("22222222-2222-2222-2222-222222222222"), email="outro@test")
TEXT = SimpleNamespace(type="text", text="Resposta.")


class CountingModel:
    def __init__(self):
        self.calls = 0
        self.messages = self

    def create(self, **_):
        self.calls += 1
        return SimpleNamespace(
            stop_reason="end_turn",
            stop_details=None,
            content=[TEXT],
            usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        )


@pytest.fixture
def api(monkeypatch):
    # Só a contagem importa aqui: o pipeline não roda.
    monkeypatch.setattr(analyses, "run_analysis", lambda *args, **kwargs: None)
    repository, usage, model = FakeRepository(), FakeUsage(), CountingModel()
    state = {"user": OWNER}
    app.dependency_overrides[current_user] = lambda: state["user"]
    app.dependency_overrides[get_repository] = lambda: repository
    app.dependency_overrides[get_storage] = FakeStorage
    app.dependency_overrides[get_usage] = lambda: usage
    app.dependency_overrides[get_chat_client] = lambda: model
    app.dependency_overrides[get_chat_repository] = FakeChatRepository
    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client, repository=repository, usage=usage, model=model, state=state
        )
    app.dependency_overrides.clear()


def limits() -> tuple[int, int]:
    # Os valores vêm da configuração: mudar o limite não quebra o teste.
    settings = get_settings()
    return settings.max_uploads_per_day, settings.max_messages_per_day


def upload(client, data: bytes | None = None):
    image = data if data is not None else KIT_IMAGE.read_bytes()
    return client.post("/analyses", files={"image": ("kit.tif", image, "image/tiff")})


def test_upload_past_the_daily_limit_is_429_and_creates_nothing(api):
    max_uploads, _ = limits()
    for _ in range(max_uploads):
        assert upload(api.client).status_code == 202

    response = upload(api.client)

    assert response.status_code == 429
    assert response.json()["detail"] == (
        f"Você chegou ao limite de {max_uploads} envios de imagem por dia. Tente de novo amanhã."
    )
    assert len(api.repository.rows) == max_uploads


def test_upload_limit_is_per_user(api):
    max_uploads, _ = limits()
    for _ in range(max_uploads):
        upload(api.client)
    api.state["user"] = OTHER

    assert upload(api.client).status_code == 202


def test_rejected_upload_does_not_count(api, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")  # o kit tem ~1,4 MB
    get_settings.cache_clear()

    assert upload(api.client).status_code == 413
    assert api.usage.counts == {}


def test_message_past_the_daily_limit_is_429_without_calling_the_model(api):
    _, max_messages = limits()
    analysis_id = api.repository.create(OWNER.id, "kit.tif")
    api.repository.rows[analysis_id]["status"] = "completed"
    url = f"/analyses/{analysis_id}/chat"

    for _ in range(max_messages):
        assert api.client.post(url, json={"message": "Oi"}).status_code == 200

    response = api.client.post(url, json={"message": "Oi"})

    assert response.status_code == 429
    assert response.json()["detail"] == (
        f"Você chegou ao limite de {max_messages} mensagens no chat por dia. Tente de novo amanhã."
    )
    assert api.model.calls == max_messages


def test_chat_on_someone_elses_analysis_does_not_count(api):
    analysis_id = api.repository.create(OWNER.id, "kit.tif")
    api.repository.rows[analysis_id]["status"] = "completed"
    api.state["user"] = OTHER

    response = api.client.post(f"/analyses/{analysis_id}/chat", json={"message": "Oi"})

    assert response.status_code == 404
    assert api.usage.counts == {}
