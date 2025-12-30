# Implementation Plan: Phase 2 콘텐츠 수집 확장

**Branch**: `003-phase2-collection-expansion` | **Date**: 2025-12-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-phase2-collection-expansion/spec.md`

## Summary

RSS가 없는 웹사이트와 자막이 없는 YouTube 영상에서도 콘텐츠를 수집할 수 있도록 확장하고, 중복/최신성/품질 기반 필터링을 강화하여 다이제스트 품질을 개선합니다.

**핵심 접근법**:
- 웹 스크래핑: Playwright 기반 4단계 폴백 전략 (Static → Dynamic → Structural → URL-based)
- YouTube STT: yt-dlp + faster-whisper 기반 음성 인식 폴백
- 품질 필터링: Jaccard 유사도 기반 중복 제거, 최신성/품질 필터 추가

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**:
- FastAPI (웹 프레임워크)
- Playwright (웹 스크래핑 - 이미 설치됨)
- BeautifulSoup4 + lxml (HTML 파싱 - 신규 추가 필요)
- yt-dlp (YouTube 오디오 추출 - 신규 추가 필요)
- faster-whisper (음성 인식 - 신규 추가 필요)
- Pydantic 2.0+ (데이터 모델링)

**Storage**: Google Firestore (기존)
**Testing**: pytest + pytest-asyncio (기존)
**Target Platform**: Google Cloud Run (Linux, 2GB+ 메모리 필요)
**Project Type**: Single (백엔드 API 서버)
**Performance Goals**:
- 웹 스크래핑: 단일 페이지 60초 이내
- YouTube STT: 30분 영상 10분 이내 처리
**Constraints**:
- Cloud Run 환경 (stateless, 최대 60분 요청)
- 메모리 제한 (STT용 최소 2GB 필요)
- 봇 차단/Rate limiting 대응 필요

**Scale/Scope**:
- 예상 소스: 수십 개 (RSS + YouTube + WEB)
- 일일 콘텐츠: 수백 개

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Test-First | ✅ PASS | 모든 도구/서비스에 대해 단위/통합 테스트 작성 예정 |
| II. API-First Design | ✅ PASS | 신규 API 없음 (내부 도구 확장), Pydantic 모델 우선 정의 |
| III. Korean-First Communication | ✅ PASS | 기존 한국어 요약 파이프라인 유지 |
| IV. Quality Gates | ✅ PASS | Ruff + MyPy + pytest 통과 필수 (기존 CI/CD) |
| V. Simplicity | ✅ PASS | 기존 패턴 재사용, 최소 추상화 (4단계 폴백은 도메인 요구사항) |

**Gate Result**: ✅ PASS - 모든 원칙 준수, Phase 0 진행 가능

## Project Structure

### Documentation (this feature)

```text
specs/003-phase2-collection-expansion/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (OpenAPI schemas if applicable)
└── tasks.md             # Phase 2 output (from /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── models/
│   └── source.py              # WEB 타입 추가
├── services/
│   └── quality_filter.py      # 중복/최신성/품질 필터 확장
├── agent/
│   └── domains/
│       └── collector/
│           └── tools/
│               ├── web_scraper_tool.py    # 신규: 4단계 폴백 스크래핑
│               ├── youtube_stt.py          # 신규: STT 폴백
│               └── youtube_tool.py         # STT 통합
├── config/
│   └── settings.py            # STT 설정 추가

tests/
├── unit/
│   ├── models/
│   │   └── test_source.py     # WEB 타입 테스트
│   ├── services/
│   │   └── test_quality_filter.py  # 확장 필터 테스트
│   └── agent/
│       └── domains/
│           └── collector/
│               ├── test_web_scraper_tool.py  # 신규
│               └── test_youtube_stt.py        # 신규
└── integration/
    └── test_web_scraping_flow.py  # 신규
```

**Structure Decision**: 기존 단일 프로젝트 구조 유지. 신규 도구는 `src/agent/domains/collector/tools/`에 추가하여 기존 ADK 에이전트 아키텍처와 일관성 유지.

## Complexity Tracking

> **현재 위반 없음** - 기존 패턴 재사용으로 복잡도 최소화

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 4단계 폴백 전략 | 다양한 웹사이트 구조 지원을 위한 도메인 요구사항 | 단일 전략으로는 80% 성공률 달성 불가 |
| faster-whisper 의존성 | 자막 없는 영상 지원을 위한 핵심 기능 | Google STT API는 비용 문제, Whisper API는 속도 문제 |

---

## Constitution Check (Post-Design)

*Re-evaluation after Phase 1 design completion.*

| Principle | Status | Post-Design Notes |
|-----------|--------|-------------------|
| I. Test-First | ✅ PASS | data-model.md에 Pydantic 모델 정의 완료, 테스트 케이스 spec에서 도출 가능 |
| II. API-First Design | ✅ PASS | contracts/tool-interfaces.md에 내부 도구 인터페이스 정의 완료 |
| III. Korean-First Communication | ✅ PASS | 영향 없음 - 기존 한국어 요약 파이프라인 유지 |
| IV. Quality Gates | ✅ PASS | 기존 CI/CD 파이프라인 적용, 신규 의존성 mypy 호환 확인 필요 |
| V. Simplicity | ✅ PASS | 기존 패턴(Tool, Service, Repository) 재사용, 추상화 최소화 |

**Post-Design Gate Result**: ✅ PASS - 설계 완료, `/speckit.tasks`로 태스크 생성 가능

---

## Generated Artifacts

| 파일 | 상태 | 설명 |
|------|------|------|
| `plan.md` | ✅ | 구현 계획 (본 문서) |
| `research.md` | ✅ | 기술 리서치 결과 |
| `data-model.md` | ✅ | 데이터 모델 정의 |
| `contracts/tool-interfaces.md` | ✅ | 내부 도구 인터페이스 |
| `quickstart.md` | ✅ | 빠른 시작 가이드 |
| `tasks.md` | ⏳ | `/speckit.tasks`로 생성 예정 |

---

## Next Steps

1. `/speckit.tasks` 실행하여 tasks.md 생성
2. 태스크 리뷰 및 승인
3. `/speckit.implement` 또는 수동 구현 시작
