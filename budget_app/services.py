"""
services.py
가계부 비즈니스 로직을 처리하는 서비스 계층입니다.
4단계(추가), 5단계(조회/검색), 6단계(수정/삭제), 7단계(카테고리), 8단계(요약/예산), 9단계(가져오기/내보내기)를 포함합니다.
"""

import csv
import os
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, Tuple

from .models import Budget, Transaction
from .repositories import FileRepository


class BudgetService:
    def __init__(self, repo: FileRepository) -> None:
        self.repo = repo

    # ---------------------------------------------------------
    # 4단계: 거래 추가 (Add)
    # ---------------------------------------------------------
    def create_transaction(
        self,
        date_str: str,
        tx_type: str,
        category: str,
        amount: int,
        memo: str = "",
        tags: Optional[List[str]] = None,
    ) -> str:
        if tags is None:
            tags = []

        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"날짜 형식이 올바르지 않습니다: '{date_str}'. 'YYYY-MM-DD' 형식이어야 합니다.")

        if tx_type not in ("income", "expense"):
            raise ValueError(f"거래 타입이 올바르지 않습니다: '{tx_type}'. 'income' 또는 'expense'여야 합니다.")

        if amount <= 0:
            raise ValueError(f"금액은 0보다 큰 양수 정수여야 합니다: {amount}")

        valid_categories = self.repo.load_categories()
        if category not in valid_categories:
            cats_str = ", ".join(valid_categories)
            raise ValueError(f"등록되지 않은 카테고리입니다: '{category}'. [가능 목록]: {cats_str}")

        unique_id = str(uuid.uuid4())[:8]
        tx = Transaction(
            id=unique_id,
            type=tx_type,  # type: ignore[arg-type]
            date=date_str,
            amount=amount,
            category=category,
            memo=memo,
            tags=tags,
        )
        self.repo.append_transaction(tx)
        return unique_id

    # ---------------------------------------------------------
    # 5단계: 거래 목록(List) 및 검색(Search)
    # ---------------------------------------------------------
    def filter_transactions_stream(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        category: Optional[str] = None,
        tx_type: Optional[str] = None,
        keyword: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> Generator[Transaction, None, None]:
        for tx in self.repo.stream_transactions():
            if from_date and tx.date < from_date:
                continue
            if to_date and tx.date > to_date:
                continue
            if category and tx.category != category:
                continue
            if tx_type and tx.type != tx_type:
                continue
            if keyword and (keyword not in tx.memo):
                continue
            if tag and (tag not in tx.tags):
                continue
            yield tx

    def list_transactions(self, limit: int = 10) -> List[Transaction]:
        all_transactions = list(self.repo.stream_transactions())
        all_transactions.sort(key=lambda x: x.date, reverse=True)
        return all_transactions[:limit]

    def search_transactions(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        category: Optional[str] = None,
        tx_type: Optional[str] = None,
        keyword: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[Transaction]:
        stream = self.filter_transactions_stream(
            from_date=from_date,
            to_date=to_date,
            category=category,
            tx_type=tx_type,
            keyword=keyword,
            tag=tag,
        )
        filtered_list = list(stream)
        filtered_list.sort(key=lambda x: x.date, reverse=True)
        return filtered_list

    # ---------------------------------------------------------
    # 6단계: 거래 삭제(Delete) 및 수정(Update)
    # ---------------------------------------------------------
    def delete_transaction(self, tx_id: str) -> bool:
        all_tx = list(self.repo.stream_transactions())
        remaining_tx = [tx for tx in all_tx if tx.id != tx_id]
        if len(all_tx) == len(remaining_tx):
            return False
        self.repo.overwrite_transactions(remaining_tx)
        return True

    def update_transaction(
        self,
        tx_id: str,
        date_str: Optional[str] = None,
        tx_type: Optional[str] = None,
        category: Optional[str] = None,
        amount: Optional[int] = None,
        memo: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        all_tx = list(self.repo.stream_transactions())
        target_tx = next((tx for tx in all_tx if tx.id == tx_id), None)
        if target_tx is None:
            return False

        if date_str is not None:
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"수정할 날짜 형식이 올바르지 않습니다: '{date_str}'")
            target_tx.date = date_str

        if tx_type is not None:
            if tx_type not in ("income", "expense"):
                raise ValueError("거래 타입은 'income' 또는 'expense'여야 합니다.")
            target_tx.type = tx_type  # type: ignore[assignment]

        if category is not None:
            valid_cats = self.repo.load_categories()
            if category not in valid_cats:
                raise ValueError(f"등록되지 않은 카테고리입니다: '{category}'")
            target_tx.category = category

        if amount is not None:
            if amount <= 0:
                raise ValueError("금액은 0보다 큰 양수 정수여야 합니다.")
            target_tx.amount = amount

        if memo is not None:
            target_tx.memo = memo

        if tags is not None:
            target_tx.tags = tags

        self.repo.overwrite_transactions(all_tx)
        return True

    # ---------------------------------------------------------
    # 7단계: 카테고리 관리 (Category)
    # ---------------------------------------------------------
    def list_categories(self) -> List[str]:
        return self.repo.load_categories()

    def add_category(self, name: str) -> None:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("카테고리 이름은 공백일 수 없습니다.")

        cats = self.repo.load_categories()
        if clean_name in cats:
            raise ValueError(f"이미 등록되어 있는 카테고리입니다: '{clean_name}'")

        cats.append(clean_name)
        self.repo.save_categories(cats)

    def remove_category(self, name: str) -> None:
        clean_name = name.strip()
        cats = self.repo.load_categories()

        if clean_name not in cats:
            raise ValueError(f"존재하지 않는 카테고리입니다: '{clean_name}'")

        for tx in self.repo.stream_transactions():
            if tx.category == clean_name:
                raise ValueError(
                    f"카테고리 '{clean_name}'을(를) 사용 중인 거래 내역(ID: {tx.id} 등)이 존재합니다.\n"
                    f"관련 거래를 먼저 수정하거나 삭제한 후에 카테고리를 삭제할 수 있습니다."
                )

        cats.remove(clean_name)
        self.repo.save_categories(cats)

    # ---------------------------------------------------------
    # 8단계: 예산(Budget) 및 요약(Summary)
    # ---------------------------------------------------------
    def set_budget(self, month: str, amount: int) -> None:
        try:
            datetime.strptime(month, "%Y-%m")
        except ValueError:
            raise ValueError(f"월 형식이 올바르지 않습니다: '{month}'. 'YYYY-MM' 형식이어야 합니다.")

        if amount <= 0:
            raise ValueError(f"예산 금액은 0보다 큰 양수 정수여야 합니다: {amount}")

        budget = Budget(month=month, amount=amount)
        self.repo.set_budget(budget)

    def get_monthly_summary(self, month: str, top_n: int = 3) -> Optional[Dict[str, Any]]:
        try:
            datetime.strptime(month, "%Y-%m")
        except ValueError:
            raise ValueError(f"월 형식이 올바르지 않습니다: '{month}'. 'YYYY-MM' 형식이어야 합니다.")

        if top_n <= 0:
            raise ValueError(f"--top 옵션 값은 1 이상이어야 합니다: {top_n}")

        total_income = 0
        total_expense = 0
        category_expenses: Dict[str, int] = defaultdict(int)
        has_data = False

        for tx in self.repo.stream_transactions():
            if tx.date.startswith(month):
                has_data = True
                if tx.type == "income":
                    total_income += tx.amount
                elif tx.type == "expense":
                    total_expense += tx.amount
                    category_expenses[tx.category] += tx.amount

        if not has_data:
            return None

        sorted_top_categories: List[Tuple[str, int]] = sorted(
            category_expenses.items(), key=lambda item: item[1], reverse=True
        )[:top_n]

        budget = self.repo.get_budget(month)

        return {
            "month": month,
            "income": total_income,
            "expense": total_expense,
            "balance": total_income - total_expense,
            "top_categories": sorted_top_categories,
            "budget": budget,
        }

    # ---------------------------------------------------------
    # 9단계: CSV 가져오기/내보내기 (Import/Export)
    # ---------------------------------------------------------
    def export_transactions_csv(
        self,
        out_path: str,
        month: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> int:
        """
        [내보내기 요건 충족]
        - --month 또는 --from/--to 조건 중 1개 이상 필수 확인
        - UTF-8 인코딩 및 필수 헤더 포함
        - 고정 스키마 순서: date, type, category, amount, memo, tags
        - 추출된 실제 건수(int) 반환
        """
        # 1. 필수 조건 검사 (--month 또는 기간 조건 필수)
        if month:
            from_date = f"{month}-01"
            to_date = f"{month}-31"

        if not from_date or not to_date:
            raise ValueError("내보내기를 수행하려면 '--month YYYY-MM' 또는 '--from과 --to' 조건을 반드시 지정해야 합니다.")

        # 대상 디렉터리가 없으면 자동 생성
        out_dir = os.path.dirname(out_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        exported_count = 0
        # UTF-8, newline='' 명시 (윈도우 줄바꿈 중복 방지)
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            # 첫 줄 필수 헤더 기록
            writer.writerow(["date", "type", "category", "amount", "memo", "tags"])

            # 스트리밍 순회로 조건에 맞는 것만 기록
            for tx in self.repo.stream_transactions():
                if from_date <= tx.date <= to_date:
                    tags_str = ",".join(tx.tags) if tx.tags else ""
                    writer.writerow([tx.date, tx.type, tx.category, tx.amount, tx.memo, tags_str])
                    exported_count += 1

        return exported_count

    def import_transactions_csv(self, file_path: str) -> int:
        """
        [가져오기 요건 충족]
        - UTF-8 인코딩 파일 읽기
        - CSV 헤더 스키마 검증
        - 각 행별 데이터 유효성 검증(날짜, 타입, 카테고리, 금액) 및 일괄 등록
        - 실제 반영된 건수(int) 반환
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"가져올 CSV 파일이 존재하지 않습니다: '{file_path}'")

        imported_count = 0
        required_columns = {"date", "type", "category", "amount"}

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # 헤더 검증
            if not reader.fieldnames or not required_columns.issubset(set(reader.fieldnames)):
                cols_str = ", ".join(required_columns)
                raise ValueError(f"CSV 스키마 오류: 필수 헤더 컬럼({cols_str})이 누락되었습니다.")

            # 행 단위 검증 및 등록
            for row_idx, row in enumerate(reader, start=2):
                date_val = row.get("date", "").strip()
                type_val = row.get("type", "").strip()
                cat_val = row.get("category", "").strip()
                amount_raw = row.get("amount", "").strip()
                memo_val = row.get("memo", "").strip()
                tags_raw = row.get("tags", "").strip()

                # 금액 정수 변환 검증
                try:
                    amount_val = int(amount_raw)
                except ValueError:
                    raise ValueError(f"[행 {row_idx}] 금액은 양수 정수여야 합니다: '{amount_raw}'")

                # 태그 파싱 (쉼표 구분)
                tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()]

                # create_transaction 내부에서 날짜, 타입, 등록 카테고리, 양수 여부를 정밀 검증
                try:
                    self.create_transaction(
                        date_str=date_val,
                        tx_type=type_val,
                        category=cat_val,
                        amount=amount_val,
                        memo=memo_val,
                        tags=tags_list,
                    )
                    imported_count += 1
                except ValueError as ve:
                    raise ValueError(f"[행 {row_idx} 데이터 오류] {ve}")

        return imported_count