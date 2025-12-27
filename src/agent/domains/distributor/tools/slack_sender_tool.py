"""Slack digest sender tool.

Slack Block Kit을 사용하여 다이제스트 메시지를 구성하고 발송합니다.
각 콘텐츠를 개별 메시지로 발송합니다.
"""

from dataclasses import dataclass, field
from typing import Any

from markdown_to_mrkdwn import SlackMarkdownConverter

from src.adapters.slack_client import SlackClient
from src.models.content import Content
from src.models.digest import Digest

# Markdown → Slack mrkdwn 변환기 (싱글톤)
_mrkdwn_converter = SlackMarkdownConverter()


def to_mrkdwn(text: str) -> str:
    """표준 Markdown을 Slack mrkdwn으로 변환.

    Args:
        text: 변환할 Markdown 텍스트.

    Returns:
        Slack mrkdwn 형식 텍스트.
    """
    if not text:
        return text
    return _mrkdwn_converter.convert(text)


@dataclass
class DigestBlock:
    """다이제스트에 포함될 콘텐츠 블록 정보."""

    content_id: str
    title_ko: str
    summary_ko: str
    why_important: str
    relevance_score: float
    original_url: str
    categories: list[str] = field(default_factory=list)


@dataclass
class SlackDigestMessage:
    """Slack으로 발송할 다이제스트 메시지."""

    channel_id: str
    blocks: list[dict[str, Any]]
    thread_ts: str | None = None


@dataclass
class SendDigestResult:
    """다이제스트 발송 결과."""

    success: bool
    message_ts: str | None = None
    error: str | None = None


def build_content_blocks(digest_block: DigestBlock) -> list[dict[str, Any]]:
    """단일 콘텐츠에 대한 Block Kit 블록 생성.

    Args:
        digest_block: 콘텐츠 블록 정보

    Returns:
        Block Kit 형식의 블록 리스트
    """
    blocks: list[dict[str, Any]] = []

    score_percent = int(digest_block.relevance_score * 100)
    score_emoji = _get_score_emoji(digest_block.relevance_score)

    # 카테고리 태그
    category_tags = (
        " ".join(f"`{cat}`" for cat in digest_block.categories)
        if digest_block.categories
        else ""
    )

    # Markdown → Slack mrkdwn 변환
    summary_mrkdwn = to_mrkdwn(digest_block.summary_ko)
    why_important_mrkdwn = to_mrkdwn(digest_block.why_important)

    # 메인 섹션
    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{digest_block.title_ko}*\n"
                    f"{summary_mrkdwn}\n\n"
                    f":bulb: _{why_important_mrkdwn}_"
                ),
            },
        }
    )

    # 메타 정보 (점수, 카테고리)
    meta_text = f"{score_emoji} 관련성: *{score_percent}%*"
    if category_tags:
        meta_text += f"  |  {category_tags}"

    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": meta_text,
                }
            ],
        }
    )

    # 원문 링크 버튼
    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": ":link: 원문 보기",
                        "emoji": True,
                    },
                    "url": digest_block.original_url,
                    "action_id": f"view_original_{digest_block.content_id}",
                }
            ],
        }
    )

    return blocks


def _get_score_emoji(score: float) -> str:
    """점수에 따른 이모지 반환."""
    if score >= 0.8:
        return ":fire:"
    elif score >= 0.6:
        return ":star:"
    elif score >= 0.4:
        return ":thumbsup:"
    else:
        return ":information_source:"


def send_digest(
    digest: Digest,
    contents: list[Content],
    slack_client: SlackClient,
) -> SendDigestResult:
    """다이제스트를 Slack으로 발송.

    각 콘텐츠를 개별 메시지로 발송합니다.

    Args:
        digest: 다이제스트 정보
        contents: 다이제스트에 포함될 콘텐츠들
        slack_client: Slack 클라이언트

    Returns:
        발송 결과 (첫 번째 메시지의 timestamp 반환)
    """
    if not contents:
        return SendDigestResult(
            success=True,
            message_ts=None,
        )

    try:
        first_message_ts: str | None = None

        for content in contents:
            # Content를 DigestBlock으로 변환
            digest_block = DigestBlock(
                content_id=content.id,
                title_ko=content.title_ko or content.original_title,
                summary_ko=content.summary_ko or "",
                why_important=content.why_important or "",
                relevance_score=content.relevance_score or 0.0,
                original_url=content.original_url,
                categories=content.categories or [],
            )

            # Block Kit 블록 생성
            blocks = build_content_blocks(digest_block)

            # 메시지 발송
            result = slack_client.post_message(
                channel=digest.channel_id,
                blocks=blocks,
                text=digest_block.title_ko,
            )

            # 첫 번째 메시지의 timestamp 저장
            if first_message_ts is None:
                first_message_ts = result.get("ts")

        return SendDigestResult(
            success=True,
            message_ts=first_message_ts,
        )

    except Exception as e:
        return SendDigestResult(
            success=False,
            error=str(e),
        )
