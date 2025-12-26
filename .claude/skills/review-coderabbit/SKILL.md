# CodeRabbit Review Processor

CodeRabbit AI 리뷰 코멘트를 자동으로 처리하는 스킬입니다.

## Description

이 스킬은 GitHub PR에서 CodeRabbit이 남긴 리뷰 코멘트를 가져와서 분석하고, 수정사항을 적용하고, 답글을 달고, 스레드를 리졸브하는 전체 워크플로우를 자동화합니다.

**자동 발견 트리거**:
- "CodeRabbit 리뷰 확인해줘"
- "PR 리뷰 코멘트 처리해줘"
- "코드래빗 피드백 반영해줘"
- "리뷰 코멘트 수정하고 리졸브해줘"

## CodeRabbit 코멘트 구조

CodeRabbit은 두 가지 유형의 코멘트를 남깁니다:

1. **요약 코멘트** (무시):
   - "Actionable comments posted: N"
   - "Nitpick comments (N)" - 접이식 섹션
   - "Review details" - 접이식 섹션

2. **개별 스레드 코멘트** (처리 대상):
   - 특정 코드 라인에 붙는 코멘트
   - 🔴 Critical, 🟠 Major, 🟡 Minor 심각도 표시
   - "제안하는 수정사항" 섹션
   - "🤖 Prompt for AI Agents" 섹션

**이 스킬은 Nitpick을 무시하고 Critical/Major 스레드 코멘트만 처리합니다.**

## Capabilities

1. **리뷰 조회**: Critical/Major 스레드 코멘트만 필터링 (Nitpick 제외)
2. **Suggestion 추출**: Committable suggestion 자동 추출
3. **코드 수정**: AI 분석 기반 수정 또는 suggestion 직접 적용
4. **커밋 & 푸시**: 변경사항 자동 커밋
5. **답글 달기**: "✅ Addressed in commit {sha}" 자동 답글
6. **리졸브**: GraphQL로 스레드 리졸브 처리

## Usage

```
# PR 번호 지정
CodeRabbit 리뷰 확인해줘 PR 23

# 현재 브랜치의 PR 자동 감지
이 PR의 코드래빗 리뷰 처리해줘

# 특정 옵션
PR 23 리뷰 코멘트 dry-run으로 확인만 해줘
```

## Workflow

### 1. 리뷰 코멘트 조회

```bash
# Actionable 코멘트만 (Critical/Major, Nitpick 제외) - 기본값
./scripts/coderabbit-fetch.sh <PR_NUMBER>

# 또는 명시적으로
./scripts/coderabbit-fetch.sh <PR_NUMBER> --actionable

# 전체 코멘트 JSON
./scripts/coderabbit-fetch.sh <PR_NUMBER> --json

# 사람이 읽기 좋은 요약
./scripts/coderabbit-fetch.sh <PR_NUMBER> --summary
```

### 2. 리뷰 스레드 조회 (리졸브 상태 포함)

```bash
./scripts/coderabbit-threads.sh <PR_NUMBER> --unresolved-only
```

### 3. 코멘트 파싱

각 코멘트에서 추출:
- **심각도**: `_🔴 Critical_`, `_🟠 Major_`, `_🟡 Minor_`
- **파일/라인**: 코멘트 메타데이터
- **Committable Suggestion**: ` ```suggestion ` 블록
- **AI Prompt**: `🤖 Prompt for AI Agents` 섹션
- **해결 상태**: `✅ Addressed in commit` 마커

### 4. 수정 적용 (반복)

각 코멘트에 대해:

**Committable Suggestion이 있는 경우**:
- suggestion 코드를 해당 파일/라인에 직접 적용

**AI Prompt만 있는 경우**:
- 파일 읽기 → 이슈 분석 → 수정 제안 → 사용자 확인 후 적용

**⚠️ 중요**: 수정만 하고 아직 커밋/푸시하지 않음!

### 5. 모든 수정 완료 후 한 번에 커밋 & 푸시

```bash
# 모든 수정 완료 후 한 번에 커밋
git add <all_modified_files>
git commit -m "fix: address CodeRabbit review comments for PR #${PR}

- <수정 요약 1>
- <수정 요약 2>
- <수정 요약 3>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

# 한 번만 푸시 (CI 1회 실행)
git push
```

### 6. 답글 & 리졸브 (배치)

푸시 후 커밋 SHA를 얻어서 모든 코멘트에 답글:

```bash
COMMIT_SHA=$(git rev-parse --short HEAD)

# 각 스레드에 답글 달기 (GraphQL - THREAD_ID 사용)
./scripts/coderabbit-reply.sh <THREAD_ID_1> "✅ Addressed in commit ${COMMIT_SHA}"
./scripts/coderabbit-reply.sh <THREAD_ID_2> "✅ Addressed in commit ${COMMIT_SHA}"

# 스레드 리졸브
./scripts/coderabbit-resolve.sh <THREAD_ID_1>
./scripts/coderabbit-resolve.sh <THREAD_ID_2>
```

> **Note**: `THREAD_ID`는 `coderabbit-fetch.sh --json`에서 확인 (예: `PRRT_kwDOQiWGTc5l63qJ`)

## Scripts

이 스킬에 포함된 헬퍼 스크립트 (모두 GraphQL API 사용):

| 스크립트 | 설명 |
|----------|------|
| `scripts/coderabbit-fetch.sh` | PR 리뷰 스레드/코멘트 조회 (`--actionable`, `--json`, `--summary`) |
| `scripts/coderabbit-threads.sh` | 리뷰 스레드 조회 (간단 버전, `--unresolved-only`) |
| `scripts/coderabbit-reply.sh` | 스레드에 답글 달기 (THREAD_ID 사용) |
| `scripts/coderabbit-resolve.sh` | 스레드 리졸브 처리 |

## Output Example

```
CodeRabbit Review Summary for PR #23

| # | Severity | File | Issue | Status |
|---|----------|------|-------|--------|
| 1 | 🔴 Critical | src/models/context.py:109 | MD5 hash 길이 불일치 | ⏳ Open |
| 2 | 🟠 Major | src/services/artifact_store.py:180 | error=str(e) 노출 | ⏳ Open |
| 3 | 🟠 Major | src/services/context_compiler.py:127 | 캐시키/텍스트 분리 | ✅ Resolved |

Committable Suggestions: 3
AI Prompts Available: 5
Already Resolved: 1
```

## Requirements

- `gh` CLI 인증 완료
- GitHub 저장소 접근 권한
- CodeRabbit이 설치된 저장소
