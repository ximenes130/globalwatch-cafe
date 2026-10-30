"""R1.7: /health público, com o estado do banco."""

from fastapi.testclient import TestClient

from app import db
from app.main import app


def test_health_without_database_url(monkeypatch):
    monkeypatch.setattr(db, "_pool", None)
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "not_configured"}


def test_health_with_unreachable_database_returns_200_with_error():
    # Porta 1 recusa conexão na hora: exercita o caminho real de falha do psycopg.
    db.open_pool("postgresql://user:password@127.0.0.1:1/db")
    try:
        response = TestClient(app).get("/health")
    finally:
        db.close_pool()
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "error"}


def test_health_with_healthy_database(monkeypatch):
    monkeypatch.setattr(db, "check", lambda: "ok")
    response = TestClient(app).get("/health")
    assert response.json() == {"status": "ok", "db": "ok"}
