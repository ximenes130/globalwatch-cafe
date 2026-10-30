"""`GET /me/usage`: os números que a interface mostra (T6.8, R6.16, R6.19)."""

from datetime import UTC, datetime, timedelta
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


class Model:
    messages = None

    def __init__(self):
        self.messages = self

    def create(self, **_):
        usage = SimpleNamespace(input_tokens=1, output_tokens=1)
        return SimpleNamespace(
            stop_reason="end_turn", stop_details=None, content=[TEXT], usage=usage
        )


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(analyses, "run_analysis", lambda *args, **kwargs: None)
    repository, usage = FakeRepository(), FakeUsage()
    state = {"user": OWNER}
    app.dependency_overrides[current_user] = lambda: state["user"]
    app.dependency_overrides[get_repository] = lambda: repository
    app.dependency_overrides[get_storage] = FakeStorage
    app.dependency_overrides[get_usage] = lambda: usage
    app.dependency_overrides[get_chat_client] = Model
    app.dependency_overrides[get_chat_repository] = FakeChatRepository
    with TestClient(app) as client:
        yield SimpleNamespace(client=client, repository=repository, state=state)
    app.dependency_overrides.clear()


def test_fresh_user_has_everything_left(api):
    settings = get_settings()
    body = api.client.get("/me/usage").json()

    tomorrow = datetime.now(UTC).date() + timedelta(days=1)
    assert body == {
        "uploads": {"used": 0, "limit": settings.max_uploads_per_day},
        "messages": {"used": 0, "limit": settings.max_messages_per_day},
        "resets_at": f"{tomorrow.isoformat()}T00:00:00Z",
        "retention_days": 7,
    }


def test_usage_follows_uploads_and_messages_without_counting_itself(api):
    files = {"image": ("kit.tif", KIT_IMAGE.read_bytes(), "image/tiff")}
    for _ in range(2):
        api.client.post("/analyses", files=files)
    analysis_id = next(iter(api.repository.rows))
    api.repository.rows[analysis_id]["status"] = "completed"
    for _ in range(3):
        api.client.post(f"/analyses/{analysis_id}/chat", json={"message": "Oi"})

    for _ in range(3):  # ler não gasta
        body = api.client.get("/me/usage").json()

    assert body["uploads"]["used"] == 2
    assert body["messages"]["used"] == 3


def test_each_user_sees_their_own_numbers(api):
    api.client.post("/analyses", files={"image": ("kit.tif", KIT_IMAGE.read_bytes(), "image/tiff")})
    api.state["user"] = OTHER

    assert api.client.get("/me/usage").json()["uploads"]["used"] == 0
