from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.services.knowledge_service import KnowledgeService
from app.core.responses import success_response

router = APIRouter(prefix="/knowledge-sources", tags=["knowledge-sources"], dependencies=[Depends(get_current_user)])


class KnowledgeSourceCreate(BaseModel):
    business_category_id: str
    name: str
    source_type: str
    description: Optional[str] = None
    content_text: Optional[str] = None
    file_path: Optional[str] = None


@router.get("/")
def list_sources(category_id: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        svc = KnowledgeService(db)
        if category_id:
            sources = svc.get_sources(category_id)
        else:
            sources = []
        return success_response(data=sources)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/")
def create_source(source_data: KnowledgeSourceCreate, db: Session = Depends(get_db)):
    try:
        svc = KnowledgeService(db)
        result = svc.add_source(
            category_id=source_data.business_category_id,
            name=source_data.name,
            source_type=source_data.source_type,
            content_text=source_data.content_text,
            file_path=source_data.file_path,
            description=source_data.description,
        )
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create source")
        return success_response(data=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{source_id}")
def get_source(source_id: str, db: Session = Depends(get_db)):
    try:
        svc = KnowledgeService(db)
        source = svc.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        return success_response(data=source)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{source_id}")
def delete_source(source_id: str, db: Session = Depends(get_db)):
    try:
        svc = KnowledgeService(db)
        result = svc.remove_source(source_id)
        if not result:
            raise HTTPException(status_code=404, detail="Source not found")
        return success_response(data={"status": "deleted"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{source_id}/index")
def index_source(source_id: str, db: Session = Depends(get_db)):
    try:
        svc = KnowledgeService(db)
        result = svc.index_source(source_id)
        if not result:
            raise HTTPException(status_code=404, detail="Source not found")
        return success_response(data={"status": "indexed"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/search")
def search_knowledge(category_id: str, query: str, limit: int = 3, db: Session = Depends(get_db)):
    try:
        svc = KnowledgeService(db)
        results = svc.search_context(category_id, query, limit=limit)
        return success_response(data=results)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
