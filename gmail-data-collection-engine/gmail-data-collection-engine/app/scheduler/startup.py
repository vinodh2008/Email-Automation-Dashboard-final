"""
FastAPI Lifespan Startup & Shutdown Management.
Hooks APScheduler initialization directly into the FastAPI application lifecycle.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.scheduler.scheduler_service import scheduler_service

import asyncio
from sqlalchemy import text
from app.db.session import SessionLocal, ensure_full_schema
from app.scheduler.jobs import poll_mailboxes_job

logger = logging.getLogger("scheduler_startup")


def _recover_stale_locks():
    """Clears locks on mailbox_accounts table that were abandoned due to prior process kills/restarts."""
    db = SessionLocal()
    try:
        query = text("""
            UPDATE mailbox_accounts 
            SET sync_status = 'connected', 
                sync_lock_token = NULL,
                sync_locked_at = NULL,
                sync_lock_expires_at = NULL
            WHERE sync_status = 'syncing'
        """)
        res = db.execute(query)
        db.commit()
        if res.rowcount > 0:
            logger.info(f"[LIFESPAN] Recovered {res.rowcount} stale mailbox lock(s) on startup.")
    except Exception as e:
        db.rollback()
        logger.error(f"[LIFESPAN] Failed to clear stale mailbox locks: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan Context Manager.
    Starts background services on app boot and gracefully cleans up resources on shutdown.
    """
    logger.info("[LIFESPAN] Starting FastAPI application services...")
    try:
        # 0. Ensure database schema is up to date
        ensure_full_schema()
        
        # 1. Clear abandoned locks from crashed runs
        _recover_stale_locks()
        
        # 2. Trigger immediate out-of-band catch-up sync for missed emails during downtime
        logger.info("[LIFESPAN] Triggering immediate startup catch-up sync...")
        asyncio.create_task(asyncio.to_thread(poll_mailboxes_job))
        
        # 3. Start periodic background scheduler
        scheduler_service.start()
    except Exception as e:
        logger.error(f"[LIFESPAN] Failed during startup initialization: {e}")

    yield

    logger.info("[LIFESPAN] Shutting down FastAPI application services...")
    try:
        scheduler_service.shutdown()
    except Exception as e:
        logger.error(f"[LIFESPAN] Failed to shutdown APScheduler: {e}")
