"""Quality filter service for content filtering and sorting.

콘텐츠 품질 기반 필터링 및 정렬 서비스입니다.
"""

import re
from datetime import UTC, datetime, timedelta

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

    # ========================================================================
    # T049-T051: 중복 필터링 메서드 (Phase 5)
    # ========================================================================

    def _tokenize(self, text: str) -> set[str]:
        """텍스트를 토큰 집합으로 변환.

        대소문자를 무시하고 구두점을 제거하여 단어 집합을 반환합니다.

        Args:
            text: 토큰화할 텍스트

        Returns:
            소문자 단어 집합
        """
        if not text:
            return set()

        # 소문자로 변환하고 구두점 제거
        cleaned = re.sub(r"[^\w\s-]", "", text.lower())
        # 공백으로 분할하고 빈 문자열 제거
        tokens = {token.strip() for token in cleaned.split() if token.strip()}
        return tokens

    def _calculate_similarity(self, title1: str, title2: str) -> float:
        """두 제목 간의 Jaccard 유사도 계산.

        Jaccard similarity = |A intersection B| / |A union B|

        Args:
            title1: 첫 번째 제목
            title2: 두 번째 제목

        Returns:
            0.0 ~ 1.0 사이의 유사도
        """
        tokens1 = self._tokenize(title1)
        tokens2 = self._tokenize(title2)

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1 & tokens2
        union = tokens1 | tokens2

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def filter_duplicates(
        self,
        contents: list[Content],
        similarity_threshold: float = 0.85,
    ) -> list[Content]:
        """제목 유사도 기반으로 중복 콘텐츠 필터링.

        유사한 제목을 가진 콘텐츠 중 가장 최신 것만 유지합니다.

        Args:
            contents: 필터링할 콘텐츠 목록
            similarity_threshold: 중복으로 판단할 유사도 임계값 (기본값: 0.85)

        Returns:
            중복 제거된 콘텐츠 목록 (최신 우선)
        """
        if len(contents) <= 1:
            return contents

        # 수집일 기준 내림차순 정렬 (최신이 먼저)
        sorted_contents = sorted(
            contents,
            key=lambda c: c.collected_at,
            reverse=True,
        )

        # 중복 제거 결과
        unique_contents: list[Content] = []

        for content in sorted_contents:
            is_duplicate = False

            for existing in unique_contents:
                similarity = self._calculate_similarity(
                    content.original_title,
                    existing.original_title,
                )

                if similarity >= similarity_threshold:
                    is_duplicate = True
                    logger.debug(
                        "duplicate_detected",
                        content_id=content.id,
                        duplicate_of=existing.id,
                        similarity=similarity,
                    )
                    break

            if not is_duplicate:
                unique_contents.append(content)

        logger.debug(
            "duplicates_filtered",
            original_count=len(contents),
            unique_count=len(unique_contents),
            removed=len(contents) - len(unique_contents),
        )

        return unique_contents

    # ========================================================================
    # T053: 최신성 필터링 메서드 (Phase 6)
    # ========================================================================

    def filter_by_recency(
        self,
        contents: list[Content],
        max_age_days: int,
    ) -> list[Content]:
        """수집일 기준 최신성 필터링.

        Args:
            contents: 필터링할 콘텐츠 목록
            max_age_days: 최대 허용 나이 (일 단위)

        Returns:
            max_age_days 이내에 수집된 콘텐츠 목록
        """
        if not contents:
            return []

        cutoff_date = datetime.now(UTC) - timedelta(days=max_age_days)

        filtered = [c for c in contents if c.collected_at >= cutoff_date]

        logger.debug(
            "recency_filtered",
            original_count=len(contents),
            filtered_count=len(filtered),
            max_age_days=max_age_days,
        )

        return filtered

    # ========================================================================
    # T056-T057: 품질 필터링 및 통합 필터 메서드 (Phase 7)
    # ========================================================================

    def filter_by_quality(
        self,
        contents: list[Content],
        min_body_length: int = 100,
        require_title: bool = True,
    ) -> list[Content]:
        """콘텐츠 품질 기준 필터링.

        Args:
            contents: 필터링할 콘텐츠 목록
            min_body_length: 최소 본문 길이 (기본값: 100)
            require_title: 제목 필수 여부 (기본값: True)

        Returns:
            품질 기준을 만족하는 콘텐츠 목록
        """
        if not contents:
            return []

        filtered = []
        for content in contents:
            # 제목 확인
            if require_title and not content.original_title:
                continue

            # 본문 길이 확인
            body_length = len(content.original_body) if content.original_body else 0
            if body_length < min_body_length:
                continue

            filtered.append(content)

        logger.debug(
            "quality_filtered",
            original_count=len(contents),
            filtered_count=len(filtered),
            min_body_length=min_body_length,
            require_title=require_title,
        )

        return filtered

    def apply_all_filters(
        self,
        contents: list[Content],
        max_age_days: int | None = None,
        min_body_length: int | None = None,
        require_title: bool | None = None,
        similarity_threshold: float | None = None,
        min_relevance: float | None = None,
    ) -> list[Content]:
        """모든 필터를 조합하여 적용.

        Args:
            contents: 필터링할 콘텐츠 목록
            max_age_days: 최대 허용 나이 (일 단위)
            min_body_length: 최소 본문 길이
            require_title: 제목 필수 여부
            similarity_threshold: 중복 판단 유사도 임계값
            min_relevance: 최소 관련성 점수

        Returns:
            모든 필터를 통과한 콘텐츠 목록
        """
        result = contents

        # 1. 최신성 필터
        if max_age_days is not None:
            result = self.filter_by_recency(result, max_age_days)

        # 2. 품질 필터
        if min_body_length is not None or require_title is not None:
            result = self.filter_by_quality(
                result,
                min_body_length=min_body_length or 0,
                require_title=require_title if require_title is not None else False,
            )

        # 3. 중복 필터
        if similarity_threshold is not None:
            result = self.filter_duplicates(result, similarity_threshold)

        # 4. 관련성 필터
        if min_relevance is not None:
            result = self.filter_by_relevance(result, min_relevance)

        logger.debug(
            "all_filters_applied",
            original_count=len(contents),
            final_count=len(result),
        )

        return result
