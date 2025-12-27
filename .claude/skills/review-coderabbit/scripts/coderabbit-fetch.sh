#!/bin/bash
# Fetch CodeRabbit review comments for a PR using GraphQL
# Usage: ./coderabbit-fetch.sh <PR_NUMBER> [--json|--summary|--actionable]

set -euo pipefail

PR=${1:-}
FORMAT=${2:-"--actionable"}

if [[ -z "$PR" ]]; then
    echo "Usage: $0 <PR_NUMBER> [--json|--summary|--actionable]" >&2
    echo ""
    echo "Options:"
    echo "  --actionable  Only actionable thread comments (excludes nitpicks/summary) [default]"
    echo "  --json        All CodeRabbit comments in JSON"
    echo "  --summary     Human-readable summary"
    exit 1
fi

# Parse owner/repo
REPO_INFO=$(gh repo view --json owner,name -q '{owner: .owner.login, repo: .name}')
OWNER=$(echo "$REPO_INFO" | jq -r '.owner')
REPO=$(echo "$REPO_INFO" | jq -r '.repo')

# GraphQL query to get review threads with comments
QUERY='
query($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          isOutdated
          comments(first: 10) {
            nodes {
              id
              databaseId
              body
              path
              line
              startLine
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
# Note: GraphQL returns "coderabbitai" without [bot] suffix
# Filter out threads with empty comments first, with null safety
CODERABBIT_THREADS=$(echo "$RESULT" | jq '[.data.repository.pullRequest.reviewThreads.nodes // [] | .[] |
    select(.comments != null) |
    select(.comments.nodes != null) |
    select((.comments.nodes | length) > 0) |
    select(.comments.nodes[0].author != null) |
    select(.comments.nodes[0].author.login == "coderabbitai")]')

if [[ "$FORMAT" == "--summary" ]]; then
    # Summary format for human reading
    echo "$CODERABBIT_THREADS" | jq -r '.[] |
        select(.comments.nodes[0].path != null) |
        select(.comments.nodes[0].body | contains("Nitpick comments") | not) |
        "[\(if .comments.nodes[0].body | contains("🔴 Critical") then "CRITICAL"
           elif .comments.nodes[0].body | contains("🟠 Major") then "MAJOR"
           elif .comments.nodes[0].body | contains("🟡 Minor") then "MINOR"
           else "INFO" end)] \(.comments.nodes[0].path):\(.comments.nodes[0].line // "N/A") [\(if .isResolved then "RESOLVED" else "OPEN" end)] - \(.comments.nodes[0].body | split("\n")[0] | .[0:80])"'
elif [[ "$FORMAT" == "--json" ]]; then
    # JSON format - all comments
    echo "$CODERABBIT_THREADS" | jq '[.[] | {
        thread_id: .id,
        is_resolved: .isResolved,
        is_outdated: .isOutdated,
        comment_id: .comments.nodes[0].databaseId,
        path: .comments.nodes[0].path,
        line: .comments.nodes[0].line,
        severity: (if .comments.nodes[0].body | contains("🔴 Critical") then "critical"
                   elif .comments.nodes[0].body | contains("🟠 Major") then "major"
                   elif .comments.nodes[0].body | contains("🟡 Minor") then "minor"
                   else "info" end),
        has_suggestion: (.comments.nodes[0].body | contains("```suggestion")),
        has_ai_prompt: (.comments.nodes[0].body | contains("🤖 Prompt for AI Agents")),
        reply_count: (.comments.nodes | length),
        body_preview: (.comments.nodes[0].body | split("\n")[0:5] | join(" ") | .[0:200])
    }]'
else
    # Actionable only - unresolved thread comments with path, excluding nitpicks/summary
    # All severity levels (Critical, Major, Minor)
    # Use intermediate variable to extract first comment safely
    echo "$CODERABBIT_THREADS" | jq '[.[] |
        . as $thread |
        ($thread.comments.nodes[0]) as $comment |
        select($thread.isResolved == false) |
        select($comment.path != null) |
        select(($comment.body | contains("Nitpick comments")) | not) |
        select(($comment.body | contains("Actionable comments")) | not) |
        {
            thread_id: $thread.id,
            comment_id: $comment.databaseId,
            path: $comment.path,
            line: $comment.line,
            start_line: $comment.startLine,
            severity: (if ($comment.body | contains("🔴 Critical")) then "critical"
                       elif ($comment.body | contains("🟠 Major")) then "major"
                       else "minor" end),
            title: ($comment.body | split("\n") | map(select(contains("**") and (contains("Critical") or contains("Major") or contains("Minor") or contains("일치") or contains("오류") or contains("문제")))) | first // ($comment.body | split("\n")[2] | .[0:100])),
            has_suggestion: ($comment.body | contains("```suggestion")),
            suggestion: (if ($comment.body | contains("```suggestion"))
                        then ($comment.body | split("```suggestion")[1] | split("```")[0] | ltrimstr("\n") | rtrimstr("\n") // null)
                        else null end),
            has_ai_prompt: ($comment.body | contains("🤖 Prompt for AI Agents")),
            ai_prompt: (if ($comment.body | contains("🤖 Prompt for AI Agents"))
                       then ($comment.body | split("🤖 Prompt for AI Agents")[1] | split("```")[1] // null)
                       else null end),
            body: $comment.body
        }]'
fi
