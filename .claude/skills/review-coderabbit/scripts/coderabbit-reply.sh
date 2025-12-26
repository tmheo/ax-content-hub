#!/bin/bash
# Reply to a GitHub PR review thread using GraphQL
# Usage: ./coderabbit-reply.sh <THREAD_ID> <MESSAGE>
# Note: THREAD_ID from coderabbit-fetch.sh (e.g., PRRT_kwDOQiWGTc5l63qJ)

set -euo pipefail

THREAD_ID=${1:-}
MESSAGE=${2:-}

if [[ -z "$THREAD_ID" || -z "$MESSAGE" ]]; then
    echo "Usage: $0 <THREAD_ID> <MESSAGE>" >&2
    echo "Example: $0 PRRT_kwDOQiWGTc5l63qJ '✅ Addressed in commit abc1234'" >&2
    echo ""
    echo "Note: Get THREAD_ID from ./coderabbit-fetch.sh <PR> --json" >&2
    exit 1
fi

# GraphQL mutation to add reply to review thread
gh api graphql -f query='
  mutation($threadId: ID!, $body: String!) {
    addPullRequestReviewThreadReply(input: {pullRequestReviewThreadId: $threadId, body: $body}) {
      comment {
        id
        body
        createdAt
      }
    }
  }
' -f threadId="$THREAD_ID" -f body="$MESSAGE" \
  --jq '.data.addPullRequestReviewThreadReply.comment | {id, body, created_at: .createdAt}'

echo "Reply posted to thread $THREAD_ID"
