#!/bin/bash
# Fetch CodeRabbit review comments for a PR
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

REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner')

if [[ "$FORMAT" == "--summary" ]]; then
    # Summary format for human reading
    gh api "repos/${REPO}/pulls/${PR}/comments" \
        --jq '.[] | select(.user.login == "coderabbitai[bot]") |
        select(.path != null) |
        select(.body | contains("Nitpick comments") | not) |
        "[\(if .body | contains("🔴 Critical") then "CRITICAL"
           elif .body | contains("🟠 Major") then "MAJOR"
           elif .body | contains("🟡 Minor") then "MINOR"
           else "INFO" end)] \(.path):\(.line // "N/A") - \(.body | split("\n")[0] | .[0:80])"'
elif [[ "$FORMAT" == "--json" ]]; then
    # JSON format - all comments
    gh api "repos/${REPO}/pulls/${PR}/comments" \
        --jq '[.[] | select(.user.login == "coderabbitai[bot]") | {
            id: .id,
            path: .path,
            line: .line,
            severity: (if .body | contains("🔴 Critical") then "critical"
                       elif .body | contains("🟠 Major") then "major"
                       elif .body | contains("🟡 Minor") then "minor"
                       else "info" end),
            has_suggestion: (.body | contains("```suggestion")),
            has_ai_prompt: (.body | contains("🤖 Prompt for AI Agents")),
            is_addressed: (.body | contains("✅ Addressed")),
            body_preview: (.body | split("\n")[0:5] | join(" ") | .[0:200])
        }]'
else
    # Actionable only - thread comments with path, excluding nitpicks/summary
    # Focus on Critical and Major issues
    gh api "repos/${REPO}/pulls/${PR}/comments" \
        --jq '[.[] | select(.user.login == "coderabbitai[bot]") |
        select(.path != null) |
        select(.body | contains("Nitpick comments") | not) |
        select(.body | contains("Actionable comments") | not) |
        select((.body | contains("🔴 Critical")) or (.body | contains("🟠 Major"))) |
        {
            id: .id,
            path: .path,
            line: .line,
            start_line: .start_line,
            severity: (if .body | contains("🔴 Critical") then "critical" else "major" end),
            title: (.body | split("\n") | map(select(contains("**") and (contains("Critical") or contains("Major") or contains("일치") or contains("오류") or contains("문제")))) | first // (.body | split("\n")[2] | .[0:100])),
            has_suggestion: (.body | contains("```suggestion")),
            suggestion: (if .body | contains("```suggestion")
                        then (.body | capture("```suggestion\\n(?<code>[\\s\\S]*?)\\n```") | .code // null)
                        else null end),
            has_ai_prompt: (.body | contains("🤖 Prompt for AI Agents")),
            ai_prompt: (if .body | contains("🤖 Prompt for AI Agents")
                       then (.body | split("🤖 Prompt for AI Agents")[1] | split("```")[1] // null)
                       else null end),
            body: .body
        }]'
fi
