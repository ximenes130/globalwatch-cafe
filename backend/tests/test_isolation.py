"""Isolamento entre usuários (T6.2, R6.2, R6.3, R6.4, R6.14).

A matriz de rotas sai do próprio app: uma rota nova com `{analysis_id}` entra no teste
sem ninguém lembrar dela. O filtro por `user_id` no SQL é testado contra Postgres em
`test_repository.py`, e a RLS em `supabase/tests/rls_isolation.sql`.
"""

import json
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.auth import CurrentUser, current_user
from app.main import app
from app.ratelimit import get_usage
from app.routes.analyses import ALL_FILES, get_repository, get_storage
from app.routes.chat import get_chat_client, get_chat_repository
from app.storage import SupabaseStorage, object_prefix
from tests.fakes import FakeChatRepository, FakeRepository, FakeStorage, FakeUsage
from tests.rasters import KIT_IMAGE, KIT_SCL

OWNER = CurrentUser(id=UUID("11111111-1111-1111-1111-111111111111"), email="dono@test")
OTHER = CurrentUser(id=UUID("22222222-2222-2222-2222-222222222222"), email="outro@test")


class NoModel:
    """Chamar o modelo numa análise alheia já seria vazamento."""

    @property
    def messages(self):
        raise AssertionError("o modelo não deveria ser chamado")


@pytest.fixture(scope="module")
def world():
    repository, storage, chat = FakeRepository(), FakeStorage(), FakeChatRepository()
    state = {"user": OWNER}
    app.dependency_overrides[current_user] = lambda: state["user"]
    app.dependency_overrides[get_repository] = lambda: repository
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_usage] = FakeUsage
    app.dependency_overrides[get_chat_client] = NoModel
    app.dependency_overrides[get_chat_repository] = lambda: chat
    with TestClient(app) as client:
        files = {
            "image": ("imagem.tif", KIT_IMAGE.read_bytes(), "image/tiff"),
            "scl": ("scl.tif", KIT_SCL.read_bytes(), "image/tiff"),
        }
        analysis_id = UUID(client.post("/analyses", files=files).json()["id"])
        chat.append(OWNER.id, analysis_id, [{"role": "assistant", "content": "Oi.", "cards": []}])
        yield SimpleNamespace(
            client=client,
            state=state,
            repository=repository,
            storage=storage,
            chat=chat,
            analysis_id=analysis_id,
        )
    app.dependency_overrides.clear()


def analysis_routes() -> list[tuple[str, str]]:
    # Pelo OpenAPI: esta versão do FastAPI não expõe as rotas dos routers incluídos em
    # `app.routes`, e o schema lista todas.
    paths = app.openapi()["paths"]
    return sorted(
        (method.upper(), path)
        for path, operations in paths.items()
        if "{analysis_id}" in path
        for method in operations
    )


BODIES = {"POST": {"message": "Mostre os dados"}}


def test_every_analysis_route_is_in_the_matrix():
    # Se esta lista mudar, a matriz abaixo cobre a rota nova automaticamente.
    assert analysis_routes() == [
        ("DELETE", "/analyses/{analysis_id}"),
        ("GET", "/analyses/{analysis_id}"),
        ("GET", "/analyses/{analysis_id}/chat"),
        ("POST", "/analyses/{analysis_id}/chat"),
    ]


@pytest.mark.parametrize(("method", "path"), analysis_routes())
def test_other_users_analysis_is_404_on_every_route(world, method, path):
    world.state["user"] = OTHER
    try:
        url = path.format(analysis_id=world.analysis_id)
        response = world.client.request(method, url, json=BODIES.get(method))
    finally:
        world.state["user"] = OWNER

    # 404, e não 403: não revela que o id existe (R6.2).
    assert response.status_code == 404
    assert response.json() == {"detail": "Análise não encontrada."}
    # Nada mudou para o dono.
    assert world.repository.get(OWNER.id, world.analysis_id) is not None
    assert len(world.chat.history(OWNER.id, world.analysis_id)) == 1


def test_other_users_list_is_empty(world):
    world.state["user"] = OTHER
    try:
        assert world.client.get("/analyses").json() == []
    finally:
        world.state["user"] = OWNER
    assert len(world.client.get("/analyses").json()) == 1


def test_files_live_under_user_then_analysis(world):
    prefix = f"{OWNER.id}/{world.analysis_id}/"

    assert world.storage.objects
    assert all(path.startswith(prefix) for path in world.storage.objects)
    assert object_prefix(OWNER.id, world.analysis_id) == prefix.rstrip("/")


def test_signed_urls_last_five_minutes(monkeypatch):
    sent = {}

    def fake_request(self, method, path, body, headers, raw=False):
        sent.update(json.loads(body))
        return [
            {"path": p, "signedURL": f"/object/sign/analyses/{p}?token=t"} for p in sent["paths"]
        ]

    monkeypatch.setattr(SupabaseStorage, "_request", fake_request)
    storage = SupabaseStorage("https://proj.supabase.co", "sb_secret_x", "analyses", 300)

    url = storage.signed_urls(["u/a/rgb.png"])["u/a/rgb.png"]

    assert sent["expiresIn"] == 300
    assert parse_qs(urlparse(url).query)["token"] == ["t"]


def test_delete_removes_files_row_and_messages(world):
    prefix = object_prefix(OWNER.id, world.analysis_id)
    # O DELETE pede ao Storage todos os arquivos possíveis da análise.
    removed = []
    original = world.storage.remove
    world.storage.remove = lambda paths: (removed.extend(paths), original(paths))
    try:
        response = world.client.delete(f"/analyses/{world.analysis_id}")
    finally:
        del world.storage.remove

    assert response.status_code == 204
    assert sorted(removed) == sorted(f"{prefix}/{name}" for name in ALL_FILES)
    assert not any(path.startswith(prefix) for path in world.storage.objects)
    assert world.repository.get(OWNER.id, world.analysis_id) is None
    # As mensagens saem por `on delete cascade` no banco (Postgres em test_repository.py);
    # pela API, a conversa da análise apagada já não é alcançável.
    assert world.client.get(f"/analyses/{world.analysis_id}/chat").status_code == 404
