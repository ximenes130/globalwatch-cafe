"""Worker em plano de fundo (T2.10, T3.5, R2.1, R2.19, R2.23, R3.10)."""

import json
import logging
import threading
from uuid import uuid4

import pytest

from app import worker
from app.processing.errors import ProcessingError
from app.worker import PROCESSING_SLOT, UNEXPECTED_ERROR, run_analysis
from tests.fakes import FakeRepository, FakeStorage
from tests.rasters import ADDITIONAL_IMAGE, ADDITIONAL_SCL, KIT_IMAGE, KIT_SCL

USER = uuid4()


@pytest.fixture
def setup():
    events = []
    repository = FakeRepository(events)
    storage = FakeStorage(events)
    analysis_id = repository.create(USER, "imagem_multiespectral.tif")
    return analysis_id, repository, storage, events


def test_kit_is_stored_and_completed(setup):
    analysis_id, repository, storage, _ = setup

    run_analysis(
        analysis_id, USER, KIT_IMAGE.read_bytes(), KIT_SCL.read_bytes(), repository, storage
    )

    row = repository.rows[analysis_id]
    assert row["status"] == "completed"
    assert row["stats"]["total_area_ha"] == 2621.44
    prefix = f"{USER}/{analysis_id}"
    assert set(storage.objects) == {
        f"{prefix}/{name}"
        for name in (
            "original.tif",
            "scl.tif",
            "rgb.png",
            "classification.png",
            "polygons.png",
            "result.geojson",
        )
    }
    assert storage.objects[f"{prefix}/original.tif"] == (KIT_IMAGE.read_bytes(), "image/tiff")
    assert storage.objects[f"{prefix}/rgb.png"][1] == "image/png"
    geojson, content_type = storage.objects[f"{prefix}/result.geojson"]
    assert content_type == "application/geo+json"
    assert len(json.loads(geojson)["features"]) == row["stats"]["polygon_count"]


def test_files_are_written_before_the_row_is_completed(setup):
    analysis_id, repository, storage, events = setup

    run_analysis(analysis_id, USER, KIT_IMAGE.read_bytes(), None, repository, storage)

    kinds = [kind for kind, _ in events]
    assert kinds[-1] == "complete"
    assert set(kinds[:-1]) == {"upload"}
    assert not any("scl.tif" in path for kind, path in events if kind == "upload")


def test_processing_error_message_goes_to_the_row(setup):
    analysis_id, repository, storage, _ = setup

    run_analysis(analysis_id, USER, b"isto nao e um tiff", None, repository, storage)

    row = repository.rows[analysis_id]
    assert row["status"] == "failed"
    assert row["error"] == "Não foi possível ler a imagem enviada como GeoTIFF."
    assert storage.objects == {}


def test_unexpected_error_is_logged_but_not_shown(setup, monkeypatch, caplog):
    analysis_id, repository, storage, _ = setup

    def broken(*_):
        raise RuntimeError("detalhe interno em /srv/app/processing")

    monkeypatch.setattr(worker, "run_pipeline", broken)
    with caplog.at_level(logging.ERROR, logger="app.worker"):
        run_analysis(analysis_id, USER, b"x", None, repository, storage)

    row = repository.rows[analysis_id]
    assert row["status"] == "failed"
    assert row["error"] == UNEXPECTED_ERROR
    assert "/srv" not in row["error"]
    assert "detalhe interno" in caplog.text


def test_storage_failure_fails_the_analysis(setup):
    analysis_id, repository, _, _ = setup
    storage = FakeStorage(fail_upload=True)

    run_analysis(analysis_id, USER, KIT_IMAGE.read_bytes(), None, repository, storage)

    assert repository.rows[analysis_id]["status"] == "failed"
    assert repository.rows[analysis_id]["error"] == UNEXPECTED_ERROR


def test_failure_to_record_failure_does_not_escape(setup):
    analysis_id, repository, storage, _ = setup
    repository.fail_on_fail = True

    run_analysis(analysis_id, USER, b"isto nao e um tiff", None, repository, storage)

    assert repository.rows[analysis_id]["status"] == "processing"  # expira depois (R2.24)


def test_second_analysis_waits_for_the_slot(setup, monkeypatch):
    analysis_id, repository, storage, _ = setup

    def failing_fast(*_):
        raise ProcessingError("rápido")

    monkeypatch.setattr(worker, "run_pipeline", failing_fast)
    PROCESSING_SLOT.acquire()  # simula um processamento em andamento
    try:
        thread = threading.Thread(
            target=run_analysis, args=(analysis_id, USER, b"x", None, repository, storage)
        )
        thread.start()
        thread.join(timeout=0.3)
        assert thread.is_alive()
        assert repository.rows[analysis_id]["status"] == "processing"
    finally:
        PROCESSING_SLOT.release()
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert repository.rows[analysis_id]["status"] == "failed"


def test_second_date_files_are_stored_too(setup):
    analysis_id, repository, storage, _ = setup

    run_analysis(
        analysis_id,
        USER,
        KIT_IMAGE.read_bytes(),
        KIT_SCL.read_bytes(),
        repository,
        storage,
        image_2=ADDITIONAL_IMAGE.read_bytes(),
        scl_2=ADDITIONAL_SCL.read_bytes(),
    )

    row = repository.rows[analysis_id]
    assert row["status"] == "completed"
    assert row["stats"]["potential_area_ha"] == 103.04
    prefix = f"{USER}/{analysis_id}"
    assert storage.objects[f"{prefix}/original_2.tif"] == (
        ADDITIONAL_IMAGE.read_bytes(),
        "image/tiff",
    )
    assert storage.objects[f"{prefix}/scl_2.tif"][0] == ADDITIONAL_SCL.read_bytes()
    assert len(storage.objects) == 8
