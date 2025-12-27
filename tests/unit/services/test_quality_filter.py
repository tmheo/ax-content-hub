"""Tests for QualityFilter service."""

from datetime import UTC, datetime

import pytest

from src.models.content import Content, ProcessingStatus
from src.services.quality_filter import QualityFilter


class TestQualityFilter:
    """Tests for QualityFilter service."""

    @pytest.fixture
    def quality_filter(self) -> QualityFilter:
        """QualityFilter 인스턴스."""
        return QualityFilter()

    @pytest.fixture
    def sample_contents(self) -> list[Content]:
        """샘플 콘텐츠 목록."""
        now = datetime.now(UTC)
        return [
            Content(
                id="cnt_001",
                source_id="src_001",
                content_key="src_001:hash1",
                original_url="https://example.com/1",
                original_title="High Score Article",
                original_body="High relevance content",
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now,
                relevance_score=0.9,
                title_ko="높은 점수 기사",
                summary_ko="높은 관련성 콘텐츠",
                why_important="중요한 내용입니다",
                categories=["AI", "Technology"],
                processing_attempts=1,
                processed_at=now,
            ),
            Content(
                id="cnt_002",
                source_id="src_001",
                content_key="src_001:hash2",
                original_url="https://example.com/2",
                original_title="Medium Score Article",
                original_body="Medium relevance content",
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now,
                relevance_score=0.5,
                title_ko="중간 점수 기사",
                summary_ko="중간 관련성 콘텐츠",
                why_important="어느 정도 중요합니다",
                categories=["Technology"],
                processing_attempts=1,
                processed_at=now,
            ),
            Content(
                id="cnt_003",
                source_id="src_001",
                content_key="src_001:hash3",
                original_url="https://example.com/3",
                original_title="Low Score Article",
                original_body="Low relevance content",
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now,
                relevance_score=0.2,
                title_ko="낮은 점수 기사",
                summary_ko="낮은 관련성 콘텐츠",
                why_important="관련성이 낮습니다",
                categories=["General"],
                processing_attempts=1,
                processed_at=now,
            ),
            Content(
                id="cnt_004",
                source_id="src_001",
                content_key="src_001:hash4",
                original_url="https://example.com/4",
                original_title="Pending Article",
                original_body="Not processed yet",
                original_language="en",
                processing_status=ProcessingStatus.PENDING,
                collected_at=now,
                processing_attempts=0,
            ),
        ]

    def test_filter_by_min_relevance(
        self,
        quality_filter: QualityFilter,
        sample_contents: list[Content],
    ) -> None:
        """최소 관련성 점수로 필터링."""
        result = quality_filter.filter_by_relevance(
            contents=sample_contents,
            min_score=0.5,
        )

        assert len(result) == 2
        assert all(c.relevance_score >= 0.5 for c in result if c.relevance_score)

    def test_filter_by_processing_status(
        self,
        quality_filter: QualityFilter,
        sample_contents: list[Content],
    ) -> None:
        """처리 상태로 필터링."""
        result = quality_filter.filter_by_status(
            contents=sample_contents,
            status=ProcessingStatus.COMPLETED,
        )

        assert len(result) == 3
        assert all(c.processing_status == ProcessingStatus.COMPLETED for c in result)

    def test_filter_by_category(
        self,
        quality_filter: QualityFilter,
        sample_contents: list[Content],
    ) -> None:
        """카테고리로 필터링."""
        result = quality_filter.filter_by_category(
            contents=sample_contents,
            category="AI",
        )

        assert len(result) == 1
        assert result[0].id == "cnt_001"

    def test_filter_by_multiple_categories(
        self,
        quality_filter: QualityFilter,
        sample_contents: list[Content],
    ) -> None:
        """여러 카테고리로 필터링."""
        result = quality_filter.filter_by_categories(
            contents=sample_contents,
            categories=["AI", "Technology"],
        )

        assert len(result) == 2  # cnt_001 has AI, cnt_002 has Technology

    def test_sort_by_relevance_descending(
        self,
        quality_filter: QualityFilter,
        sample_contents: list[Content],
    ) -> None:
        """관련성 점수로 내림차순 정렬."""
        result = quality_filter.sort_by_relevance(
            contents=sample_contents,
            descending=True,
        )

        scores = [c.relevance_score or 0 for c in result]
        assert scores == sorted(scores, reverse=True)

    def test_sort_by_relevance_ascending(
        self,
        quality_filter: QualityFilter,
        sample_contents: list[Content],
    ) -> None:
        """관련성 점수로 오름차순 정렬."""
        result = quality_filter.sort_by_relevance(
            contents=sample_contents,
            descending=False,
        )

        scores = [c.relevance_score or 0 for c in result]
        assert scores == sorted(scores)

    def test_apply_filters_combined(
        self,
        quality_filter: QualityFilter,
        sample_contents: list[Content],
    ) -> None:
        """여러 필터 조합 적용."""
        result = quality_filter.apply_filters(
            contents=sample_contents,
            min_relevance=0.3,
            status=ProcessingStatus.COMPLETED,
            sort_by_relevance=True,
        )

        assert len(result) == 2  # 0.9 and 0.5, excluding 0.2 (< 0.3)
        assert result[0].relevance_score == 0.9
        assert result[1].relevance_score == 0.5

    def test_apply_filters_with_limit(
        self,
        quality_filter: QualityFilter,
        sample_contents: list[Content],
    ) -> None:
        """최대 결과 수 제한."""
        result = quality_filter.apply_filters(
            contents=sample_contents,
            min_relevance=0.1,
            status=ProcessingStatus.COMPLETED,
            sort_by_relevance=True,
            limit=2,
        )

        assert len(result) == 2

    def test_filter_empty_list(
        self,
        quality_filter: QualityFilter,
    ) -> None:
        """빈 목록 필터링."""
        result = quality_filter.filter_by_relevance(
            contents=[],
            min_score=0.5,
        )

        assert result == []

    def test_filter_no_matches(
        self,
        quality_filter: QualityFilter,
        sample_contents: list[Content],
    ) -> None:
        """일치하는 항목이 없는 경우."""
        result = quality_filter.filter_by_relevance(
            contents=sample_contents,
            min_score=0.95,
        )

        assert result == []

    def test_get_top_contents(
        self,
        quality_filter: QualityFilter,
        sample_contents: list[Content],
    ) -> None:
        """상위 N개 콘텐츠 조회."""
        result = quality_filter.get_top_contents(
            contents=sample_contents,
            n=2,
        )

        assert len(result) == 2
        assert result[0].relevance_score == 0.9
        assert result[1].relevance_score == 0.5

    def test_filter_excludes_null_scores(
        self,
        quality_filter: QualityFilter,
        sample_contents: list[Content],
    ) -> None:
        """점수가 없는 콘텐츠 제외."""
        # PENDING status content has no relevance_score
        result = quality_filter.filter_by_relevance(
            contents=sample_contents,
            min_score=0.0,  # Include all with scores
        )

        # Pending content (cnt_004) should be excluded as it has no score
        assert all(c.relevance_score is not None for c in result)
