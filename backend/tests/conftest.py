"""Isola os testes do `backend/.env` local: variáveis de ambiente têm prioridade."""

import pytest

from app import auth
from app.config import get_settings

TEST_SUPABASE_URL = "https://test-project.supabase.co"


@pytest.fixture(autouse=True)
def test_settings(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", TEST_SUPABASE_URL)
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    get_settings.cache_clear()
    auth.get_jwks_client.cache_clear()
    yield
    get_settings.cache_clear()
    auth.get_jwks_client.cache_clear()
