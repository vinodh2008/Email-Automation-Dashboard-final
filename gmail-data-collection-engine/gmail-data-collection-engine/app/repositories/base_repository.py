import logging
from typing import Optional, List, Type, TypeVar
from sqlalchemy.orm import Session

logger = logging.getLogger("repository")

T = TypeVar('T')


class BaseRepository:
    def __init__(self, db: Session, model):
        self.db = db
        self.model = model

    def get_by_id(self, id: str) -> Optional[T]:
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_active(self) -> List[T]:
        return self.db.query(self.model).filter(self.model.is_active == True).all()

    def get_all(self) -> List[T]:
        return self.db.query(self.model).all()

    def create(self, **kwargs) -> T:
        instance = self.model(**kwargs)
        self.db.add(instance)
        self.db.flush()
        return instance

    def update(self, id: str, **kwargs) -> Optional[T]:
        instance = self.get_by_id(id)
        if not instance:
            return None
        for key, value in kwargs.items():
            if hasattr(instance, key) and value is not None:
                setattr(instance, key, value)
        self.db.flush()
        return instance

    def soft_delete(self, id: str) -> bool:
        instance = self.get_by_id(id)
        if not instance:
            return False
        instance.is_active = False
        self.db.flush()
        return True

    def count(self) -> int:
        return self.db.query(self.model).filter(self.model.is_active == True).count()

    def exists(self, id: str) -> bool:
        return self.db.query(self.model).filter(self.model.id == id).first() is not None
