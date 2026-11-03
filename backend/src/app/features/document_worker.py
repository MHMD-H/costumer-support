"""Single-instance durable document ingestion worker.

PostgreSQL holds pending work. Run exactly one worker against local, persistent
upload and Chroma directories; the advisory lock enforces that at runtime.
"""

import asyncio
import logging
from os import getenv
from uuid import UUID

from sqlalchemy import text

from app.db.postgres import dispose_engine, get_engine, get_sessionmaker
from app.db.repositories import documents as document_repository
from app.features.documents import process_uploaded_document
from rag.core.config import RagSettings
from rag.ingestion import IngestionPipeline


logger = logging.getLogger(__name__)
WORKER_LOCK_ID = 220022


async def process_next_document(
    pipeline: IngestionPipeline,
    previous_tenant_id: UUID | None = None,
) -> UUID | None:
    async with get_sessionmaker()() as session:
        identity = await document_repository.next_uploaded_document(session, previous_tenant_id)
        if identity is None:
            return None
        await process_uploaded_document(session, *identity, pipeline=pipeline)
        return identity[0]


async def run_worker(*, poll_seconds: float = 2.0) -> None:
    upload_dir = getenv("DOCUMENT_UPLOAD_DIR")
    chroma_dir = getenv("CHROMA_PERSIST_DIRECTORY")
    if not upload_dir or not chroma_dir:
        raise RuntimeError("DOCUMENT_UPLOAD_DIR and CHROMA_PERSIST_DIRECTORY must be configured")
    settings = RagSettings(chroma_persist_directory=chroma_dir)
    pipeline = await asyncio.to_thread(IngestionPipeline.from_settings, settings)
    try:
        async with get_engine().connect() as lock_connection:
            acquired = await lock_connection.scalar(text("select pg_try_advisory_lock(:lock_id)"), {"lock_id": WORKER_LOCK_ID})
            await lock_connection.commit()
            if not acquired:
                raise RuntimeError("Another document worker is already running")
            try:
                async with get_sessionmaker()() as session:
                    resumed = await document_repository.requeue_interrupted_documents(session)
                    if resumed:
                        logger.info("Requeued %s interrupted document(s)", resumed)
                previous_tenant_id = None
                while True:
                    processed_tenant_id = await process_next_document(pipeline, previous_tenant_id)
                    if processed_tenant_id is None:
                        await asyncio.sleep(poll_seconds)
                    else:
                        previous_tenant_id = processed_tenant_id
            finally:
                await lock_connection.scalar(text("select pg_advisory_unlock(:lock_id)"), {"lock_id": WORKER_LOCK_ID})
                await lock_connection.commit()
    finally:
        await dispose_engine()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
