"""Worker polling and interrupted-job recovery without a live PostgreSQL server."""

import asyncio

import pytest

from app.features import document_worker as worker


class AsyncContext:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, *_args):
        return False


def test_worker_requeues_interrupted_jobs_before_polling(monkeypatch, tmp_path):
    monkeypatch.setenv("DOCUMENT_UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("CHROMA_PERSIST_DIRECTORY", str(tmp_path / "chroma"))
    calls = []

    class Connection:
        async def scalar(self, statement, params):
            calls.append((str(statement), params))
            return True

        async def commit(self):
            calls.append("commit")

    class Engine:
        def connect(self):
            return AsyncContext(Connection())

    class SessionMaker:
        def __call__(self):
            return AsyncContext(object())

    async def requeue(_session):
        calls.append("requeue")
        return 1

    async def poll(_pipeline, previous_tenant_id):
        calls.append(("poll", previous_tenant_id))
        raise RuntimeError("stop test loop")

    async def dispose():
        calls.append("dispose")

    monkeypatch.setattr(worker, "get_engine", lambda: Engine())
    monkeypatch.setattr(worker, "get_sessionmaker", lambda: SessionMaker())
    monkeypatch.setattr(worker.document_repository, "requeue_interrupted_documents", requeue)
    monkeypatch.setattr(worker, "process_next_document", poll)
    monkeypatch.setattr(worker, "dispose_engine", dispose)
    monkeypatch.setattr(worker.IngestionPipeline, "from_settings", lambda *_args: object())

    with pytest.raises(RuntimeError, match="stop test loop"):
        asyncio.run(worker.run_worker())
    assert calls.index("requeue") < calls.index(("poll", None))
    assert "pg_try_advisory_lock" in calls[0][0]
    assert any(isinstance(call, tuple) and "pg_advisory_unlock" in call[0] for call in calls)
    assert calls[-1] == "dispose"


def test_second_worker_exits_without_requeue(monkeypatch, tmp_path):
    monkeypatch.setenv("DOCUMENT_UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("CHROMA_PERSIST_DIRECTORY", str(tmp_path / "chroma"))

    class Connection:
        async def scalar(self, *_args):
            return False

        async def commit(self):
            pass

    class Engine:
        def connect(self):
            return AsyncContext(Connection())

    async def dispose():
        pass

    monkeypatch.setattr(worker, "get_engine", lambda: Engine())
    monkeypatch.setattr(worker, "dispose_engine", dispose)
    monkeypatch.setattr(worker.IngestionPipeline, "from_settings", lambda *_args: object())
    with pytest.raises(RuntimeError, match="already running"):
        asyncio.run(worker.run_worker())


def test_worker_passes_previous_tenant_to_fair_queue_selection(monkeypatch):
    previous_tenant = worker.UUID("11111111-1111-1111-1111-111111111111")
    selected_tenant = worker.UUID("22222222-2222-2222-2222-222222222222")
    document_id = worker.UUID("33333333-3333-3333-3333-333333333333")
    calls = []

    class SessionMaker:
        def __call__(self):
            return AsyncContext(object())

    async def select(_session, requested_previous):
        calls.append(("select", requested_previous))
        return selected_tenant, document_id

    async def process(_session, tenant_id, requested_document, *, pipeline):
        calls.append(("process", tenant_id, requested_document, pipeline))
        return True

    pipeline = object()
    monkeypatch.setattr(worker, "get_sessionmaker", lambda: SessionMaker())
    monkeypatch.setattr(worker.document_repository, "next_uploaded_document", select)
    monkeypatch.setattr(worker, "process_uploaded_document", process)

    result = asyncio.run(worker.process_next_document(pipeline, previous_tenant))

    assert result == selected_tenant
    assert calls == [
        ("select", previous_tenant),
        ("process", selected_tenant, document_id, pipeline),
    ]
