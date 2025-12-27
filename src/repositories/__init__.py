"""Repository layer for Firestore data access.

This module exports all repository classes for data persistence.
"""

from src.repositories.base import BaseRepository
from src.repositories.content_repo import ContentRepository
from src.repositories.digest_repo import DigestRepository
from src.repositories.source_repo import SourceRepository
from src.repositories.subscription_repo import SubscriptionRepository

__all__ = [
    "BaseRepository",
    "ContentRepository",
    "DigestRepository",
    "SourceRepository",
    "SubscriptionRepository",
]
