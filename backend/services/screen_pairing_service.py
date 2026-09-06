"""Screen Hardware Pairing and Enrollment Application Service."""

import logging
import random
import string
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from .base import BaseService
from ..repositories.screen_repo import ScreenRepository
from .. import models

logger = logging.getLogger(__name__)


def generate_pair_code() -> str:
    """Generate a 6-digit numeric pairing code for screen display."""
    return "".join(random.choices(string.digits, k=6))


def as_aware_utc(value: datetime) -> datetime:
    """Ensure datetime has explicit UTC timezone awareness."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class ScreenPairingService(BaseService):
    """Application Service managing pairing codes, onboarding tokens, and hardware admission."""

    def __init__(self, db: Session, repo: Optional[ScreenRepository] = None):
        super().__init__(db)
        self.repo = repo or ScreenRepository(db)

    def generate_code(self) -> str:
        return generate_pair_code()
