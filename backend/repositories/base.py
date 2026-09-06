"""Base Repository for Clean Architecture persistence layer.

Encapsulates generic database CRUD operations and tenant-scoping logic away
from HTTP route handlers.
"""

from typing import Generic, TypeVar, Type, Optional, List, Any
from sqlalchemy.orm import Session, Query
from ..tenancy import TenantScope

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """Generic repository providing clean database operations for an ORM model."""

    def __init__(self, model: Type[ModelT], db: Session):
        self.model = model
        self.db = db

    def get_by_id(self, record_id: Any) -> Optional[ModelT]:
        """Fetch a single record by primary key id."""
        id_col = getattr(self.model, "id", None)
        if id_col is None:
            raise AttributeError(f"{self.model.__name__} has no 'id' column")
        return self.db.query(self.model).filter(id_col == record_id).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> List[ModelT]:
        """Fetch all records with optional offset and limit."""
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def add(self, entity: ModelT, auto_flush: bool = True) -> ModelT:
        """Add an entity to the session, optionally flushing."""
        self.db.add(entity)
        if auto_flush:
            self.db.flush()
        return entity

    def delete(self, entity: ModelT, auto_flush: bool = True) -> None:
        """Remove an entity from the session."""
        self.db.delete(entity)
        if auto_flush:
            self.db.flush()

    def query(self) -> Query:
        """Direct raw query on this model."""
        return self.db.query(self.model)

    def scoped_query(self, scope: TenantScope) -> Query:
        """Tenant-isolated query utilizing TenantScope."""
        return scope.query(self.model)

    def get_scoped(self, scope: TenantScope, record_id: Any) -> Optional[ModelT]:
        """Fetch a record by id within the tenant's security scope."""
        return scope.get(self.model, record_id)
