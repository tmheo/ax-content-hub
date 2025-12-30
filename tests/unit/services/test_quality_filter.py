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


# ============================================================================
# T045-T048: 중복 필터링 테스트 (Phase 5)
# ============================================================================


class TestDuplicateFiltering:
    """중복 콘텐츠 필터링 테스트."""

    @pytest.fixture
    def quality_filter(self) -> QualityFilter:
        """QualityFilter 인스턴스."""
        return QualityFilter()

    @pytest.fixture
    def duplicate_contents(self) -> list[Content]:
        """중복 제목을 가진 샘플 콘텐츠 목록."""
        from datetime import timedelta

        now = datetime.now(UTC)
        return [
            Content(
                id="cnt_001",
                source_id="src_001",
                content_key="src_001:hash1",
                original_url="https://example.com/1",
                original_title="OpenAI Announces GPT-5 Release",
                original_body="Original content",
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now - timedelta(hours=2),  # 2시간 전 (오래된 것)
                relevance_score=0.9,
            ),
            Content(
                id="cnt_002",
                source_id="src_002",
                content_key="src_002:hash2",
                original_url="https://example2.com/1",
                original_title="OpenAI Announces GPT-5 Release Today",  # 유사
                original_body="Slightly different content",
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now,  # 최신
                relevance_score=0.85,
            ),
            Content(
                id="cnt_003",
                source_id="src_003",
                content_key="src_003:hash3",
                original_url="https://example3.com/1",
                original_title="Completely Different Article",  # 다른 제목
                original_body="Different topic",
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now - timedelta(hours=1),
                relevance_score=0.7,
            ),
            Content(
                id="cnt_004",
                source_id="src_004",
                content_key="src_004:hash4",
                original_url="https://example4.com/1",
                original_title="GPT-5 Released by OpenAI",  # 유사 (단어 순서 다름)
                original_body="Another similar content",
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now - timedelta(hours=3),  # 가장 오래된 것
                relevance_score=0.8,
            ),
        ]

    # T046: _tokenize() 테스트
    def test_tokenize_basic(self, quality_filter: QualityFilter) -> None:
        """기본 토큰화 테스트."""
        title = "OpenAI Announces GPT-5 Release"
        tokens = quality_filter._tokenize(title)

        assert isinstance(tokens, set)
        assert "openai" in tokens
        assert "announces" in tokens
        assert "gpt" in tokens or "gpt-5" in tokens
        assert "release" in tokens

    def test_tokenize_case_insensitive(self, quality_filter: QualityFilter) -> None:
        """대소문자 무시 토큰화."""
        title1 = "OpenAI GPT"
        title2 = "openai gpt"

        tokens1 = quality_filter._tokenize(title1)
        tokens2 = quality_filter._tokenize(title2)

        assert tokens1 == tokens2

    def test_tokenize_removes_punctuation(self, quality_filter: QualityFilter) -> None:
        """구두점 제거 토큰화."""
        title = "Hello, World! How are you?"
        tokens = quality_filter._tokenize(title)

        assert "hello" in tokens
        assert "world" in tokens
        # 각 토큰에 구두점이 포함되어 있지 않음
        for token in tokens:
            assert "," not in token
            assert "!" not in token
            assert "?" not in token

    def test_tokenize_empty_string(self, quality_filter: QualityFilter) -> None:
        """빈 문자열 토큰화."""
        tokens = quality_filter._tokenize("")
        assert tokens == set()

    # T047: _calculate_similarity() Jaccard 유사도 테스트
    def test_calculate_similarity_identical(
        self, quality_filter: QualityFilter
    ) -> None:
        """동일 제목 유사도 = 1.0."""
        title = "OpenAI Announces GPT-5"
        similarity = quality_filter._calculate_similarity(title, title)
        assert similarity == 1.0

    def test_calculate_similarity_completely_different(
        self, quality_filter: QualityFilter
    ) -> None:
        """완전히 다른 제목 유사도 = 0.0."""
        title1 = "Apple iPhone Release"
        title2 = "Weather Forecast Today"
        similarity = quality_filter._calculate_similarity(title1, title2)
        assert similarity == 0.0

    def test_calculate_similarity_partial_overlap(
        self, quality_filter: QualityFilter
    ) -> None:
        """부분 일치 유사도."""
        title1 = "OpenAI Announces GPT-5 Release"
        title2 = "OpenAI Announces GPT-5 Release Today"
        similarity = quality_filter._calculate_similarity(title1, title2)
        # Jaccard: intersection / union
        # 공통 토큰 많으므로 높은 유사도
        assert 0.7 < similarity < 1.0

    def test_calculate_similarity_word_order_different(
        self, quality_filter: QualityFilter
    ) -> None:
        """단어 순서 다른 경우."""
        title1 = "GPT-5 Released by OpenAI"
        title2 = "OpenAI Released GPT-5"
        similarity = quality_filter._calculate_similarity(title1, title2)
        # Jaccard는 순서 무관
        assert similarity > 0.7

    def test_calculate_similarity_empty_string(
        self, quality_filter: QualityFilter
    ) -> None:
        """빈 문자열과의 유사도."""
        similarity = quality_filter._calculate_similarity("Some Title", "")
        assert similarity == 0.0

    # T048: filter_duplicates() 테스트
    def test_filter_duplicates_removes_similar_titles(
        self,
        quality_filter: QualityFilter,
        duplicate_contents: list[Content],
    ) -> None:
        """유사한 제목의 중복 제거."""
        result = quality_filter.filter_duplicates(
            contents=duplicate_contents,
            similarity_threshold=0.7,
        )

        # 4개 중 2개는 중복으로 제거됨 (GPT-5 관련 3개 → 1개)
        assert len(result) < len(duplicate_contents)
        # 최소 2개는 남아야 함 (서로 다른 콘텐츠)
        assert len(result) >= 2

    def test_filter_duplicates_keeps_newest(
        self,
        quality_filter: QualityFilter,
        duplicate_contents: list[Content],
    ) -> None:
        """중복 중 최신 콘텐츠 유지."""
        result = quality_filter.filter_duplicates(
            contents=duplicate_contents,
            similarity_threshold=0.7,
        )

        # cnt_002가 GPT-5 관련 중 최신이므로 유지되어야 함
        ids = [c.id for c in result]
        assert "cnt_002" in ids  # 최신
        # cnt_001, cnt_004는 중복으로 제거됨
        assert "cnt_001" not in ids or "cnt_004" not in ids

    def test_filter_duplicates_low_threshold(
        self,
        quality_filter: QualityFilter,
        duplicate_contents: list[Content],
    ) -> None:
        """낮은 임계값 - 더 많이 중복 처리."""
        result = quality_filter.filter_duplicates(
            contents=duplicate_contents,
            similarity_threshold=0.3,  # 낮은 임계값
        )

        # 낮은 임계값이면 더 많이 중복 처리됨
        assert len(result) <= 3

    def test_filter_duplicates_high_threshold(
        self,
        quality_filter: QualityFilter,
        duplicate_contents: list[Content],
    ) -> None:
        """높은 임계값 - 거의 동일해야 중복 처리."""
        result = quality_filter.filter_duplicates(
            contents=duplicate_contents,
            similarity_threshold=0.95,  # 거의 동일해야 중복
        )

        # 높은 임계값이면 대부분 유지
        assert len(result) >= 3

    def test_filter_duplicates_empty_list(
        self,
        quality_filter: QualityFilter,
    ) -> None:
        """빈 목록 필터링."""
        result = quality_filter.filter_duplicates(
            contents=[],
            similarity_threshold=0.85,
        )
        assert result == []

    def test_filter_duplicates_single_item(
        self,
        quality_filter: QualityFilter,
        duplicate_contents: list[Content],
    ) -> None:
        """단일 항목은 그대로 반환."""
        single = [duplicate_contents[0]]
        result = quality_filter.filter_duplicates(
            contents=single,
            similarity_threshold=0.85,
        )
        assert len(result) == 1
        assert result[0].id == "cnt_001"

    def test_filter_duplicates_preserves_unique_content(
        self,
        quality_filter: QualityFilter,
        duplicate_contents: list[Content],
    ) -> None:
        """유일한 콘텐츠는 항상 유지."""
        result = quality_filter.filter_duplicates(
            contents=duplicate_contents,
            similarity_threshold=0.7,
        )

        # "Completely Different Article"는 항상 유지
        ids = [c.id for c in result]
        assert "cnt_003" in ids


