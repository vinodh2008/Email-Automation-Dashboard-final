"""
KnowledgeService — Knowledge source management and context retrieval.
Phase 2B: Simple text search. Phase 3: Vector similarity search.
"""
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

logger = logging.getLogger("knowledge_service")


class KnowledgeService:
    def __init__(self, db: Session):
        self.db = db

    def add_source(self, category_id: str, name: str, source_type: str, 
                   content_text: Optional[str] = None, file_path: Optional[str] = None,
                   description: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Add a knowledge source for a category."""
        try:
            from app.models.knowledge_source import KnowledgeSource
            import uuid
            
            source = KnowledgeSource(
                business_category_id=uuid.UUID(category_id),
                name=name,
                source_type=source_type,
                content_text=content_text,
                file_path=file_path,
                description=description,
                embedding_status="ready" if content_text else "pending",
            )
            self.db.add(source)
            self.db.commit()
            return {"id": str(source.id), "status": "created"}
        except Exception as e:
            self.db.rollback()
            logger.error(f"[KNOWLEDGE] Failed to add source: {e}")
            return None

    def get_sources(self, category_id: str) -> List[Dict[str, Any]]:
        """Get all knowledge sources for a category."""
        try:
            from app.models.knowledge_source import KnowledgeSource
            sources = self.db.query(KnowledgeSource).filter(
                KnowledgeSource.business_category_id == category_id,
                KnowledgeSource.is_active == True
            ).order_by(KnowledgeSource.created_at.desc()).all()
            
            return [{
                "id": str(s.id),
                "name": s.name,
                "source_type": s.source_type,
                "description": s.description,
                "file_path": s.file_path,
                "file_size_bytes": s.file_size_bytes,
                "mime_type": s.mime_type,
                "embedding_status": s.embedding_status,
                "chunk_count": s.chunk_count,
                "is_active": s.is_active,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            } for s in sources]
        except Exception as e:
            logger.error(f"[KNOWLEDGE] Failed to get sources: {e}")
            return []

    def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Get a single knowledge source."""
        try:
            from app.models.knowledge_source import KnowledgeSource
            source = self.db.query(KnowledgeSource).filter(KnowledgeSource.id == source_id).first()
            if not source:
                return None
            return {
                "id": str(source.id),
                "name": source.name,
                "source_type": source.source_type,
                "description": source.description,
                "content_text": source.content_text,
                "file_path": source.file_path,
                "embedding_status": source.embedding_status,
                "chunk_count": source.chunk_count,
            }
        except Exception as e:
            logger.error(f"[KNOWLEDGE] Failed to get source: {e}")
            return None

    def remove_source(self, source_id: str) -> bool:
        """Remove a knowledge source."""
        try:
            from app.models.knowledge_source import KnowledgeSource
            source = self.db.query(KnowledgeSource).filter(KnowledgeSource.id == source_id).first()
            if not source:
                return False
            self.db.delete(source)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"[KNOWLEDGE] Failed to remove source: {e}")
            return False

    def search_context(self, category_id: str, query: str, limit: int = 3) -> List[str]:
        """Search knowledge sources for relevant context (Phase 2B: simple text search)."""
        try:
            from app.models.knowledge_source import KnowledgeSource
            sources = self.db.query(KnowledgeSource).filter(
                KnowledgeSource.business_category_id == category_id,
                KnowledgeSource.is_active == True,
                KnowledgeSource.embedding_status == "ready",
                KnowledgeSource.content_text.ilike(f"%{query}%")
            ).limit(limit).all()
            
            return [s.content_text[:500] for s in sources if s.content_text]
        except Exception as e:
            logger.error(f"[KNOWLEDGE] Failed to search context: {e}")
            return []

    def index_source(self, source_id: str) -> bool:
        """Index a knowledge source (Phase 2B: mark as ready)."""
        try:
            from app.models.knowledge_source import KnowledgeSource
            source = self.db.query(KnowledgeSource).filter(KnowledgeSource.id == source_id).first()
            if not source:
                return False
            source.embedding_status = "ready"
            if source.content_text:
                source.chunk_count = max(1, len(source.content_text) // 500)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"[KNOWLEDGE] Failed to index source: {e}")
            return False