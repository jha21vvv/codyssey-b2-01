"""
decorators.py
애플리케이션 전반에서 재사용되는 공통 관심사(예외 처리, 로깅, 실행 시간 측정)를
비즈니스 로직과 분리하여 캡슐화하는 데코레이터 모듈입니다.
"""

import functools
import os
import sys
import time
from typing import Any, Callable, TypeVar

# 제네릭 함수 반환 타입 힌트 정의
F = TypeVar("F", bound=Callable[..., Any])


def handle_cli_errors(func: F) -> F:
    """
    [요건 충족 1 & 2 & 3] CLI 엔드포인트 전용 예외 처리 데코레이터.
    
    1. 예외 처리 관심사 분리: 핵심 비즈니스 로직과 화면 출력/종료 로직을 분리합니다.
    2. 스택트레이스(Traceback) 차단: 콘솔에 복잡한 파이썬 호출 스택 대신
       '원인 + 해결 힌트'를 명확한 포맷으로 출력합니다.
    3. 종료 코드 제어: 정상 실행 완료 시에는 0으로 종료되도록 허용하고,
       예외 발생 시에는 프로세스 종료 코드 sys.exit(1)로 비정상 종료 처리합니다.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except ValueError as ve:
            # 입력 데이터 유효성 검증 실패 (날짜 형식, 양수 금액, 잘못된 타입 등)
            print(f"\n[오류 원인] 잘못된 값 또는 형식이 전달되었습니다: {ve}", file=sys.stderr)
            print("[해결 힌트] 날짜(YYYY-MM-DD), 양수 금액, 허용된 카테고리인지 다시 확인하세요.", file=sys.stderr)
            sys.exit(1)
        except KeyError as ke:
            # 필수 데이터 누락 또는 스키마 키 불일치
            print(f"\n[오류 원인] 필수 데이터 항목이 누락되었습니다: {ke}", file=sys.stderr)
            print("[해결 힌트] 입력 데이터의 형식과 필수 필드 존재 여부를 확인하세요.", file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError as fe:
            # 데이터 디렉터리 부재 또는 잘못된 파일 경로 지정
            print(f"\n[오류 원인] 요청한 파일 또는 경로를 찾을 수 없습니다: {fe.filename}", file=sys.stderr)
            print("[해결 힌트] 파일 경로가 올바른지, --data-dir 옵션 값에 오타가 없는지 확인하세요.", file=sys.stderr)
            sys.exit(1)
        except PermissionError as pe:
            # 파일 읽기/쓰기 권한 부재
            print(f"\n[오류 원인] 파일에 접근할 수 있는 시스템 권한이 없습니다: {pe.filename}", file=sys.stderr)
            print("[해결 힌트] 대상 디렉터리나 파일의 읽기/쓰기 권한을 확인하세요.", file=sys.stderr)
            sys.exit(1)
        except KeyboardInterrupt:
            # 사용자가 대화형 입력 도중 Ctrl+C를 눌러 작업을 중단한 경우
            print("\n\n[작업 취소] 사용자에 의해 작업이 취소되었습니다.", file=sys.stderr)
            print("[해결 힌트] 안전하게 종료되었습니다. 필요할 때 다시 명령을 실행하세요.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            # 기타 예상치 못한 런타임 오류
            print(f"\n[시스템 오류] 예기치 않은 오류가 발생했습니다: {e}", file=sys.stderr)
            print("[해결 힌트] 인자 표기(--) 및 명령어 형식이 명세와 일치하는지 점검하세요.", file=sys.stderr)
            sys.exit(1)

    return wrapper  # type: ignore[return-value]


def measure_time(func: F) -> F:
    """
    [부가 공통 관심사] 함수의 실행 시간을 정밀 측정하는 데코레이터.
    
    - 대량 데이터 조회, 스트리밍 집계(summary), CSV export/import 등 
      성능 병목이 발생할 수 있는 구간에 부착하여 경과 시간을 확인합니다.
    - 환경 변수(BUDGET_DEBUG=1)가 설정된 경우에만 콘솔에 로그를 출력하도록 설계하여
      일반 CLI 실행 화면의 가독성을 해치지 않습니다.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed_time = time.perf_counter() - start_time
            if os.getenv("BUDGET_DEBUG") == "1":
                print(f"[DEBUG LOG] {func.__name__} 실행 소요 시간: {elapsed_time:.6f}초", file=sys.stderr)

    return wrapper  # type: ignore[return-value]


def log_operation(action_name: str) -> Callable[[F], F]:
    """
    [부가 공통 관심사] 특정 작업 수행 여부를 로깅하는 파라미터형 데코레이터.
    
    - 어떤 핵심 기능이 호출되었는지 감사(Audit) 로그 목적으로 사용됩니다.
    - BUDGET_DEBUG=1 모드에서만 동작합니다.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if os.getenv("BUDGET_DEBUG") == "1":
                print(f"[DEBUG LOG] 작업 시작: '{action_name}' (함수: {func.__name__})", file=sys.stderr)
            result = func(*args, **kwargs)
            if os.getenv("BUDGET_DEBUG") == "1":
                print(f"[DEBUG LOG] 작업 완료: '{action_name}'", file=sys.stderr)
            return result
        return wrapper  # type: ignore[return-value]
    return decorator

# 요건 충족 및 설계 세부 사항
# 스택트레이스 완전 차단: try-except 블록을 구성해 내부에서 터지는 예외의 Python Traceback 노출을 완전히 막고, 표준 에러 스트림(sys.stderr)으로 직관적인 [오류 원인] 및 [해결 힌트]만 안내합니다[cite: 1].
# 프로세스 종료 코드(exit code) 준수: 모든 예외 처리 분기 마지막에 sys.exit(1)을 명시하여 0이 아닌 비정상 종료 코드를 시스템에 반환하도록 보장했습니다[cite: 1].
# 관심사의 완벽한 분리: 비즈니스 로직과 CLI 핸들러 상단에 @handle_cli_errors 또는 @measure_time 어노테이션만 붙이면 동작하도록 하여 핵심 코드의 복잡도를 낮췄습니다[cite: 1]