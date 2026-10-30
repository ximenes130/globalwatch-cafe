"""Isola os testes do `backend/.env` local: variáveis de ambiente têm prioridade."""

import os

import pytest

# Lida na importação do app (main.py), antes de qualquer fixture: a documentação da
# API fica desligada nos testes mesmo com `API_DOCS=true` no `.env` local.
os.environ["API_DOCS"] = "false"
# Também lida na importação: a origem do front em desenvolvimento, como no `.env.example`.
os.environ["CORS_ORIGINS"] = "http://localhost:5173"

from app import auth
from app.config import get_settings

TEST_SUPABASE_URL = "https://test-project.supabase.co"


@pytest.fixture(autouse=True)
def test_settings(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", TEST_SUPABASE_URL)
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    get_settings.cache_clear()
    auth.get_jwks_client.cache_clear()
    yield
    get_settings.cache_clear()
    auth.get_jwks_client.cache_clear()
