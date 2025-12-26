"""Base repository for Firestore data access.

모든 Repository가 상속하는 기본 클래스.
"""

from datetime import date, datetime
from typing import Any, ClassVar, Generic, TypeVar

from pydantic import BaseModel, HttpUrl

from src.adapters.firestore_client import FirestoreClient

# Pydantic 모델 타입 변수
T = TypeVar("T", bound=BaseModel)


class BaseRepository(Generic[T]):
    """Firestore Repository 기본 클래스.

    각 도메인 Repository는 이 클래스를 상속하고
    collection_name과 model_class를 정의해야 합니다.

    Example:
        class SourceRepository(BaseRepository[Source]):
            collection_name = "sources"
            model_class = Source
    """

    collection_name: ClassVar[str]
    model_class: ClassVar[type[BaseModel]]

    def __init__(self, firestore_client: FirestoreClient) -> None:
        """Initialize repository with Firestore client.

        Args:
            firestore_client: Firestore 클라이언트 인스턴스.
        """
        self._db = firestore_client

    def get_by_id(self, doc_id: str) -> T | None:
        """ID로 문서 조회.

        Args:
            doc_id: 문서 ID.

        Returns:
            모델 인스턴스 또는 None.
        """
        data = self._db.get(self.collection_name, doc_id)
        if data is None:
            return None
        return self.model_class(**data)  # type: ignore[return-value]

    def create(self, model: T) -> None:
        """문서 생성.

        Args:
            model: 저장할 모델 인스턴스.
        """
        data = self._model_to_dict(model)
        self._db.set(self.collection_name, model.id, data)  # type: ignore[attr-defined]

    def update(self, model: T) -> None:
        """문서 업데이트 (전체 교체).

        Args:
            model: 업데이트할 모델 인스턴스.
        """
        data = self._model_to_dict(model)
        self._db.set(self.collection_name, model.id, data)  # type: ignore[attr-defined]

    def delete(self, doc_id: str) -> None:
        """문서 삭제.

        Args:
            doc_id: 삭제할 문서 ID.
        """
        self._db.delete(self.collection_name, doc_id)

    def find_by(self, filters: list[tuple[str, str, Any]]) -> list[T]:
        """필터로 문서 조회.

        Args:
            filters: (field, operator, value) 튜플 리스트.

        Returns:
            매칭되는 모델 인스턴스 리스트.
        """
        results = self._db.query(self.collection_name, filters)
        return [self.model_class(**data) for data in results]  # type: ignore[misc]

    def find_all(self) -> list[T]:
        """전체 문서 조회.

        Returns:
            모든 모델 인스턴스 리스트.
        """
        return self.find_by([])

    def exists(self, doc_id: str) -> bool:
        """문서 존재 여부 확인.

        Args:
            doc_id: 확인할 문서 ID.

        Returns:
            존재하면 True.
        """
        data = self._db.get(self.collection_name, doc_id)
        return data is not None

    def count(self, filters: list[tuple[str, str, Any]] | None = None) -> int:
        """문서 수 카운트.

        Args:
            filters: 선택적 필터 조건.

        Returns:
            매칭되는 문서 수.
        """
        results = self._db.query(self.collection_name, filters or [])
        return len(results)

    def _model_to_dict(self, model: T) -> dict[str, Any]:
        """모델을 Firestore 저장용 dict로 변환.

        Args:
            model: 변환할 모델.

        Returns:
            Firestore에 저장할 dict.
        """
        # mode='python' preserves datetime objects for Firestore
        data = model.model_dump(mode="python")
        return self._serialize_for_firestore(data)

    def _serialize_for_firestore(self, data: Any) -> Any:
        """Firestore에 저장 가능한 형태로 직렬화.

        HttpUrl, date 등 Firestore에서 직접 지원하지 않는 타입을 변환합니다.

        Args:
            data: 변환할 데이터.

        Returns:
            Firestore에 저장 가능한 데이터.
        """
        if isinstance(data, HttpUrl):
            return str(data)
        elif isinstance(data, date) and not isinstance(data, datetime):
            # date를 datetime으로 변환 (Firestore는 date를 직접 지원하지 않음)
            return datetime.combine(data, datetime.min.time())
        elif isinstance(data, dict):
            return {k: self._serialize_for_firestore(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._serialize_for_firestore(item) for item in data]
        return data
