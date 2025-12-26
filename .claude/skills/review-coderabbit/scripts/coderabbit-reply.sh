#!/bin/bash
# Reply to a GitHub PR review comment
# Usage: ./coderabbit-reply.sh <PR_NUMBER> <COMMENT_ID> <MESSAGE>

set -euo pipefail

PR=${1:-}
COMMENT_ID=${2:-}
MESSAGE=${3:-}

if [[ -z "$PR" || -z "$COMMENT_ID" || -z "$MESSAGE" ]]; then
    echo "Usage: $0 <PR_NUMBER> <COMMENT_ID> <MESSAGE>" >&2
    echo "Example: $0 23 2615862695 '✅ Addressed in commit abc1234'" >&2
    exit 1
fi

REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner')

gh api "repos/${REPO}/pulls/${PR}/comments" \
    --method POST \
    -f body="$MESSAGE" \
    -F in_reply_to="$COMMENT_ID" \
    --jq '{id: .id, body: .body, created_at: .created_at}'

echo "Reply posted to comment $COMMENT_ID"
