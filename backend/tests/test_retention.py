"""Retenção de 7 dias com banco e Storage em memória (T6.7, R6.15).

A seleção por idade contra Postgres fica em `test_repository.py`.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from app import retention
from app.retention import purge_expired
from app.routes.analyses import ALL_FILES
from app.storage import StorageError, object_prefix
from tests.fakes import FakeRepository, FakeStorage

A = UUID("11111111-1111-1111-1111-111111111111")
B = UUID("22222222-2222-2222-2222-222222222222")


def analysis(repository, storage, user_id, age_days: float):
    analysis_id = repository.create(user_id, "kit.tif")
    repository.rows[analysis_id]["created_at"] = datetime.now(UTC) - timedelta(days=age_days)
    for name in ("original.tif", "rgb.png", "result.geojson"):
        storage.upload(f"{object_prefix(user_id, analysis_id)}/{name}", b"x", "image/png")
    return analysis_id


def files_of(storage, user_id, analysis_id):
    prefix = object_prefix(user_id, analysis_id)
    return [path for path in storage.objects if path.startswith(prefix)]


def test_only_analyses_older_than_seven_days_go_of_any_user():
    repository, storage = FakeRepository(), FakeStorage()
    old_a = analysis(repository, storage, A, 8)
    old_b = analysis(repository, storage, B, 30)
    recent = analysis(repository, storage, A, 6.9)

    assert purge_expired(repository, storage) == (2, 0)

    assert set(repository.rows) == {recent}
    assert files_of(storage, A, old_a) == [] and files_of(storage, B, old_b) == []
    assert len(files_of(storage, A, recent)) == 3


def test_files_go_before_the_row():
    events = []
    repository, storage = FakeRepository(), FakeStorage()
    analysis_id = analysis(repository, storage, A, 8)
    original_remove, original_delete = storage.remove, repository.delete
    storage.remove = lambda paths: (
        events.append(("remove", sorted(paths))),
        original_remove(paths),
    )
    repository.delete = lambda user_id, aid: (
        events.append(("delete", aid)),
        original_delete(user_id, aid),
    )

    purge_expired(repository, storage)

    prefix = object_prefix(A, analysis_id)
    assert events == [
        ("remove", sorted(f"{prefix}/{name}" for name in ALL_FILES)),
        ("delete", analysis_id),
    ]


def test_storage_failure_keeps_the_row_and_continues():
    repository, storage = FakeRepository(), FakeStorage()
    failing = analysis(repository, storage, A, 9)
    other = analysis(repository, storage, B, 8)
    original = storage.remove

    def remove(paths):
        if any(str(failing) in path for path in paths):
            raise StorageError("Storage fora do ar")
        original(paths)

    storage.remove = remove

    assert purge_expired(repository, storage) == (1, 1)
    assert failing in repository.rows
    assert other not in repository.rows


def test_main_without_configuration_fails_without_touching_anything(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    retention.get_settings.cache_clear()

    assert retention.main() == 2