# ============================================================================
# T052: 최신성 필터링 테스트 (Phase 6)
# ============================================================================


class TestRecencyFiltering:
    """최신성 기반 콘텐츠 필터링 테스트."""

    @pytest.fixture
    def quality_filter(self) -> QualityFilter:
        """QualityFilter 인스턴스."""
        return QualityFilter()

    @pytest.fixture
    def recency_contents(self) -> list[Content]:
        """다양한 수집일을 가진 샘플 콘텐츠 목록."""
        from datetime import timedelta

        now = datetime.now(UTC)
        return [
            Content(
                id="cnt_today",
                source_id="src_001",
                content_key="src_001:hash1",
                original_url="https://example.com/today",
                original_title="Today's Article",
                original_body="Content from today",
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now,  # 오늘
                relevance_score=0.9,
            ),
            Content(
                id="cnt_3days",
                source_id="src_001",
                content_key="src_001:hash2",
                original_url="https://example.com/3days",
                original_title="3 Days Old Article",
                original_body="Content from 3 days ago",
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                # 정확히 3일이 아닌 2일 23시간으로 설정 (시간 차이 문제 방지)
                collected_at=now - timedelta(days=2, hours=23),
                relevance_score=0.8,
            ),
            Content(
                id="cnt_7days",
                source_id="src_001",
                content_key="src_001:hash3",
                original_url="https://example.com/7days",
                original_title="Week Old Article",
                original_body="Content from a week ago",
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                # 정확히 7일이 아닌 6일 23시간으로 설정 (시간 차이 문제 방지)
                collected_at=now - timedelta(days=6, hours=23),
                relevance_score=0.7,
            ),
            Content(
                id="cnt_14days",
                source_id="src_001",
                content_key="src_001:hash4",
                original_url="https://example.com/14days",
                original_title="Two Weeks Old Article",
                original_body="Content from 2 weeks ago",
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now - timedelta(days=14),
                relevance_score=0.6,
            ),
        ]

    def test_filter_by_recency_7_days(
        self,
        quality_filter: QualityFilter,
        recency_contents: list[Content],
    ) -> None:
        """7일 이내 콘텐츠만 필터링."""
        result = quality_filter.filter_by_recency(
            contents=recency_contents,
            max_age_days=7,
        )

        assert len(result) == 3  # today, 3days, 7days
        ids = [c.id for c in result]
        assert "cnt_today" in ids
        assert "cnt_3days" in ids
        assert "cnt_7days" in ids
        assert "cnt_14days" not in ids

    def test_filter_by_recency_3_days(
        self,
        quality_filter: QualityFilter,
        recency_contents: list[Content],
    ) -> None:
        """3일 이내 콘텐츠만 필터링."""
        result = quality_filter.filter_by_recency(
            contents=recency_contents,
            max_age_days=3,
        )

        assert len(result) == 2  # today, 3days
        ids = [c.id for c in result]
        assert "cnt_today" in ids
        assert "cnt_3days" in ids

    def test_filter_by_recency_30_days(
        self,
        quality_filter: QualityFilter,
        recency_contents: list[Content],
    ) -> None:
        """30일 이내면 모든 콘텐츠 포함."""
        result = quality_filter.filter_by_recency(
            contents=recency_contents,
            max_age_days=30,
        )

        assert len(result) == 4  # 모두 포함

    def test_filter_by_recency_empty_list(
        self,
        quality_filter: QualityFilter,
    ) -> None:
        """빈 목록 필터링."""
        result = quality_filter.filter_by_recency(
            contents=[],
            max_age_days=7,
        )
        assert result == []


