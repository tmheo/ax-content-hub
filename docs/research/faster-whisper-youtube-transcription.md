# Faster-Whisper를 활용한 YouTube 비디오 트랜스크립션 연구

## 개요

이 문서는 Cloud Run 환경에서 faster-whisper를 사용하여 YouTube 비디오를 트랜스크립션하기 위한 최적의 방법을 연구한 결과입니다.

**연구 일자**: 2025-12-30

**핵심 결론**:
- **권장 모델**: `small` 모델 + `int8` 양자화 (2GB 메모리 제약)
- **권장 오디오 포맷**: M4A (YouTube 네이티브) 또는 WAV
- **예상 처리 시간**: 30분 비디오 → CPU에서 15-30분, GPU(L4)에서 2-3분

---

## 1. 모델 선택 (Cloud Run 환경)

### 1.1 모델 크기별 사양

| 모델 | 파라미터 | VRAM/RAM | 상대 속도 | 영어 전용 | 다국어 |
|------|----------|----------|-----------|-----------|--------|
| tiny | 39M | ~1 GB | ~10x | tiny.en | tiny |
| base | 74M | ~1 GB | ~7x | base.en | base |
| **small** | 244M | ~2 GB | ~4x | small.en | small |
| medium | 769M | ~5 GB | ~2x | medium.en | medium |
| large | 1550M | ~10 GB | 1x | N/A | large |
| turbo | 809M | ~6 GB | ~8x | N/A | turbo |

