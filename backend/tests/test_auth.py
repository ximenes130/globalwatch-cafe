"""R1.5, R1.6: validação do JWT do Supabase no backend."""

import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from tests.conftest import TEST_SUPABASE_URL

KID = "test-key"
PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())
OTHER_PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())
USER_ID = str(uuid.uuid4())


def _jwks() -> dict:
    jwk = jwt.algorithms.ECAlgorithm.to_jwk(PRIVATE_KEY.public_key(), as_dict=True)
    return {"keys": [{**jwk, "kid": KID, "alg": "ES256", "use": "sig"}]}


@pytest.fixture(autouse=True)
def fake_jwks(monkeypatch):
    # Só a busca HTTP é falsa; a seleção da chave pelo `kid` é a do PyJWKClient real.
    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", lambda self: _jwks())


def make_token(key=PRIVATE_KEY, algorithm="ES256", kid=KID, drop=(), **overrides) -> str:
    now = int(time.time())
    claims = {
        "sub": USER_ID,
        "email": "a@example.com",
        "aud": "authenticated",
        "iss": f"{TEST_SUPABASE_URL}/auth/v1",
        "iat": now,
        "exp": now + 3600,
        "role": "authenticated",
        **overrides,
    }
    for name in drop:
        claims.pop(name)
    return jwt.encode(claims, key, algorithm=algorithm, headers={"kid": kid})


def get_me(token: str | None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return TestClient(app).get("/me", headers=headers)


def assert_unauthorized(response):
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"detail": "Não autenticado."}


def test_valid_token_returns_user():
    response = get_me(make_token())
    assert response.status_code == 200
    assert response.json() == {"user_id": USER_ID, "email": "a@example.com"}


def test_missing_token_returns_401():
    assert_unauthorized(get_me(None))


def test_non_bearer_scheme_returns_401():
    response = TestClient(app).get("/me", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert_unauthorized(response)


def test_malformed_token_returns_401():
    assert_unauthorized(get_me("not-a-jwt"))


def test_expired_token_returns_401():
    assert_unauthorized(get_me(make_token(exp=int(time.time()) - 60)))


def test_wrong_audience_returns_401():
    assert_unauthorized(get_me(make_token(aud="anon")))


def test_wrong_issuer_returns_401():
    assert_unauthorized(get_me(make_token(iss="https://other-project.supabase.co/auth/v1")))


@pytest.mark.parametrize("claim", ["exp", "sub", "aud", "iss"])
def test_missing_required_claim_returns_401(claim):
    assert_unauthorized(get_me(make_token(drop=(claim,))))


def test_non_uuid_sub_returns_401():
    assert_unauthorized(get_me(make_token(sub="not-a-uuid")))


def test_token_signed_by_another_key_returns_401():
    assert_unauthorized(get_me(make_token(key=OTHER_PRIVATE_KEY)))


def test_unknown_kid_returns_401():
    assert_unauthorized(get_me(make_token(kid="unknown")))


def test_hs256_token_returns_401():
    # Confusão de algoritmo: token simétrico com o mesmo `kid` não pode passar.
    assert_unauthorized(get_me(make_token(key="a" * 32, algorithm="HS256")))


def test_anonymous_session_returns_401():
    assert_unauthorized(get_me(make_token(is_anonymous=True)))


def test_jwks_unavailable_returns_503(monkeypatch):
    def fail(self):
        raise jwt.PyJWKClientConnectionError("timeout")

    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", fail)
    response = get_me(make_token())
    assert response.status_code == 503


def test_missing_supabase_url_returns_503(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "")
    get_settings.cache_clear()
    assert get_me(make_token()).status_code == 503
