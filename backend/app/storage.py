"""Supabase Storage pela API REST (bucket privado, R6.4).

Só o backend fala com o Storage, com a chave secreta. O front recebe URLs
assinadas de curta duração. `urllib` basta para as três operações usadas.
"""

import json
import logging
import urllib.error
import urllib.request
from typing import Protocol
from urllib.parse import quote
from uuid import UUID

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 30


class StorageError(Exception):
    """Falha ao falar com o Storage (rede ou resposta de erro)."""


class Storage(Protocol):
    def upload(self, path: str, data: bytes, content_type: str) -> None: ...

    def signed_urls(self, paths: list[str]) -> dict[str, str]: ...

    def remove(self, paths: list[str]) -> None: ...


def object_prefix(user_id: UUID, analysis_id: UUID) -> str:
    """Pasta da análise no bucket: `<user_id>/<analysis_id>` (R6.4)."""
    return f"{user_id}/{analysis_id}"


class SupabaseStorage:
    def __init__(self, supabase_url: str, key: str, bucket: str, ttl_seconds: int):
        self.base = f"{supabase_url.rstrip('/')}/storage/v1"
        self.bucket = bucket
        self.ttl_seconds = ttl_seconds
        self.headers = {"apikey": key}
        # Chave antiga (JWT) vai também no Authorization; a nova (sb_secret_…)
        # não é JWT e vai só no apikey.
        if not key.startswith("sb_"):
            self.headers["Authorization"] = f"Bearer {key}"

    def upload(self, path: str, data: bytes, content_type: str) -> None:
        self._request(
            "POST",
            f"/object/{self.bucket}/{quote(path)}",
            data,
            {"Content-Type": content_type, "x-upsert": "true"},
        )

    def signed_urls(self, paths: list[str]) -> dict[str, str]:
        """Caminho → URL assinada válida por `ttl_seconds`."""
        body = json.dumps({"expiresIn": self.ttl_seconds, "paths": paths}).encode()
        items = self._request(
            "POST", f"/object/sign/{self.bucket}", body, {"Content-Type": "application/json"}
        )
        urls = {}
        for item in items:
            if item.get("error") or not item.get("signedURL"):
                raise StorageError(f"Sem URL assinada para {item.get('path')}")
            urls[item["path"]] = f"{self.base}{item['signedURL']}"
        return urls

    def remove(self, paths: list[str]) -> None:
        body = json.dumps({"prefixes": paths}).encode()
        self._request(
            "DELETE", f"/object/{self.bucket}", body, {"Content-Type": "application/json"}
        )

    def _request(self, method: str, path: str, body: bytes, headers: dict[str, str]):
        request = urllib.request.Request(
            self.base + path, data=body, method=method, headers={**self.headers, **headers}
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            # O corpo do erro do Storage não traz a chave; vai para o log, não para o usuário.
            detail = exc.read()[:300].decode(errors="replace")
            raise StorageError(
                f"Storage respondeu {exc.code} em {method} {path}: {detail}"
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise StorageError(f"Storage inacessível em {method} {path}: {exc}") from exc
        return json.loads(payload) if payload else None
