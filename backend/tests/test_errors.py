"""Erros sem detalhe interno e CORS só para o front (T6.5, R6.10, R6.12)."""

import logging
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.auth import CurrentUser, current_user
from app.main import app
from app.routes.analyses import get_repository

OWNER = CurrentUser(id=UUID("11111111-1111-1111-1111-111111111111"), email="dono@test")
FRONT = "http://localhost:5173"
SECRET = "falha em /srv/app/repository.py com sb_secret_abc123"


class BrokenRepository:
    def expire_stale(self, *args):
        raise RuntimeError(SECRET)


@pytest.fixture
def broken():
    app.dependency_overrides[current_user] = lambda: OWNER
    app.dependency_overrides[get_repository] = BrokenRepository
    # Sem relançar no cliente: o teste quer ver a resposta que o navegador veria.
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    app.dependency_overrides.clear()


def test_unexpected_error_is_neutral_json(broken, caplog):
    with caplog.at_level(logging.ERROR, logger="app.errors"):
        response = broken.get("/analyses", headers={"Origin": FRONT})

    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno do servidor. Tente de novo em instantes."}
    for leak in ("Traceback", "/srv/app", "sb_secret", "RuntimeError"):
        assert leak not in response.text
    # O detalhe vai para o log do servidor.
    assert SECRET in caplog.text
    # Com CORS: o front lê a mensagem em vez de ver "sem conexão".
    assert response.headers["access-control-allow-origin"] == FRONT


def test_expected_errors_keep_their_message(broken):
    app.dependency_overrides.clear()
    response = TestClient(app).get("/analyses")

    assert response.status_code == 401
    assert response.json() == {"detail": "Não autenticado."}


@pytest.mark.parametrize("origin", ["https://evil.example", "http://localhost:3000"])
def test_other_origins_get_no_cors_headers(origin):
    client = TestClient(app)

    preflight = client.options(
        "/analyses",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )
    simple = client.get("/health", headers={"Origin": origin})

    assert "access-control-allow-origin" not in preflight.headers
    assert "access-control-allow-origin" not in simple.headers


def test_front_origin_is_allowed_without_credentials():
    response = TestClient(app).options(
        "/analyses",
        headers={
            "Origin": FRONT,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONT
    # O token vai no cabeçalho Authorization, não em cookie.
    assert "access-control-allow-credentials" not in response.headers
