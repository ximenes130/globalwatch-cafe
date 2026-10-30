"""SQL de `analyses`, `chat_messages` e `usage_daily` contra Postgres (T2.10, T5.5, T6.4, C3.2).

Precisa de `TEST_DATABASE_URL` apontando para um banco com as migrations e o
stub de `supabase/tests/` (o `rls_test` que o `run.sh` cria). Sem a variável,
os testes são pulados.
"""

import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.processing.pipeline import AnalysisResult
from app.ratelimit import UsageRepository
from app.repository import STALE_MESSAGE, AnalysisRepository, ChatMessageRepository

DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL não definida")


@pytest.fixture(scope="module")
def pool():
    from psycopg_pool import ConnectionPool

    with ConnectionPool(DATABASE_URL, min_size=1, max_size=2) as pool:
        yield pool


@pytest.fixture
def users(pool):
    ids = [uuid4(), uuid4()]
    with pool.connection() as conn:
        for user_id in ids:
            conn.execute("insert into auth.users (id, email) values (%s, %s)", (user_id, "t@t"))
    yield ids
    with pool.connection() as conn:
        conn.execute("delete from analyses where user_id = any(%s)", (ids,))
        conn.execute("delete from usage_daily where user_id = any(%s)", (ids,))
        conn.execute("delete from auth.users where id = any(%s)", (ids,))


def result(potential: float = 12.5) -> AnalysisResult:
    return AnalysisResult(
        acquired_at=datetime(2025, 8, 16, 13, 28, tzinfo=UTC),
        crs="EPSG:32723",
        bounds_wgs84=[[-46.7, -21.3], [-46.6, -21.3], [-46.6, -21.4], [-46.7, -21.4]],
        stats={"potential_area_ha": potential, "polygon_count": 2},
        params={"ndvi_min": 0.55},
        method_version="spectral-rules-1.0",
        rationale={"summary": "ok"},
        geojson={"type": "FeatureCollection", "features": []},
        images={},
    )


def age(pool, analysis_id: UUID, minutes: int) -> None:
    with pool.connection() as conn:
        conn.execute(
            "update analyses set created_at = now() - make_interval(mins => %s) where id = %s",
            (minutes, analysis_id),
        )


def test_create_complete_and_read_back(pool, users):
    repo = AnalysisRepository(pool)
    owner, _ = users

    analysis_id = repo.create(owner, "kit.tif")
    assert repo.get(owner, analysis_id)["status"] == "processing"
    repo.complete(analysis_id, result())

    row = repo.get(owner, analysis_id)
    assert row["status"] == "completed"
    assert row["crs"] == "EPSG:32723"
    assert row["stats"]["potential_area_ha"] == 12.5
    assert row["rationale"] == {"summary": "ok"}
    assert row["acquired_at"] == datetime(2025, 8, 16, 13, 28, tzinfo=UTC)
    assert repo.list(owner)[0]["potential_area_ha"] == 12.5


def test_other_user_sees_nothing(pool, users):
    repo = AnalysisRepository(pool)
    owner, other = users
    analysis_id = repo.create(owner, "kit.tif")

    assert repo.get(other, analysis_id) is None
    assert repo.list(other) == []
    assert repo.delete(other, analysis_id) is False
    assert repo.get(owner, analysis_id) is not None


def test_list_is_newest_first(pool, users):
    repo = AnalysisRepository(pool)
    owner, _ = users
    older = repo.create(owner, "a.tif")
    age(pool, older, 5)
    newer = repo.create(owner, "b.tif")

    assert [row["id"] for row in repo.list(owner)] == [newer, older]


def test_fail_and_complete_only_touch_processing_rows(pool, users):
    repo = AnalysisRepository(pool)
    owner, _ = users
    analysis_id = repo.create(owner, "kit.tif")

    repo.fail(analysis_id, "erro legível")
    repo.complete(analysis_id, result())  # chega tarde: não sobrescreve a falha

    row = repo.get(owner, analysis_id)
    assert row["status"] == "failed"
    assert row["error"] == "erro legível"


def test_expire_stale_only_old_processing_rows_of_the_user(pool, users):
    repo = AnalysisRepository(pool)
    owner, other = users
    stale = repo.create(owner, "velha.tif")
    age(pool, stale, 20)
    fresh = repo.create(owner, "nova.tif")
    other_stale = repo.create(other, "alheia.tif")
    age(pool, other_stale, 20)
    done = repo.create(owner, "pronta.tif")
    repo.complete(done, result())
    age(pool, done, 20)

    assert repo.expire_stale(owner, 15) == 1

    assert repo.get(owner, stale)["status"] == "failed"
    assert repo.get(owner, stale)["error"] == STALE_MESSAGE
    assert repo.get(owner, fresh)["status"] == "processing"
    assert repo.get(other, other_stale)["status"] == "processing"
    assert repo.get(owner, done)["status"] == "completed"


def test_delete_own_analysis(pool, users):
    repo = AnalysisRepository(pool)
    owner, _ = users
    analysis_id = repo.create(owner, "kit.tif")

    assert repo.delete(owner, analysis_id) is True
    assert repo.get(owner, analysis_id) is None


CARD = {"kind": "polygon", "data": {"id": 31, "area_ha": 1.73, "centroid": [-46.68, -21.31]}}


