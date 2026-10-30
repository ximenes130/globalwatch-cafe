"""Dublês em memória do banco e do Storage para testar worker e rotas."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.repository import STALE_MESSAGE
from app.storage import StorageError


class FakeStorage:
    def __init__(self, events: list | None = None, fail_upload: bool = False):
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.events = events if events is not None else []
        self.fail_upload = fail_upload
        self.fail_remove = False

    def upload(self, path: str, data: bytes, content_type: str) -> None:
        if self.fail_upload:
            raise StorageError("Storage fora do ar")
        self.events.append(("upload", path))
        self.objects[path] = (data, content_type)

    def signed_urls(self, paths: list[str]) -> dict[str, str]:
        return {path: f"https://storage.test/sign/{path}?token=t" for path in paths}

    def remove(self, paths: list[str]) -> None:
        if self.fail_remove:
            raise StorageError("Storage fora do ar")
        for path in paths:
            self.objects.pop(path, None)

    def download(self, path: str) -> bytes:
        if path not in self.objects:
            raise StorageError(f"Objeto não encontrado: {path}")
        return self.objects[path][0]


class FakeRepository:
    def __init__(self, events: list | None = None):
        self.rows: dict[UUID, dict] = {}
        self.events = events if events is not None else []
        self.fail_on_fail = False

    def create(self, user_id: UUID, filename: str) -> UUID:
        analysis_id = uuid4()
        self.rows[analysis_id] = {
            "id": analysis_id,
            "user_id": user_id,
            "status": "processing",
            "filename": filename,
            "created_at": datetime.now(UTC),
            "acquired_at": None,
            "crs": None,
            "bounds_wgs84": None,
            "stats": None,
            "params": None,
            "method_version": None,
            "rationale": None,
            "error": None,
        }
        return analysis_id

    def complete(self, analysis_id: UUID, result) -> None:
        self.events.append(("complete", analysis_id))
        row = self.rows[analysis_id]
        if row["status"] != "processing":
            return
        row.update(
            status="completed",
            acquired_at=result.acquired_at,
            crs=result.crs,
            bounds_wgs84=result.bounds_wgs84,
            stats=result.stats,
            params=result.params,
            method_version=result.method_version,
            rationale=result.rationale,
        )

    def fail(self, analysis_id: UUID, message: str) -> None:
        if self.fail_on_fail:
            raise RuntimeError("banco fora do ar")
        self.events.append(("fail", analysis_id))
        row = self.rows[analysis_id]
        if row["status"] == "processing":
            row.update(status="failed", error=message)

    def expire_stale(self, user_id: UUID, minutes: int) -> int:
        limit = datetime.now(UTC) - timedelta(minutes=minutes)
        expired = 0
        for row in self.rows.values():
            if row["user_id"] == user_id and row["status"] == "processing":
                if row["created_at"] < limit:
                    row.update(status="failed", error=STALE_MESSAGE)
                    expired += 1
        return expired

    def list(self, user_id: UUID) -> list[dict]:
        rows = [r for r in self.rows.values() if r["user_id"] == user_id]
        rows.sort(key=lambda r: r["created_at"], reverse=True)
        return [
            {
                "id": r["id"],
                "filename": r["filename"],
                "created_at": r["created_at"],
                "status": r["status"],
                "acquired_at": r["acquired_at"],
                "potential_area_ha": (r["stats"] or {}).get("potential_area_ha"),
            }
            for r in rows
        ]

    def get(self, user_id: UUID, analysis_id: UUID) -> dict | None:
        row = self.rows.get(analysis_id)
        return dict(row) if row and row["user_id"] == user_id else None

    def delete(self, user_id: UUID, analysis_id: UUID) -> bool:
        row = self.rows.get(analysis_id)
        if row and row["user_id"] == user_id:
            del self.rows[analysis_id]
            return True
        return False

    def list_expired(self, days: int) -> Sequence[tuple[UUID, UUID]]:
        limit = datetime.now(UTC) - timedelta(days=days)
        rows = sorted(self.rows.values(), key=lambda r: r["created_at"])
        return [(r["id"], r["user_id"]) for r in rows if r["created_at"] < limit]


class FakeChatRepository:
    def __init__(self):
        self.rows: list[dict] = []
        self.fail = False

    def history(self, user_id: UUID, analysis_id: UUID) -> list[dict]:
        return [
            {k: r[k] for k in ("id", "role", "content", "cards", "created_at")}
            for r in self.rows
            if r["user_id"] == user_id and r["analysis_id"] == analysis_id
        ]

    def append(self, user_id: UUID, analysis_id: UUID, messages: list[dict]) -> None:
        if self.fail:
            raise RuntimeError("banco fora do ar")
        for message in messages:
            self.rows.append(
                {
                    "id": len(self.rows) + 1,
                    "user_id": user_id,
                    "analysis_id": analysis_id,
                    "role": message["role"],
                    "content": message["content"],
                    "cards": message.get("cards", []),
                    "created_at": datetime.now(UTC),
                }
            )


class FakeUsage:
    """Contador de uso em memória, com o mesmo contrato do `UsageRepository`."""

    def __init__(self):
        self.counts: dict[tuple[UUID, str], int] = {}

    def consume(self, user_id: UUID, kind: str, limit: int) -> bool:
        used = self.counts.get((user_id, kind), 0)
        if used >= limit:
            return False
        self.counts[(user_id, kind)] = used + 1
        return True
