"""
repositories.py
파일 영구 저장(Persistence) 및 라인 단위 스트리밍 처리를 전담하는 저장소 계층 모듈입니다.
"""

import json
import os
import tempfile
from typing import Generator, List, Optional
from .models import Budget, Category, Transaction


class FileRepository:
    """
    JSONL 기반 파일 저장소 클래스입니다.

    충족 요건:
    - 표준 라이브러리만 사용 (os, json, tempfile 등)
    - 3개 분리 파일 영구 저장: transactions.jsonl, categories.jsonl, budgets.jsonl
    - 기본 경로 ./data 설정 및 사용자 지정 디렉터리 경로 주입 허용 (--data-dir 대응)
    - 파일 부재 시 자동 생성 초기화 및 기본 카테고리 자동 시딩(안 A)
    - yield 기반 제너레이터 스트리밍 I/O
    - 원자적 파일 교체(atomic replace)를 통한 안전한 갱신
    """

    def __init__(self, data_dir: str = "./data") -> None:
        self.data_dir = data_dir
        # 저장 폴더가 없으면 자동 생성
        os.makedirs(self.data_dir, exist_ok=True)

        # 3개 파일 경로 분리 설정
        self.tx_file = os.path.join(self.data_dir, "transactions.jsonl")
        self.cat_file = os.path.join(self.data_dir, "categories.jsonl")
        self.budget_file = os.path.join(self.data_dir, "budgets.jsonl")

        # 초기 파일 점검 및 기본 데이터 생성
        self._initialize_storage()

    def _initialize_storage(self) -> None:
        """
        저장소 초기화:
        - transactions, budgets 파일이 없으면 빈 파일 생성
        - categories 파일이 없으면 정책(안 A)에 따라 기본 카테고리 자동 생성
        """
        # 1. 거래 내역 및 예산 파일 초기화 (없는 경우 빈 파일 생성)
        for path in (self.tx_file, self.budget_file):
            if not os.path.exists(path):
                open(path, "a", encoding="utf-8").close()

        # 2. 카테고리 파일 초기화 (안 A: 기본 카테고리 자동 생성)
        if not os.path.exists(self.cat_file) or os.path.getsize(self.cat_file) == 0:
            default_categories = ["식비", "교통", "주거", "쇼핑", "급여", "기타"]
            self.save_categories(default_categories)

    # -------------------------------------------------------------------------
    # 1. Transactions (거래 내역) 스트리밍 및 쓰기
    # -------------------------------------------------------------------------

    def stream_transactions(self) -> Generator[Transaction, None, None]:
        """
        [스트리밍 요건 충족]
        파일 전체를 메모리에 한 번에 올리지 않고 한 줄씩 읽어 Transaction 객체로 반환합니다.
        대용량 파일에서도 메모리 사용량을 최소화합니다.
        """
        if not os.path.exists(self.tx_file):
            return

        with open(self.tx_file, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                data = json.loads(line_str)
                yield Transaction.from_dict(data)

    def append_transaction(self, tx: Transaction) -> None:
        """단일 거래 내역을 파일 끝에 추가(append)합니다."""
        with open(self.tx_file, "a", encoding="utf-8") as f:
            json_line = json.dumps(tx.to_dict(), ensure_ascii=False)
            f.write(json_line + "\n")

    def overwrite_transactions(self, transactions: List[Transaction]) -> None:
        """
        [원자적 교체(Atomic Write) 요건 충족]
        기존 파일을 직접 덮어쓰지 않고, 동일 디렉터리 내에 임시 파일을 먼저 완전히 기록한 뒤
        os.replace로 원자적으로 교체합니다.
        작성 도중 프로그램이 강제 종료되더라도 기존 데이터가 깨지지 않습니다.
        """
        dir_name = os.path.dirname(self.tx_file)
        # NamedTemporaryFile로 임시 파일 생성
        with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
            temp_path = tf.name
            for tx in transactions:
                line = json.dumps(tx.to_dict(), ensure_ascii=False)
                tf.write(line + "\n")
            tf.flush()
            os.fsync(tf.fileno())  # 디스크에 물리적으로 기록 보장

        # 원자적 파일 교체
        os.replace(temp_path, self.tx_file)

    # -------------------------------------------------------------------------
    # 2. Categories (카테고리 목록) 관리
    # -------------------------------------------------------------------------

    def stream_categories(self) -> Generator[str, None, None]:
        """카테고리 목록을 스트리밍 방식으로 조회합니다."""
        if not os.path.exists(self.cat_file):
            return

        with open(self.cat_file, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                data = json.loads(line_str)
                yield data["name"]

    def load_categories(self) -> List[str]:
        """카테고리 전체 목록을 리스트로 반환합니다."""
        return list(self.stream_categories())

    def save_categories(self, categories: List[str]) -> None:
        """
        카테고리 목록을 원자적으로 갱신합니다.
        중복을 배제하고 저장합니다.
        """
        # 중복 방지 및 순서 유지
        unique_cats = list(dict.fromkeys(categories))
        dir_name = os.path.dirname(self.cat_file)

        with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
            temp_path = tf.name
            for cat in unique_cats:
                line = json.dumps({"name": cat}, ensure_ascii=False)
                tf.write(line + "\n")
            tf.flush()
            os.fsync(tf.fileno())

        os.replace(temp_path, self.cat_file)

    # -------------------------------------------------------------------------
    # 3. Budgets (월별 예산) 관리
    # -------------------------------------------------------------------------

    def stream_budgets(self) -> Generator[Budget, None, None]:
        """월별 예산 데이터를 스트리밍 방식으로 순회합니다."""
        if not os.path.exists(self.budget_file):
            return

        with open(self.budget_file, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                data = json.loads(line_str)
                yield Budget.from_dict(data)

    def get_budget(self, month: str) -> Optional[Budget]:
        """특정 월(YYYY-MM)에 해당하는 예산 정보를 조회합니다."""
        for b in self.stream_budgets():
            if b.month == month:
                return b
        return None

    def set_budget(self, budget: Budget) -> None:
        """
        예산을 설정하거나 갱신(Upsert)하며 원자적으로 저장합니다.
        동일한 월의 기존 예산이 있다면 새로운 금액으로 덮어씁니다.
        """
        budgets_map = {b.month: b.amount for b in self.stream_budgets()}
        budgets_map[budget.month] = budget.amount

        dir_name = os.path.dirname(self.budget_file)
        with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
            temp_path = tf.name
            for m, amt in sorted(budgets_map.items()):
                line = json.dumps({"month": m, "amount": amt}, ensure_ascii=False)
                tf.write(line + "\n")
            tf.flush()
            os.fsync(tf.fileno())

        os.replace(temp_path, self.budget_file)

# 핵심 설계 및 요건 검증
# 표준 라이브러리 준수: json, os, tempfile 등 Python 표준 모듈만을 사용해 외부 종속성 없이 단독 구동됩니다[cite: 1].
# 3개 분리 저장 파일: transactions.jsonl, categories.jsonl, budgets.jsonl로 역할을 분리하여 데이터 간 결합도를 낮추고 독립적인 확장이 가능합니다[cite: 1].
# 안전한 스트리밍 (yield): stream_transactions(), stream_categories(), stream_budgets() 모두 제너레이터 패턴으로 구현되어 파일 크기에 상관없이 O(1)의 일정한 메모리 공간에서 라인을 읽어 들입니다[cite: 1].
# 원자적 쓰기 (Atomic Write): NamedTemporaryFile로 동일한 디렉터리 내에 임시 파일을 작성하고 os.fsync 후 os.replace로 파일 교체를 수행합니다[cite: 1]. 이를 통해 쓰기 작업 도중 OS 비정상 종료나 예기치 않은 인터럽트가 발생해도 기존 파일이 0바이트로 깨지거나 손상되는 현상을 완전히 방지합니다[cite: 1].
# 초기화 정책 준수: 카테고리 파일이 비어있거나 생성되지 않았을 때 (안 A)를 채택하여 기본 카테고리(식비, 교통, 주거 등)를 자동 생성하도록 구성했습니다[cite: 1].