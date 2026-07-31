import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.prompt_variable import PromptVariable
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger("prompt_variable_repository")


class PromptVariableRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, PromptVariable)

    def get_by_name(self, name: str) -> Optional[PromptVariable]:
        return self.db.query(PromptVariable).filter(
            PromptVariable.name == name,
            PromptVariable.is_active == True
        ).first()

    def get_by_scope(self, scope: str) -> List[PromptVariable]:
        return self.db.query(PromptVariable).filter(
            PromptVariable.scope == scope,
            PromptVariable.is_active == True
        ).all()

    def get_by_adapter(self, adapter: str) -> List[PromptVariable]:
        return self.db.query(PromptVariable).filter(
            PromptVariable.source_adapter == adapter,
            PromptVariable.is_active == True
        ).all()

    def get_by_category(self, category: str) -> List[PromptVariable]:
        return self.db.query(PromptVariable).filter(
            PromptVariable.category == category,
            PromptVariable.is_active == True
        ).all()

    def get_global(self) -> List[PromptVariable]:
        return self.db.query(PromptVariable).filter(
            PromptVariable.scope == 'GLOBAL',
            PromptVariable.is_active == True
        ).all()

    def name_exists(self, name: str, exclude_id: str = None) -> bool:
        query = self.db.query(PromptVariable).filter(PromptVariable.name == name)
        if exclude_id:
            query = query.filter(PromptVariable.id != exclude_id)
        return query.first() is not None

    def get_registry(self) -> List[PromptVariable]:
        return self.db.query(PromptVariable).filter(
            PromptVariable.is_active == True
        ).order_by(PromptVariable.scope, PromptVariable.name).all()
