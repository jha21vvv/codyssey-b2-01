"""
__main__.py
'python -m budget_app' 명령 실행 시 호출되는 최상위 진입점(Entry Point)입니다.

초보자를 위한 해설:
- 파이썬에서 -m 옵션은 '모듈이나 패키지를 스크립트로 실행하라'는 뜻입니다.
- 패키지 폴더 안에 __main__.py가 있으면, 파이썬 인터프리터가 이 파일을 자동으로 찾아 실행합니다.
- 복잡한 로직을 여기에 두지 않고, cli.py에 있는 run_cli()만 깔끔하게 호출하는 것이 모듈화의 핵심입니다.
"""

from .cli import run_cli

if __name__ == "__main__":
    # CLI 메인 루프 실행 (decorators.py의 @handle_cli_errors 데코레이터가 예외를 자동 제어함)
    run_cli()