def test_chat_exchange_round_trip_in_order(pool, users):
    owner, _ = users
    analysis_id = AnalysisRepository(pool).create(owner, "kit.tif")
    chat = ChatMessageRepository(pool)

    intro = [{"role": "assistant", "content": "Apresentação.", "cards": []}]
    chat.append(owner, analysis_id, intro)
    chat.append(
        owner,
        analysis_id,
        [
            {"role": "user", "content": "Fale do 31"},
            {"role": "assistant", "content": "O 31 tem 1,73 ha.", "cards": [CARD]},
        ],
    )

    history = chat.history(owner, analysis_id)
    assert [(m["role"], m["content"]) for m in history] == [
        ("assistant", "Apresentação."),
        ("user", "Fale do 31"),
        ("assistant", "O 31 tem 1,73 ha."),
    ]
    assert history[1]["cards"] == []
    assert history[2]["cards"] == [CARD]


def test_chat_history_is_per_user_and_goes_with_the_analysis(pool, users):
    owner, other = users
    repo = AnalysisRepository(pool)
    analysis_id = repo.create(owner, "kit.tif")
    chat = ChatMessageRepository(pool)
    chat.append(owner, analysis_id, [{"role": "assistant", "content": "Oi.", "cards": []}])

    assert chat.history(other, analysis_id) == []
    repo.delete(owner, analysis_id)
    assert chat.history(owner, analysis_id) == []


def test_chat_exchange_is_all_or_nothing(pool, users):
    owner, _ = users
    analysis_id = AnalysisRepository(pool).create(owner, "kit.tif")
    chat = ChatMessageRepository(pool)

    with pytest.raises(Exception):  # noqa: B017 - qualquer erro do banco serve
        chat.append(
            owner,
            analysis_id,
            [
                {"role": "user", "content": "Pergunta"},
                {"role": "system", "content": "papel inválido"},
            ],
        )

    assert chat.history(owner, analysis_id) == []


def test_usage_stops_at_the_limit_per_kind_and_user(pool, users):
    owner, other = users
    usage = UsageRepository(pool)

    assert [usage.consume(owner, "uploads", 5) for _ in range(6)] == [True] * 5 + [False]
    # Mensagens e outro usuário têm contadores próprios.
    assert usage.consume(owner, "messages", 30) is True
    assert usage.consume(other, "uploads", 5) is True
    with pool.connection() as conn:
        row = conn.execute(
            "select uploads, messages from usage_daily where user_id = %s and day = current_date",
            (owner,),
        ).fetchone()
    # O contador não passa do limite com as tentativas recusadas.
    assert row == (5, 1)


def test_usage_of_yesterday_does_not_count(pool, users):
    owner, _ = users
    with pool.connection() as conn:
        conn.execute(
            "insert into usage_daily (user_id, day, uploads) values (%s, current_date - 1, 5)",
            (owner,),
        )

    assert UsageRepository(pool).consume(owner, "uploads", 5) is True


def test_concurrent_requests_do_not_pass_the_limit(pool, users):
    from concurrent.futures import ThreadPoolExecutor

    from psycopg_pool import ConnectionPool

    owner, _ = users
    with ConnectionPool(DATABASE_URL, min_size=10, max_size=10) as wide:
        usage = UsageRepository(wide)
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(lambda _: usage.consume(owner, "uploads", 5), range(10)))

    assert results.count(True) == 5


def test_unknown_usage_kind_is_rejected(pool, users):
    with pytest.raises(ValueError):
        UsageRepository(pool).consume(users[0], "uploads; drop table usage_daily", 5)


def test_list_expired_by_age_across_users(pool, users):
    owner, other = users
    repo = AnalysisRepository(pool)
    old_owner = repo.create(owner, "velha.tif")
    old_other = repo.create(other, "velha.tif")
    recent = repo.create(owner, "nova.tif")
    with pool.connection() as conn:
        conn.execute(
            "update analyses set created_at = now() - interval '8 days' where id = any(%s)",
            ([old_owner, old_other],),
        )
        conn.execute(
            "update analyses set created_at = now() - interval '6 days 23 hours' where id = %s",
            (recent,),
        )

    expired = [row for row in repo.list_expired(7) if row[1] in (owner, other)]

    assert sorted(expired) == sorted([(old_owner, owner), (old_other, other)])


def test_usage_today_reads_without_counting(pool, users):
    owner, other = users
    usage = UsageRepository(pool)
    with pool.connection() as conn:
        conn.execute(
            "insert into usage_daily (user_id, day, uploads) values (%s, current_date - 1, 4)",
            (owner,),
        )
        tomorrow = conn.execute("select (current_date + 1)::timestamptz").fetchone()[0]

    assert usage.today(owner) == {"uploads": 0, "messages": 0, "resets_at": tomorrow}
    usage.consume(owner, "uploads", 5)
    usage.consume(owner, "messages", 30)
    usage.consume(owner, "messages", 30)
    assert usage.today(owner)["uploads"] == 1
    assert usage.today(owner)["messages"] == 2
    # Ler duas vezes não muda nada, e outro usuário continua zerado.
    assert usage.today(owner)["messages"] == 2
    assert usage.today(other)["uploads"] == 0
