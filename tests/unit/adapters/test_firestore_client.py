"""Tests for Firestore client."""

from unittest.mock import MagicMock, patch

import pytest


class TestFirestoreClient:
    """Test FirestoreClient class."""

    @pytest.fixture
    def mock_firestore_db(self) -> MagicMock:
        """Create a mock Firestore database client."""
        mock_db = MagicMock()
        mock_doc = MagicMock()
        mock_doc.get.return_value = MagicMock(
            exists=True,
            to_dict=lambda: {"field": "value"},
        )
        mock_doc.set = MagicMock()
        mock_doc.update = MagicMock()
        mock_doc.delete = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_doc
        return mock_db

    def test_get_document_exists(self, mock_firestore_db: MagicMock) -> None:
        """get should return document data when document exists."""
        with patch("google.cloud.firestore.Client", return_value=mock_firestore_db):
            from src.adapters.firestore_client import FirestoreClient

            client = FirestoreClient(project_id="test-project")
            result = client.get("test_collection", "doc_id")

            assert result == {"field": "value"}
            mock_firestore_db.collection.assert_called_with("test_collection")

    def test_get_document_not_exists(self, mock_firestore_db: MagicMock) -> None:
        """get should return None when document doesn't exist."""
        mock_firestore_db.collection.return_value.document.return_value.get.return_value = MagicMock(
            exists=False
        )

        with patch("google.cloud.firestore.Client", return_value=mock_firestore_db):
            from src.adapters.firestore_client import FirestoreClient

            client = FirestoreClient(project_id="test-project")
            result = client.get("test_collection", "doc_id")

            assert result is None

    def test_set_document(self, mock_firestore_db: MagicMock) -> None:
        """set should create or replace a document."""
        with patch("google.cloud.firestore.Client", return_value=mock_firestore_db):
            from src.adapters.firestore_client import FirestoreClient

            client = FirestoreClient(project_id="test-project")
            data = {"name": "test", "value": 123}
            client.set("test_collection", "doc_id", data)

            mock_firestore_db.collection.return_value.document.return_value.set.assert_called_once_with(
                data
            )

    def test_update_document(self, mock_firestore_db: MagicMock) -> None:
        """update should update specific fields in a document."""
        with patch("google.cloud.firestore.Client", return_value=mock_firestore_db):
            from src.adapters.firestore_client import FirestoreClient

            client = FirestoreClient(project_id="test-project")
            data = {"value": 456}
            client.update("test_collection", "doc_id", data)

            mock_firestore_db.collection.return_value.document.return_value.update.assert_called_once_with(
                data
            )

    def test_delete_document(self, mock_firestore_db: MagicMock) -> None:
        """delete should remove a document."""
        with patch("google.cloud.firestore.Client", return_value=mock_firestore_db):
            from src.adapters.firestore_client import FirestoreClient

            client = FirestoreClient(project_id="test-project")
            client.delete("test_collection", "doc_id")

            mock_firestore_db.collection.return_value.document.return_value.delete.assert_called_once()

    def test_query_documents(self, mock_firestore_db: MagicMock) -> None:
        """query should return matching documents."""
        mock_docs = [
            MagicMock(to_dict=lambda: {"id": "1", "status": "active"}),
            MagicMock(to_dict=lambda: {"id": "2", "status": "active"}),
        ]
        mock_query = MagicMock()
        mock_query.stream.return_value = iter(mock_docs)
        mock_firestore_db.collection.return_value.where.return_value = mock_query

        with patch("google.cloud.firestore.Client", return_value=mock_firestore_db):
            from src.adapters.firestore_client import FirestoreClient

            client = FirestoreClient(project_id="test-project")
            results = client.query("test_collection", [("status", "==", "active")])

            assert len(results) == 2
            assert results[0]["id"] == "1"
