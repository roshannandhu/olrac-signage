"""Base Service class for Clean Architecture Application Layer.

Encapsulates business operations, transaction management, and logging.
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session


class BaseService:
    """Base application service with transaction handling and structured logging."""

    def __init__(self, db: Session, logger: Optional[logging.Logger] = None):
        self.db = db
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def commit(self) -> None:
        """Commit current database transaction."""
        self.db.commit()

    def rollback(self) -> None:
        """Roll back current database transaction."""
        self.db.rollback()

    def refresh(self, entity: object) -> None:
        """Refresh instance from database."""
        self.db.refresh(entity)