> 출처: [OpenAI Whisper GitHub](https://github.com/openai/whisper)

### 1.2 faster-whisper 양자화별 메모리 사용량

| 모델 | Precision | GPU VRAM | CPU RAM | 참고 |
|------|-----------|----------|---------|------|
| large-v3 | fp16 | 4521MB | 901MB | GPU 기본 |
| large-v3 | int8 | 2953MB | 2261MB | 40% 메모리 절약 |
| distil-large-v3 | fp16 | 2409MB | 900MB | 경량화 버전 |
| distil-large-v3 | int8 | 1481MB | 1468MB | 가장 효율적 |

> 출처: [faster-whisper GitHub Benchmark](https://github.com/SYSTRAN/faster-whisper/issues/1030)

### 1.3 2GB 메모리 제약 환경 권장 구성

**CPU 전용 (Cloud Run 기본)**:
```python
from faster_whisper import WhisperModel

# 2GB 메모리 제약 → small 모델 + int8 양자화
model = WhisperModel(
    "small",           # 또는 "base" (더 빠르지만 정확도 낮음)
    device="cpu",
    compute_type="int8",  # CPU에서 최적 성능
    cpu_threads=4,        # Cloud Run vCPU 수에 맞게 조정
)
```

**GPU 사용 가능 시 (Cloud Run GPU - L4)**:
```python
model = WhisperModel(
    "large-v3",         # GPU에서는 large 모델 사용 가능
    device="cuda",
    compute_type="float16",  # GPU에서 최적
)
```

### 1.4 정확도 vs 속도 트레이드오프

| 우선순위 | 권장 모델 | 특징 |
|----------|-----------|------|
| 속도 우선 | tiny, base | 실시간 처리 가능, WER 높음 |
| 균형 | **small** | 가장 가성비 좋음 |
| 정확도 우선 | medium, large | 느리지만 정확 |

**한국어 특별 고려사항**:
- Whisper 학습 데이터 중 한국어 비중이 매우 낮음 (비영어 17% 중 98개 언어)
- large-v3 기준: 영어 CER 3.91% vs 한국어 CER 11.13%
- 한국어 정확도가 중요하면 `medium` 이상 권장

> 출처: [Small Models, Big Heat — Conquering Korean ASR](https://enerzai.com/resources/blog/small-models-big-heat-conquering-korean-asr-with-low-bit-whisper)

---

## 2. yt-dlp를 활용한 오디오 추출

### 2.1 권장 오디오 포맷

| 포맷 | 장점 | 단점 | Whisper 호환성 |
|------|------|------|---------------|
| **M4A** | YouTube 네이티브, 변환 불필요 | AAC 코덱 | 직접 지원 |
| **WAV** | 무손실, 가장 정확 | 파일 크기 큼 | 직접 지원 |
| MP3 | 범용성, 작은 크기 | 손실 압축 | 직접 지원 |
| Opus | YouTube 기본 | 일부 도구 미지원 | 직접 지원 |

**권장**: M4A (변환 없이 바로 사용) 또는 WAV (정확도 최우선)

### 2.2 yt-dlp 설정 코드

```python
import yt_dlp
import tempfile
import os

def extract_audio_from_youtube(video_url: str, output_format: str = "m4a") -> str:
    """YouTube 비디오에서 오디오를 추출합니다.

    Args:
        video_url: YouTube 비디오 URL
        output_format: 출력 포맷 ("m4a", "wav", "mp3")

    Returns:
        추출된 오디오 파일 경로
    """
    # 임시 파일 생성 (수동 삭제 필요)
    temp_dir = tempfile.mkdtemp()
    output_template = os.path.join(temp_dir, "audio.%(ext)s")

    ydl_opts = {
        # 오디오 포맷 설정
        "format": "bestaudio/best",
        "outtmpl": output_template,

        # 오디오 추출 후처리
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": output_format,
            "preferredquality": "192",  # 비트레이트 (kbps)
        }],

        # 에러 핸들링
        "ignoreerrors": False,
        "no_warnings": False,

        # 재시도 설정
        "retries": 3,
        "fragment_retries": 3,

        # 타임아웃
        "socket_timeout": 30,

        # User-Agent (차단 방지)
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # 출력 파일 찾기
        output_file = os.path.join(temp_dir, f"audio.{output_format}")
        if os.path.exists(output_file):
            return output_file
        raise FileNotFoundError(f"Audio file not found: {output_file}")

    except Exception as e:
        # 임시 디렉토리 정리
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
```

### 2.3 에러 핸들링

```python
from yt_dlp.utils import DownloadError, ExtractorError

class YouTubeExtractionError(Exception):
    """YouTube 오디오 추출 실패"""
    pass

class AgeRestrictedError(YouTubeExtractionError):
    """연령 제한 비디오"""
    pass

class VideoUnavailableError(YouTubeExtractionError):
    """비디오 접근 불가 (삭제, 비공개 등)"""
    pass

def extract_audio_with_error_handling(video_url: str) -> str:
    """에러 핸들링이 포함된 오디오 추출"""
    try:
        return extract_audio_from_youtube(video_url)

    except DownloadError as e:
        error_msg = str(e).lower()

        if "sign in to confirm your age" in error_msg:
            raise AgeRestrictedError(
                f"연령 제한 비디오입니다: {video_url}"
            ) from e

        if "video unavailable" in error_msg or "private video" in error_msg:
            raise VideoUnavailableError(
                f"비디오에 접근할 수 없습니다: {video_url}"
            ) from e

        if "copyright" in error_msg:
            raise VideoUnavailableError(
                f"저작권으로 차단된 비디오입니다: {video_url}"
            ) from e

        raise YouTubeExtractionError(f"다운로드 실패: {e}") from e

    except ExtractorError as e:
        raise YouTubeExtractionError(f"메타데이터 추출 실패: {e}") from e
```

### 2.4 연령 제한 비디오 처리 (제한적)

> **주의**: 연령 제한 비디오 자동 우회는 YouTube ToS 위반 가능성이 있습니다.

```python
# 쿠키 기반 접근 (로그인된 브라우저 필요)
ydl_opts = {
    # ... 기본 설정 ...
    "cookiesfrombrowser": ("firefox",),  # 또는 "chrome"
    # 또는 쿠키 파일 직접 지정
    # "cookiefile": "/path/to/cookies.txt",
}
```

> 출처: [yt-dlp Age Restriction Issue](https://github.com/yt-dlp/yt-dlp/issues/11296)

---

## 3. 성능 최적화

### 3.1 compute_type 옵션

| compute_type | 대상 | 메모리 | 속도 | 정확도 |
|--------------|------|--------|------|--------|
| float32 | CPU | 높음 | 기준 | 최고 |
| float16 | GPU | 중간 | 빠름 | 최고 |
| **int8** | CPU | **낮음** | **빠름** | 약간 저하 |
| int8_float16 | GPU | 낮음 | 빠름 | 약간 저하 |

**권장**:
- CPU: `int8` (최적 성능)
- GPU: `float16` (품질) 또는 `int8_float16` (메모리 절약)

```python
import torch

# 자동 선택 패턴
device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "float16" if device == "cuda" else "int8"

model = WhisperModel("small", device=device, compute_type=compute_type)
```

> 출처: [faster-whisper compute_type Discussion](https://github.com/SYSTRAN/faster-whisper/discussions/173)

### 3.2 VAD (Voice Activity Detection) 활용

VAD를 사용하면 무음 구간을 건너뛰어 처리 속도가 크게 향상됩니다.

```python
from faster_whisper import WhisperModel

model = WhisperModel("small", device="cpu", compute_type="int8")

segments, info = model.transcribe(
    "audio.m4a",
    beam_size=5,

    # VAD 필터 활성화 (Silero VAD 사용)
    vad_filter=True,
    vad_parameters={
        "min_silence_duration_ms": 500,   # 최소 무음 길이 (기본 2000ms)
        "speech_pad_ms": 200,              # 음성 전후 패딩
        "threshold": 0.5,                  # 음성 감지 임계값
    },
)
```

**VAD 장점**:
- 무음 구간 스킵으로 2-4배 속도 향상
- 환각(hallucination) 현상 감소
- 30초 청크 최적화로 긴 오디오 안정적 처리

> 출처: [What is VAD and Diarization With Whisper Models](https://www.f22labs.com/blogs/what-is-vad-and-diarization-with-whisper-models-a-complete-guide/)

### 3.3 배치 처리 (Batched Inference)

GPU 환경에서 배치 처리로 추가 2-4배 속도 향상:

```python
from faster_whisper import WhisperModel, BatchedInferencePipeline

# 기본 모델 로드
model = WhisperModel("large-v3", device="cuda", compute_type="float16")

# 배치 파이프라인 생성
batched_model = BatchedInferencePipeline(model=model)

# 배치 크기로 트랜스크립션
segments, info = batched_model.transcribe(
    "audio.m4a",
    batch_size=16,  # GPU VRAM에 따라 조정
)
```

> 출처: [faster-whisper GitHub](https://github.com/SYSTRAN/faster-whisper)

### 3.4 예상 처리 시간 (30분 비디오)

| 환경 | 모델 | compute_type | 예상 시간 |
|------|------|--------------|-----------|
| CPU (4 vCPU) | tiny | int8 | 5-10분 |
| CPU (4 vCPU) | **small** | int8 | 15-30분 |
| CPU (4 vCPU) | medium | int8 | 30-60분 |
| GPU (L4) | large-v3 | float16 | 2-3분 |
| GPU (L4) + 배치 | large-v3 | float16 | 1-2분 |

> **참고**: 실제 시간은 오디오 특성(음성 밀도, 언어 복잡도)에 따라 달라짐

---

## 4. 메모리 관리

### 4.1 알려진 메모리 이슈

faster-whisper에는 긴 오디오 처리 시 메모리 누수 문제가 보고되었습니다:

- 5.5시간 오디오 처리 시 메모리가 점진적으로 증가하여 OOM 발생
- Flask 앱에서 연속 처리 시 메모리 미해제

> 출처: [faster-whisper Memory Leak Issue](https://github.com/guillaumekln/faster-whisper/issues/390)

### 4.2 메모리 관리 패턴

```python
import gc
import tempfile
import shutil
from contextlib import contextmanager
from faster_whisper import WhisperModel

# 싱글톤 모델 로더 (Cold Start 최적화)
_model: WhisperModel | None = None

def get_model() -> WhisperModel:
    """모델 싱글톤 반환 (지연 로딩)"""
    global _model
    if _model is None:
        _model = WhisperModel(
            "small",
            device="cpu",
            compute_type="int8",
            download_root="/tmp/whisper_models",  # 캐시 경로
        )
    return _model

@contextmanager
def managed_transcription(audio_path: str):
    """메모리 관리가 포함된 트랜스크립션 컨텍스트"""
    try:
        model = get_model()
        segments, info = model.transcribe(
            audio_path,
            vad_filter=True,
            beam_size=5,
        )
        # 제너레이터를 리스트로 소비 (메모리 해제 촉진)
        yield list(segments), info
    finally:
        # 명시적 가비지 컬렉션
        gc.collect()

def cleanup_temp_files(temp_dir: str) -> None:
    """임시 파일 정리"""
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass  # 로깅만 하고 무시
```

### 4.3 긴 오디오 청킹 처리

2시간 이상의 긴 오디오는 청크로 나누어 처리:

```python
from pydub import AudioSegment
import os

def chunk_audio(
    audio_path: str,
    chunk_duration_ms: int = 30 * 60 * 1000,  # 30분
) -> list[str]:
    """긴 오디오를 청크로 분할"""
    audio = AudioSegment.from_file(audio_path)
    chunks = []

    for i, start in enumerate(range(0, len(audio), chunk_duration_ms)):
        chunk = audio[start:start + chunk_duration_ms]
        chunk_path = f"/tmp/chunk_{i}.wav"
        chunk.export(chunk_path, format="wav")
        chunks.append(chunk_path)

    return chunks

def transcribe_long_audio(audio_path: str) -> str:
    """긴 오디오 청크별 트랜스크립션"""
    audio = AudioSegment.from_file(audio_path)
    duration_hours = len(audio) / (1000 * 60 * 60)

    if duration_hours <= 1:
        # 1시간 이하는 직접 처리
        with managed_transcription(audio_path) as (segments, _):
            return " ".join(seg.text for seg in segments)

    # 긴 오디오는 청크 처리
    chunks = chunk_audio(audio_path)
    transcripts = []

    try:
        for chunk_path in chunks:
            with managed_transcription(chunk_path) as (segments, _):
                transcripts.append(" ".join(seg.text for seg in segments))
            os.remove(chunk_path)  # 즉시 정리
            gc.collect()
    finally:
        # 남은 청크 파일 정리
        for chunk_path in chunks:
            if os.path.exists(chunk_path):
                os.remove(chunk_path)

    return " ".join(transcripts)
```

---

## 5. 언어 감지 및 다국어 지원

### 5.1 자동 언어 감지

```python
from faster_whisper import WhisperModel

model = WhisperModel("small", device="cpu", compute_type="int8")

segments, info = model.transcribe("audio.m4a")

# 언어 감지 결과
print(f"감지된 언어: {info.language}")          # 예: "ko"
print(f"언어 확률: {info.language_probability:.2%}")  # 예: "95.32%"
```

**주의사항**:
- 처음 30초만 사용하여 언어 감지
- 다국어 혼합 오디오는 정확도 저하
- 한국어/영어 혼합 → 명시적 언어 지정 권장

> 출처: [Whisper Language Detection Issues](https://github.com/SYSTRAN/faster-whisper/issues/918)

### 5.2 명시적 언어 지정

```python
# 한국어 콘텐츠
segments, info = model.transcribe(
    "audio.m4a",
    language="ko",  # 명시적 지정
    task="transcribe",  # 또는 "translate" (영어로 번역)
)

# 영어 콘텐츠
segments, info = model.transcribe(
    "audio.m4a",
    language="en",
)
```

### 5.3 다국어 콘텐츠 처리 전략

```python
def transcribe_multilingual(audio_path: str) -> dict:
    """다국어 콘텐츠 처리 (언어 감지 후 재처리)"""
    model = get_model()

    # 1단계: 언어 감지
    _, info = model.transcribe(audio_path, beam_size=1)
    detected_lang = info.language
    confidence = info.language_probability

    # 2단계: 낮은 신뢰도면 기본 언어 사용
    target_lang = detected_lang if confidence > 0.8 else "ko"

    # 3단계: 명시적 언어로 재트랜스크립션
    segments, _ = model.transcribe(
        audio_path,
        language=target_lang,
        condition_on_previous_text=True,  # 문맥 유지
    )

    return {
        "language": target_lang,
        "confidence": confidence,
        "text": " ".join(seg.text for seg in segments),
    }
```

---

## 6. Cloud Run 배포 고려사항

### 6.1 Cloud Run 제약 조건

| 항목 | 기본값 | 최대값 | 권장값 |
|------|--------|--------|--------|
| 메모리 | 512MB | 32GB | 2-4GB (CPU), 16GB (GPU) |
| vCPU | 1 | 8 | 4 (CPU 추론) |
| 타임아웃 | 5분 | 60분 | 30분 |
| 요청 크기 | 32MB | 32MB | - |
| GPU | 없음 | L4 1개 | L4 (가능시) |

### 6.2 GPU vs CPU 결정

**CPU 선택 시** (기본):
- 비용 효율적
- 콜드 스타트 빠름 (~5초)
- small 모델 + int8로 충분한 품질
- 30분 비디오 처리 시 15-30분 소요

**GPU 선택 시** (Cloud Run GPU):
- L4 GPU 최소 요구사항: 4 vCPU, 16GB 메모리
- 콜드 스타트 ~5초 (드라이버 사전 설치)
- large-v3 모델로 최고 품질
- 30분 비디오 처리 시 2-3분 소요
- 인스턴스 기반 과금 (유휴 시에도 요금)

> 출처: [Cloud Run GPU Documentation](https://docs.cloud.google.com/run/docs/configuring/services/gpu)

### 6.3 콜드 스타트 최적화

```python
# 1. 모델 사전 다운로드 (Docker 빌드 시)
# Dockerfile
"""
FROM python:3.12-slim

# 모델 사전 다운로드
RUN python -c "from faster_whisper import WhisperModel; \
    WhisperModel('small', device='cpu', compute_type='int8', \
    download_root='/app/models')"

COPY . /app
WORKDIR /app
"""

# 2. 앱 시작 시 모델 로드 (lifespan)
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 모델 로드 (콜드 스타트 시간에 포함)
    _ = get_model()
    yield
    # 종료 시 정리 (필요시)

app = FastAPI(lifespan=lifespan)
```

### 6.4 타임아웃 처리

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=2)

async def transcribe_with_timeout(
    audio_path: str,
    timeout_seconds: int = 1800,  # 30분
) -> str:
    """타임아웃이 있는 트랜스크립션"""
    loop = asyncio.get_event_loop()

    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(
                executor,
                lambda: transcribe_long_audio(audio_path),
            ),
            timeout=timeout_seconds,
        )
        return result
    except asyncio.TimeoutError:
        raise TimeoutError(
            f"트랜스크립션 타임아웃 ({timeout_seconds}초 초과)"
        )
```

### 6.5 Cloud Run 설정 예시

```yaml
# service.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: whisper-transcriber
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "0"
        autoscaling.knative.dev/maxScale: "5"
        run.googleapis.com/cpu-throttling: "false"  # CPU 항상 할당
    spec:
      containerConcurrency: 1  # 동시 요청 1개 (무거운 작업)
      timeoutSeconds: 1800     # 30분 타임아웃
      containers:
        - image: gcr.io/PROJECT/whisper-transcriber
          resources:
            limits:
              memory: "4Gi"
              cpu: "4"
```

---

## 7. 전체 구현 예시

```python
"""YouTube 비디오 트랜스크립션 서비스"""
import gc
import os
import shutil
import tempfile
from dataclasses import dataclass

import yt_dlp
from faster_whisper import WhisperModel

@dataclass
class TranscriptionResult:
    """트랜스크립션 결과"""
    text: str
    language: str
    language_probability: float
    duration_seconds: float

class YouTubeTranscriber:
    """YouTube 비디오 트랜스크립터"""

    def __init__(
        self,
        model_size: str = "small",
        compute_type: str = "int8",
        device: str = "cpu",
    ):
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            download_root="/tmp/whisper_models",
        )

    def transcribe(
        self,
        video_url: str,
        language: str | None = None,
    ) -> TranscriptionResult:
        """YouTube 비디오 트랜스크립션

        Args:
            video_url: YouTube 비디오 URL
            language: 언어 코드 (None이면 자동 감지)

        Returns:
            트랜스크립션 결과
        """
        temp_dir = tempfile.mkdtemp()

        try:
            # 1. 오디오 추출
            audio_path = self._extract_audio(video_url, temp_dir)

            # 2. 트랜스크립션
            segments, info = self.model.transcribe(
                audio_path,
                language=language,
                beam_size=5,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
            )

            # 3. 결과 수집
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            return TranscriptionResult(
                text=" ".join(text_parts),
                language=info.language,
                language_probability=info.language_probability,
                duration_seconds=info.duration,
            )

        finally:
            # 4. 정리
            shutil.rmtree(temp_dir, ignore_errors=True)
            gc.collect()

    def _extract_audio(self, video_url: str, output_dir: str) -> str:
        """YouTube에서 오디오 추출"""
        output_template = os.path.join(output_dir, "audio.%(ext)s")

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": output_template,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "192",
            }],
            "quiet": True,
            "no_warnings": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        return os.path.join(output_dir, "audio.m4a")


# 사용 예시
if __name__ == "__main__":
    transcriber = YouTubeTranscriber(
        model_size="small",
        compute_type="int8",
    )

    result = transcriber.transcribe(
        "https://www.youtube.com/watch?v=example",
        language="ko",  # 한국어 명시
    )

    print(f"언어: {result.language} ({result.language_probability:.1%})")
    print(f"길이: {result.duration_seconds / 60:.1f}분")
    print(f"텍스트: {result.text[:500]}...")
```

---

## 8. 참고 자료

### 공식 문서
- [faster-whisper GitHub](https://github.com/SYSTRAN/faster-whisper)
- [OpenAI Whisper GitHub](https://github.com/openai/whisper)
- [yt-dlp Documentation](https://github.com/yt-dlp/yt-dlp)
- [Cloud Run GPU Documentation](https://docs.cloud.google.com/run/docs/configuring/services/gpu)

### 벤치마크 및 비교
- [Choosing between Whisper variants (Modal)](https://modal.com/blog/choosing-whisper-variants)
- [faster-whisper Turbo v3 Benchmark](https://github.com/SYSTRAN/faster-whisper/issues/1030)
- [Whisper Model Memory Requirements](https://huggingface.co/openai/whisper-large-v3/discussions/83)

### 한국어 최적화
- [Small Models, Big Heat — Conquering Korean ASR](https://enerzai.com/resources/blog/small-models-big-heat-conquering-korean-asr-with-low-bit-whisper)
- [Fine-tuning Whisper for Korean](https://www.eksss.org/archive/view_article?pid=pss-15-3-75)

### 배포 가이드
- [Deploying Faster-Whisper on CPU](https://codesphere.com/articles/deploying-faster-whisper-on-cpu)
- [Deploy Whisper on GCP](https://github.com/fentresspaul61B/Deploy-Whisper-On-GCP)
- [Cloud Run with NVIDIA L4 GPUs](https://developer.nvidia.com/blog/google-cloud-run-adds-support-for-nvidia-l4-gpus-nvidia-nim-and-serverless-ai-inference-deployments-at-scale/)
