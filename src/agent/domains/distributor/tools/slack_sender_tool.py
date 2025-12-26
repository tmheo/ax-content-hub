"""Slack digest sender tool.

Slack Block Kit을 사용하여 다이제스트 메시지를 구성하고 발송합니다.
50개 블록 제한을 고려하여 필요시 분할 발송합니다.
"""

from dataclasses import dataclass, field
from datetime import date
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


SLACK_BLOCKS_LIMIT = 50


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


def build_digest_blocks(
    digest_blocks: list[DigestBlock],
    digest_date: date,
) -> list[dict[str, Any]]:
    """Block Kit 형식의 다이제스트 블록 생성.

    Args:
        digest_blocks: 다이제스트에 포함될 콘텐츠 블록들
        digest_date: 다이제스트 날짜

    Returns:
        Block Kit 형식의 블록 리스트
    """
    blocks: list[dict[str, Any]] = []

    # 헤더 블록
    header_text = f":newspaper: AX 다이제스트 ({digest_date.isoformat()})"
    blocks.append(
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": header_text,
                "emoji": True,
            },
        }
    )

    # 콘텐츠가 없는 경우
    if not digest_blocks:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":information_source: 오늘은 새로운 AX 콘텐츠가 없습니다.",
                },
            }
        )
        return blocks

    # 요약 정보
    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f":memo: 오늘의 콘텐츠 *{len(digest_blocks)}*건",
                }
            ],
        }
    )

    blocks.append({"type": "divider"})

    # 각 콘텐츠 블록
    for i, digest_block in enumerate(digest_blocks):
        # 제목과 점수
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
                        f"*{i + 1}. {digest_block.title_ko}*\n"
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

        # 구분선 (마지막 항목 제외)
        if i < len(digest_blocks) - 1:
            blocks.append({"type": "divider"})

    # 푸터
    blocks.append({"type": "divider"})
    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": ":robot_face: _AX Content Hub에서 자동 생성됨_",
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


def split_blocks_for_slack(
    blocks: list[dict[str, Any]],
    limit: int = SLACK_BLOCKS_LIMIT,
) -> list[list[dict[str, Any]]]:
    """Slack 블록 제한에 맞게 분할.

    Args:
        blocks: 분할할 블록 리스트
        limit: 블록 제한 (기본 50)

    Returns:
        분할된 블록 리스트들
    """
    if not blocks:
        return [[]]

    if len(blocks) <= limit:
        return [blocks]

    result = []
    for i in range(0, len(blocks), limit):
        result.append(blocks[i : i + limit])

    return result


def send_digest(
    digest: Digest,
    contents: list[Content],
    slack_client: SlackClient,
) -> SendDigestResult:
    """다이제스트를 Slack으로 발송.

    Args:
        digest: 다이제스트 정보
        contents: 다이제스트에 포함될 콘텐츠들
        slack_client: Slack 클라이언트

    Returns:
        발송 결과
    """
    try:
        # Content를 DigestBlock으로 변환
        digest_blocks = [
            DigestBlock(
                content_id=content.id,
                title_ko=content.title_ko or content.original_title,
                summary_ko=content.summary_ko or "",
                why_important=content.why_important or "",
                relevance_score=content.relevance_score or 0.0,
                original_url=content.original_url,
                categories=content.categories or [],
            )
            for content in contents
        ]

        # Block Kit 블록 생성
        blocks = build_digest_blocks(
            digest_blocks=digest_blocks,
            digest_date=digest.digest_date,
        )

        # 블록 분할
        block_chunks = split_blocks_for_slack(blocks)

        # 첫 번째 메시지 발송
        first_result = slack_client.post_message(
            channel=digest.channel_id,
            blocks=block_chunks[0],
            text=f"AX 다이제스트 ({digest.digest_date.isoformat()})",
        )

        message_ts = first_result.get("ts")

        # 추가 청크가 있으면 스레드로 발송
        for chunk in block_chunks[1:]:
            slack_client.post_message(
                channel=digest.channel_id,
                blocks=chunk,
                text="(계속)",
                thread_ts=message_ts,
            )

        return SendDigestResult(
            success=True,
            message_ts=message_ts,
        )

    except Exception as e:
        return SendDigestResult(
            success=False,
            error=str(e),
        )
