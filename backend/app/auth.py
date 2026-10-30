"""Validação do JWT do Supabase (R1.5, R1.6)."""

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings

log = logging.getLogger(__name__)

# Só algoritmos assimétricos: aceitar HS256 abriria a confusão de algoritmo.
ALLOWED_ALGORITHMS = {"ES256", "RS256"}
REQUIRED_CLAIMS = ["exp", "iss", "aud", "sub"]

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    email: str | None


@lru_cache
def get_jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    # Guarda o JWKS por 10 min; um `kid` desconhecido força nova busca (rotação de chave).
    return jwt.PyJWKClient(jwks_url, lifespan=600, timeout=5)


def decode_token(token: str, settings: Settings) -> dict:
    issuer = f"{settings.supabase_url}/auth/v1"
    signing_key = get_jwks_client(f"{issuer}/.well-known/jwks.json").get_signing_key_from_jwt(token)
    if signing_key.algorithm_name not in ALLOWED_ALGORITHMS:
        raise jwt.InvalidAlgorithmError(signing_key.algorithm_name)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=[signing_key.algorithm_name],
        audience=settings.supabase_jwt_audience,
        issuer=issuer,
        options={"require": REQUIRED_CLAIMS},
    )


def _unauthorized() -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail="Não autenticado.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> CurrentUser:
    """Dependência das rotas protegidas: devolve o usuário do token ou 401."""
    settings = get_settings()
    if not settings.supabase_url:
        log.error("SUPABASE_URL ausente; impossível validar tokens")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Autenticação indisponível.")
    if credentials is None:
        raise _unauthorized()
    try:
        claims = decode_token(credentials.credentials, settings)
        user_id = UUID(claims["sub"])
    except jwt.PyJWKClientConnectionError:
        log.exception("Falha ao buscar o JWKS do Supabase")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Autenticação indisponível."
        ) from None
    except (jwt.PyJWTError, ValueError):
        raise _unauthorized() from None
    if claims.get("is_anonymous"):
        raise _unauthorized()
    return CurrentUser(id=user_id, email=claims.get("email"))
