"""Quality filter service for content filtering and sorting.

콘텐츠 품질 기반 필터링 및 정렬 서비스입니다.
"""

import structlog

from src.models.content import Content, ProcessingStatus

logger = structlog.get_logger(__name__)


class QualityFilter:
    """콘텐츠 품질 필터링 서비스.

    관련성 점수, 처리 상태, 카테고리 등을 기반으로 콘텐츠를 필터링합니다.
    """

    def filter_by_relevance(
        self,
        contents: list[Content],
        min_score: float,
    ) -> list[Content]:
        """관련성 점수로 필터링.

        Args:
            contents: 필터링할 콘텐츠 목록
            min_score: 최소 관련성 점수 (0.0 ~ 1.0)

        Returns:
            필터링된 콘텐츠 목록
        """
        return [
            c
            for c in contents
            if c.relevance_score is not None and c.relevance_score >= min_score
        ]

    def filter_by_status(
        self,
        contents: list[Content],
        status: ProcessingStatus,
    ) -> list[Content]:
        """처리 상태로 필터링.

        Args:
            contents: 필터링할 콘텐츠 목록
            status: 필터링할 처리 상태

        Returns:
            필터링된 콘텐츠 목록
        """
        return [c for c in contents if c.processing_status == status]

    def filter_by_category(
        self,
        contents: list[Content],
        category: str,
    ) -> list[Content]:
        """카테고리로 필터링.

        Args:
            contents: 필터링할 콘텐츠 목록
            category: 필터링할 카테고리

        Returns:
            필터링된 콘텐츠 목록
        """
        return [c for c in contents if c.categories and category in c.categories]

    def filter_by_categories(
        self,
        contents: list[Content],
        categories: list[str],
    ) -> list[Content]:
        """여러 카테고리 중 하나라도 포함된 콘텐츠 필터링.

        Args:
            contents: 필터링할 콘텐츠 목록
            categories: 필터링할 카테고리 목록

        Returns:
            필터링된 콘텐츠 목록
        """
        category_set = set(categories)
        return [
            c
            for c in contents
            if c.categories and any(cat in category_set for cat in c.categories)
        ]

    def sort_by_relevance(
        self,
        contents: list[Content],
        descending: bool = True,
    ) -> list[Content]:
        """관련성 점수로 정렬.

        Args:
            contents: 정렬할 콘텐츠 목록
            descending: True면 내림차순, False면 오름차순

        Returns:
            정렬된 콘텐츠 목록
        """
        return sorted(
            contents,
            key=lambda c: c.relevance_score or 0,
            reverse=descending,
        )

    def apply_filters(
        self,
        contents: list[Content],
        min_relevance: float | None = None,
        status: ProcessingStatus | None = None,
        categories: list[str] | None = None,
        sort_by_relevance: bool = False,
        limit: int | None = None,
    ) -> list[Content]:
        """여러 필터를 조합하여 적용.

        Args:
            contents: 필터링할 콘텐츠 목록
            min_relevance: 최소 관련성 점수
            status: 처리 상태 필터
            categories: 카테고리 필터
            sort_by_relevance: 관련성 정렬 여부
            limit: 최대 결과 수

        Returns:
            필터링 및 정렬된 콘텐츠 목록
        """
        result = contents

        if status is not None:
            result = self.filter_by_status(result, status)

        if min_relevance is not None:
            result = self.filter_by_relevance(result, min_relevance)

        if categories:
            result = self.filter_by_categories(result, categories)

        if sort_by_relevance:
            result = self.sort_by_relevance(result, descending=True)

        if limit is not None:
            result = result[:limit]

        logger.debug(
            "quality_filter_applied",
            original_count=len(contents),
            filtered_count=len(result),
            min_relevance=min_relevance,
            status=status.value if status else None,
        )

        return result

    def get_top_contents(
        self,
        contents: list[Content],
        n: int,
        min_relevance: float = 0.0,
    ) -> list[Content]:
        """상위 N개 콘텐츠 조회.

        Args:
            contents: 콘텐츠 목록
            n: 조회할 상위 콘텐츠 수
            min_relevance: 최소 관련성 점수 (기본값: 0.0)

        Returns:
            상위 N개 콘텐츠 목록
        """
        filtered = self.filter_by_relevance(contents, min_relevance)
        sorted_contents = self.sort_by_relevance(filtered, descending=True)
        return sorted_contents[:n]
