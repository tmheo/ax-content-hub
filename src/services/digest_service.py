"""Digest service for creating and sending digests."""

import uuid
from datetime import UTC, date, datetime

from src.adapters.slack_client import SlackClient
from src.agent.domains.distributor.tools.slack_sender_tool import send_digest
from src.models.content import Content
from src.models.digest import Digest, DigestStatus, generate_digest_key
from src.models.subscription import Subscription
from src.repositories.content_repo import ContentRepository
from src.repositories.digest_repo import DigestRepository
from src.repositories.subscription_repo import SubscriptionRepository


class DigestService:
    """다이제스트 생성 및 발송 서비스."""

    def __init__(
        self,
        content_repo: ContentRepository,
        digest_repo: DigestRepository,
        subscription_repo: SubscriptionRepository,
        slack_client: SlackClient,
    ) -> None:
        """DigestService 초기화.

        Args:
            content_repo: 콘텐츠 리포지토리
            digest_repo: 다이제스트 리포지토리
            subscription_repo: 구독 리포지토리
            slack_client: Slack 클라이언트
        """
        self.content_repo = content_repo
        self.digest_repo = digest_repo
        self.subscription_repo = subscription_repo
        self.slack_client = slack_client

    def create_digest(
        self,
        subscription: Subscription,
        digest_date: date,
    ) -> Digest:
        """구독에 대한 다이제스트 생성.

        이미 존재하는 다이제스트가 있으면 기존 것을 반환합니다.

        Args:
            subscription: 구독 정보
            digest_date: 다이제스트 날짜

        Returns:
            생성된 또는 기존 다이제스트
        """
        digest_key = generate_digest_key(subscription.id, digest_date)

        # 이미 존재하는지 확인
        if self.digest_repo.exists_by_digest_key(digest_key):
            existing = self.digest_repo.get_by_digest_key(digest_key)
            if existing:
                return existing

        # 콘텐츠 조회
        min_relevance = subscription.preferences.min_relevance
        contents = self.content_repo.find_for_digest(
            min_relevance=min_relevance,
        )

        # 관련성 필터링 및 정렬
        filtered_contents = self._filter_by_relevance(contents, min_relevance)
        sorted_contents = self._sort_by_relevance(filtered_contents)

        content_ids = [c.id for c in sorted_contents]

        # 채널 ID 추출
        channel_id = subscription.platform_config.get("channel_id", "")

        # 다이제스트 생성
        digest = Digest(
            id=f"dgst_{uuid.uuid4().hex[:12]}",
            subscription_id=subscription.id,
            digest_key=digest_key,
            digest_date=digest_date,
            content_ids=content_ids,
            content_count=len(content_ids),
            channel_id=channel_id,
            status=DigestStatus.PENDING,
            created_at=datetime.now(UTC),
        )

        self.digest_repo.create(digest)
        return digest

    def send_digest(self, digest: Digest) -> bool:
        """다이제스트를 Slack으로 발송.

        Args:
            digest: 발송할 다이제스트

        Returns:
            발송 성공 여부
        """
        try:
            # 콘텐츠 조회
            contents = self.content_repo.find_by_ids(digest.content_ids)

            # 발송
            result = send_digest(
                digest=digest,
                contents=contents,
                slack_client=self.slack_client,
            )

            if result.success and result.message_ts:
                self.digest_repo.update_sent_info(digest.id, result.message_ts)
                # 콘텐츠를 다이제스트에 포함됨으로 마킹 (중복 발송 방지)
                self.content_repo.mark_as_included_in_digest(
                    digest.content_ids, digest.id
                )
                return True
            else:
                error_msg = result.error or "Unknown error"
                self.digest_repo.mark_as_failed(digest.id, error_msg)
                return False

        except Exception as e:
            self.digest_repo.mark_as_failed(digest.id, str(e))
            return False

    def process_pending_digests(self) -> dict[str, int]:
        """대기 중인 다이제스트 일괄 처리.

        Returns:
            처리 결과 통계 (total, sent, failed)
        """
        pending = self.digest_repo.find_pending_for_sending()

        results = {
            "total": len(pending),
            "sent": 0,
            "failed": 0,
        }

        for digest in pending:
            success = self.send_digest(digest)
            if success:
                results["sent"] += 1
            else:
                results["failed"] += 1

        return results

    def get_due_subscriptions(self, delivery_time: str) -> list[Subscription]:
        """배송 시간에 맞는 구독 조회.

        Args:
            delivery_time: 배송 시간 (HH:MM 형식)

        Returns:
            해당 시간에 발송해야 할 구독 목록
        """
        return self.subscription_repo.find_due_for_delivery(delivery_time)

    def create_and_send(
        self,
        subscription: Subscription,
        digest_date: date,
    ) -> bool:
        """구독에 대한 다이제스트 생성 및 발송.

        Args:
            subscription: 구독 정보
            digest_date: 다이제스트 날짜

        Returns:
            발송 성공 여부
        """
        digest = self.create_digest(subscription, digest_date)
        return self.send_digest(digest)

    def _filter_by_relevance(
        self,
        contents: list[Content],
        min_relevance: float,
    ) -> list[Content]:
        """관련성 점수로 콘텐츠 필터링.

        Args:
            contents: 필터링할 콘텐츠 목록
            min_relevance: 최소 관련성 점수

        Returns:
            필터링된 콘텐츠 목록
        """
        return [
            c
            for c in contents
            if c.relevance_score is not None and c.relevance_score >= min_relevance
        ]

    def _sort_by_relevance(self, contents: list[Content]) -> list[Content]:
        """관련성 점수로 콘텐츠 정렬 (내림차순).

        Args:
            contents: 정렬할 콘텐츠 목록

        Returns:
            정렬된 콘텐츠 목록
        """
        return sorted(
            contents,
            key=lambda c: c.relevance_score or 0.0,
            reverse=True,
        )