# ============================================================================
# T054-T055: 품질 필터링 테스트 (Phase 7)
# ============================================================================


class TestQualityFiltering:
    """콘텐츠 품질 기반 필터링 테스트."""

    @pytest.fixture
    def quality_filter(self) -> QualityFilter:
        """QualityFilter 인스턴스."""
        return QualityFilter()

    @pytest.fixture
    def quality_contents(self) -> list[Content]:
        """다양한 품질의 샘플 콘텐츠 목록."""
        now = datetime.now(UTC)
        return [
            Content(
                id="cnt_good",
                source_id="src_001",
                content_key="src_001:hash1",
                original_url="https://example.com/good",
                original_title="Good Quality Article",
                original_body="A" * 500,  # 충분한 길이
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now,
                relevance_score=0.9,
            ),
            Content(
                id="cnt_short",
                source_id="src_001",
                content_key="src_001:hash2",
                original_url="https://example.com/short",
                original_title="Short Article",
                original_body="Too short",  # 짧은 본문
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now,
                relevance_score=0.8,
            ),
            Content(
                id="cnt_no_title",
                source_id="src_001",
                content_key="src_001:hash3",
                original_url="https://example.com/no-title",
                original_title="",  # 빈 제목
                original_body="B" * 500,
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now,
                relevance_score=0.7,
            ),
            Content(
                id="cnt_no_body",
                source_id="src_001",
                content_key="src_001:hash4",
                original_url="https://example.com/no-body",
                original_title="No Body Article",
                original_body=None,  # 본문 없음
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now,
                relevance_score=0.6,
            ),
        ]

    def test_filter_by_quality_min_body_length(
        self,
        quality_filter: QualityFilter,
        quality_contents: list[Content],
    ) -> None:
        """최소 본문 길이 필터링."""
        result = quality_filter.filter_by_quality(
            contents=quality_contents,
            min_body_length=100,
            require_title=False,
        )

        # 본문이 100자 이상인 것만 포함
        assert len(result) == 2  # good, no_title
        ids = [c.id for c in result]
        assert "cnt_good" in ids
        assert "cnt_no_title" in ids

    def test_filter_by_quality_require_title(
        self,
        quality_filter: QualityFilter,
        quality_contents: list[Content],
    ) -> None:
        """제목 필수 필터링."""
        result = quality_filter.filter_by_quality(
            contents=quality_contents,
            min_body_length=0,
            require_title=True,
        )

        # 제목이 있는 것만 포함 (빈 문자열 제외)
        assert len(result) == 3  # good, short, no_body
        ids = [c.id for c in result]
        assert "cnt_no_title" not in ids

    def test_filter_by_quality_combined(
        self,
        quality_filter: QualityFilter,
        quality_contents: list[Content],
    ) -> None:
        """본문 길이 + 제목 필수 조합."""
        result = quality_filter.filter_by_quality(
            contents=quality_contents,
            min_body_length=100,
            require_title=True,
        )

        # 둘 다 만족하는 것만
        assert len(result) == 1
        assert result[0].id == "cnt_good"

    def test_filter_by_quality_empty_list(
        self,
        quality_filter: QualityFilter,
    ) -> None:
        """빈 목록 필터링."""
        result = quality_filter.filter_by_quality(
            contents=[],
            min_body_length=100,
        )
        assert result == []

    # T055: apply_all_filters() 통합 테스트
    def test_apply_all_filters_combined(
        self,
        quality_filter: QualityFilter,
    ) -> None:
        """모든 필터 조합 적용."""
        from datetime import timedelta

        now = datetime.now(UTC)
        contents = [
            # 좋은 콘텐츠: 최신, 좋은 품질, 높은 점수
            Content(
                id="cnt_best",
                source_id="src_001",
                content_key="src_001:hash1",
                original_url="https://example.com/best",
                original_title="Best Article",
                original_body="A" * 200,
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now,
                relevance_score=0.95,
            ),
            # 오래된 콘텐츠
            Content(
                id="cnt_old",
                source_id="src_001",
                content_key="src_001:hash2",
                original_url="https://example.com/old",
                original_title="Old Article",
                original_body="B" * 200,
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now - timedelta(days=30),
                relevance_score=0.9,
            ),
            # 짧은 본문
            Content(
                id="cnt_short",
                source_id="src_001",
                content_key="src_001:hash3",
                original_url="https://example.com/short",
                original_title="Short Article",
                original_body="Short",
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now,
                relevance_score=0.85,
            ),
            # 낮은 관련성
            Content(
                id="cnt_low_score",
                source_id="src_001",
                content_key="src_001:hash4",
                original_url="https://example.com/low",
                original_title="Low Score Article",
                original_body="C" * 200,
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now,
                relevance_score=0.2,
            ),
            # 중복 제목
            Content(
                id="cnt_duplicate",
                source_id="src_002",
                content_key="src_002:hash5",
                original_url="https://example2.com/best",
                original_title="Best Article Today",  # 유사
                original_body="D" * 200,
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now - timedelta(hours=1),  # cnt_best보다 오래됨
                relevance_score=0.9,
            ),
        ]

        result = quality_filter.apply_all_filters(
            contents=contents,
            max_age_days=7,
            min_body_length=100,
            require_title=True,
            # "Best Article"(2 tokens) vs "Best Article Today"(3 tokens) = 2/3 = 0.667
            similarity_threshold=0.65,
            min_relevance=0.5,
        )

        # cnt_best만 모든 조건 통과
        assert len(result) == 1
        assert result[0].id == "cnt_best"

    def test_apply_all_filters_partial(
        self,
        quality_filter: QualityFilter,
    ) -> None:
        """일부 필터만 적용."""
        now = datetime.now(UTC)
        contents = [
            Content(
                id="cnt_1",
                source_id="src_001",
                content_key="src_001:hash1",
                original_url="https://example.com/1",
                original_title="Article 1",
                original_body="A" * 200,
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now,
                relevance_score=0.9,
            ),
            Content(
                id="cnt_2",
                source_id="src_001",
                content_key="src_001:hash2",
                original_url="https://example.com/2",
                original_title="Article 2",
                original_body="B" * 200,
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now,
                relevance_score=0.8,
            ),
        ]

        # 품질 필터만 적용 (중복, 최신성 필터 없음)
        result = quality_filter.apply_all_filters(
            contents=contents,
            min_body_length=100,
            require_title=True,
        )

        assert len(result) == 2
