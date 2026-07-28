from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.sync_orchestrator import SyncOrchestrator
from app.providers.gmail_provider import GmailProvider
from app.auth.dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sync", tags=["sync"], dependencies=[Depends(get_current_user)])

@router.post("/{mailbox_account_id}")
def trigger_sync(mailbox_account_id: str, db: Session = Depends(get_db)):
    try:
        provider = GmailProvider()
        provider.authenticate()
        orchestrator = SyncOrchestrator(db, provider)
        success = orchestrator.run_sync(mailbox_account_id, mode="incremental")
        if success:
            return {"status": "success", "message": f"Sync completed for {mailbox_account_id}"}
        raise HTTPException(status_code=400, detail="Sync failed or mailbox is locked")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during sync")
