#!/bin/bash
# Fetch CodeRabbit review threads with resolve status (GraphQL)
# Usage: ./coderabbit-threads.sh <PR_NUMBER> [--unresolved-only]

set -euo pipefail

PR=${1:-}
FILTER=${2:-""}

if [[ -z "$PR" ]]; then
    echo "Usage: $0 <PR_NUMBER> [--unresolved-only]" >&2
    exit 1
fi

# Parse owner/repo
REPO_INFO=$(gh repo view --json owner,name -q '{owner: .owner.login, repo: .name}')
OWNER=$(echo "$REPO_INFO" | jq -r '.owner')
REPO=$(echo "$REPO_INFO" | jq -r '.repo')

# GraphQL query
QUERY='
query($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          isOutdated
          comments(first: 1) {
            nodes {
              id
              body
              path
              line
              author {
                login
              }
            }
          }
        }
      }
    }
  }
}
'

# Fetch threads
RESULT=$(gh api graphql \
    -f query="$QUERY" \
    -f owner="$OWNER" \
    -f repo="$REPO" \
    -F pr="$PR")

# Filter for CodeRabbit threads only
# Note: GraphQL returns "coderabbitai" without [bot] suffix (unlike REST API)
if [[ "$FILTER" == "--unresolved-only" ]]; then
    echo "$RESULT" | jq '[.data.repository.pullRequest.reviewThreads.nodes[] |
        select(.comments.nodes[0].author.login == "coderabbitai") |
        select(.isResolved == false) |
        {
            thread_id: .id,
            is_resolved: .isResolved,
            is_outdated: .isOutdated,
            comment_id: .comments.nodes[0].id,
            path: .comments.nodes[0].path,
            line: .comments.nodes[0].line,
            body_preview: (.comments.nodes[0].body | split("\n")[0:3] | join(" ") | .[0:150])
        }]'
else
    echo "$RESULT" | jq '[.data.repository.pullRequest.reviewThreads.nodes[] |
        select(.comments.nodes[0].author.login == "coderabbitai") |
        {
            thread_id: .id,
            is_resolved: .isResolved,
            is_outdated: .isOutdated,
            comment_id: .comments.nodes[0].id,
            path: .comments.nodes[0].path,
            line: .comments.nodes[0].line,
            body_preview: (.comments.nodes[0].body | split("\n")[0:3] | join(" ") | .[0:150])
        }]'
fi
