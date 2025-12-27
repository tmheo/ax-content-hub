"""Firestore database client."""

from typing import Any

from google.cloud import firestore  # type: ignore[attr-defined]
from google.cloud.firestore_v1.base_query import FieldFilter


class FirestoreClient:
    """Client for Firestore CRUD operations.

    Automatically connects to emulator when FIRESTORE_EMULATOR_HOST is set.
    """

    def __init__(self, project_id: str) -> None:
        """Initialize Firestore client.

        Args:
            project_id: GCP project ID.
        """
        self._db = firestore.Client(project=project_id)

    def get(self, collection: str, doc_id: str) -> dict[str, Any] | None:
        """Get a document by ID.

        Args:
            collection: Collection name.
            doc_id: Document ID.

        Returns:
            Document data or None if not found.
        """
        doc = self._db.collection(collection).document(doc_id).get()
        if doc.exists:
            return doc.to_dict()
        return None

    def set(self, collection: str, doc_id: str, data: dict[str, Any]) -> None:
        """Create or replace a document.

        Args:
            collection: Collection name.
            doc_id: Document ID.
            data: Document data.
        """
        self._db.collection(collection).document(doc_id).set(data)

    def update(self, collection: str, doc_id: str, data: dict[str, Any]) -> None:
        """Update specific fields in a document.

        Args:
            collection: Collection name.
            doc_id: Document ID.
            data: Fields to update.
        """
        self._db.collection(collection).document(doc_id).update(data)

    def delete(self, collection: str, doc_id: str) -> None:
        """Delete a document.

        Args:
            collection: Collection name.
            doc_id: Document ID.
        """
        self._db.collection(collection).document(doc_id).delete()

    def query(
        self, collection: str, filters: list[tuple[str, str, Any]]
    ) -> list[dict[str, Any]]:
        """Query documents with filters.

        Args:
            collection: Collection name.
            filters: List of (field, operator, value) tuples.

        Returns:
            List of matching documents.
        """
        query = self._db.collection(collection)
        for field, op, value in filters:
            query = query.where(filter=FieldFilter(field, op, value))

        return [doc.to_dict() for doc in query.stream()]
