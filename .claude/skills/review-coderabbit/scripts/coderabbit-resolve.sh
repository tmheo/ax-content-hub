#!/bin/bash
# Resolve a GitHub review thread
# Usage: ./coderabbit-resolve.sh <THREAD_ID>

set -euo pipefail

THREAD_ID=${1:-}

if [[ -z "$THREAD_ID" ]]; then
    echo "Usage: $0 <THREAD_ID>" >&2
    echo "Example: $0 PRRT_kwDOQiWGTc5l63qJ" >&2
    exit 1
fi

gh api graphql -f query='
  mutation($threadId: ID!) {
    resolveReviewThread(input: {threadId: $threadId}) {
      thread {
        id
        isResolved
      }
    }
  }
' -f threadId="$THREAD_ID" --jq '.data.resolveReviewThread.thread'

echo "Thread $THREAD_ID resolved successfully"
