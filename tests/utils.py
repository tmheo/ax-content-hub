"""Test utilities shared across test modules."""

import os
import socket


def is_emulator_available() -> bool:
    """Firestore 에뮬레이터 사용 가능 여부 확인.

    환경변수 FIRESTORE_EMULATOR_HOST에서 호스트/포트를 읽어
    연결 가능 여부를 확인합니다.

    Returns:
        에뮬레이터 연결 가능 여부.
    """
    host = os.environ.get("FIRESTORE_EMULATOR_HOST", "localhost:8086")
    host_parts = host.split(":")
    hostname = host_parts[0]
    port = int(host_parts[1]) if len(host_parts) > 1 else 8086

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((hostname, port))
            return result == 0
    except Exception:
        return False
