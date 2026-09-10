"""
cli.py
가계부 콘솔 입출력 및 명령줄 인터페이스(CLI)를 전담하는 프레젠테이션 계층입니다.
4단계부터 9단계(export, import)까지의 모든 CLI 명세가 구현되어 있습니다.
"""

import argparse
import sys
from datetime import datetime
from typing import List

from .decorators import handle_cli_errors
from .repositories import FileRepository
from .services import BudgetService


# =====================================================================
# 4단계 대화형 입력 헬퍼 함수
# =====================================================================

def prompt_date() -> str:
    while True:
        val = input("1. 날짜 (YYYY-MM-DD): ").strip()
        try:
            datetime.strptime(val, "%Y-%m-%d")
            return val
        except ValueError:
            print("   [입력 오류] 'YYYY-MM-DD' 형식(예: 2026-05-15)으로 정확히 입력하세요.")


def prompt_type() -> str:
    while True:
        val = input("2. 타입 (income/expense): ").strip().lower()
        if val in ("income", "expense"):
            return val
        print("   [입력 오류] 수입은 'income', 지출은 'expense'로만 입력할 수 있습니다.")


def prompt_category(valid_categories: List[str]) -> str:
    cats_display = ", ".join(valid_categories)
    while True:
        print(f"   (등록된 카테고리: {cats_display})")
        val = input("3. 카테고리: ").strip()
        if val in valid_categories:
            return val
        print(f"   [입력 오류] '{val}'은(는) 등록되지 않은 카테고리입니다.")


def prompt_amount() -> int:
    while True:
        val = input("4. 금액 (양수 정수): ").strip().replace(",", "")
        try:
            num = int(val)
            if num > 0:
                return num
            print("   [입력 오류] 금액은 0보다 큰 양수 정수여야 합니다.")
        except ValueError:
            print("   [입력 오류] 숫자 형태로만 입력해 주세요.")


def prompt_memo() -> str:
    return input("5. 메모 (선택 사항, 없으면 Enter): ").strip()


def prompt_tags() -> List[str]:
    val = input("6. 태그 (선택 사항, 쉼표로 구분 예: 점심,외식): ").strip()
    if not val:
        return []
    return [t.strip() for t in val.split(",") if t.strip()]


# =====================================================================
# CLI 메인 진입 함수
# =====================================================================

@handle_cli_errors
def run_cli() -> None:
    parser = argparse.ArgumentParser(
        prog="budget_app",
        description="콘솔 가계부 애플리케이션 (Python 3.10+)"
    )
    parser.add_argument(
        "--data-dir",
        default="./data",
        help="데이터 파일 저장 디렉터리 경로 (기본값: ./data)"
    )

    subparsers = parser.add_subparsers(dest="command", help="실행할 명령어")

    # 1. add
    subparsers.add_parser("add", help="대화형으로 새로운 거래 내역을 추가합니다.")

    # 2. list
    list_parser = subparsers.add_parser("list", help="최신 거래 내역 목록을 조회합니다.")
    list_parser.add_argument("--limit", type=int, default=10, help="출력할 최대 거래 개수 (기본값: 10)")

    # 3. search
    search_parser = subparsers.add_parser("search", help="다양한 조건으로 거래 내역을 검색합니다.")
    search_parser.add_argument("--from", dest="from_date", help="검색 시작일 (YYYY-MM-DD)")
    search_parser.add_argument("--to", dest="to_date", help="검색 종료일 (YYYY-MM-DD)")
    search_parser.add_argument("--category", help="카테고리 일치 검색")
    search_parser.add_argument("--type", choices=["income", "expense"], help="거래 타입")
    search_parser.add_argument("--q", dest="keyword", help="메모 검색 키워드")
    search_parser.add_argument("--tag", help="특정 태그 포함 여부")

    # 4. delete
    del_parser = subparsers.add_parser("delete", help="거래 내역을 삭제합니다.")
    del_parser.add_argument("--id", required=True, help="삭제할 거래 ID")

    # 5. update
    update_parser = subparsers.add_parser("update", help="거래 내역을 수정합니다.")
    update_parser.add_argument("--id", required=True, help="수정할 대상 거래 ID")
    update_parser.add_argument("--date", help="새로운 날짜 (YYYY-MM-DD)")
    update_parser.add_argument("--type", choices=["income", "expense"], help="새로운 거래 타입")
    update_parser.add_argument("--category", help="새로운 카테고리")
    update_parser.add_argument("--amount", type=int, help="새로운 금액 (양수 정수)")
    update_parser.add_argument("--memo", help="새로운 메모")
    update_parser.add_argument("--tags", help="새로운 태그 (쉼표로 구분)")

    # 6. category
    cat_parser = subparsers.add_parser("category", help="카테고리를 관리합니다.")
    cat_sub = cat_parser.add_subparsers(dest="category_action", help="카테고리 작업 선택")
    cat_sub.add_parser("list", help="전체 카테고리 목록을 확인합니다.")
    cat_add = cat_sub.add_parser("add", help="새로운 카테고리를 추가합니다.")
    cat_add.add_argument("name", help="추가할 카테고리 이름")
    cat_del = cat_sub.add_parser("remove", help="카테고리를 삭제합니다.")
    cat_del.add_argument("name", help="삭제할 카테고리 이름")

    # 7. budget
    budget_parser = subparsers.add_parser("budget", help="월별 예산을 관리합니다.")
    budget_sub = budget_parser.add_subparsers(dest="budget_action", help="예산 작업 선택")
    b_set = budget_sub.add_parser("set", help="월별 예산을 설정합니다.")
    b_set.add_argument("--month", required=True, help="설정 대상 월 (YYYY-MM)")
    b_set.add_argument("--amount", type=int, required=True, help="예산 금액 (양수 정수)")

    # 8. summary
    sum_parser = subparsers.add_parser("summary", help="월별 요약 리포트를 출력합니다.")
    sum_parser.add_argument("--month", required=True, help="조회할 대상 월 (YYYY-MM)")
    sum_parser.add_argument("--top", type=int, default=3, help="지출 상위 카테고리 수 (기본값: 3)")

    # 9. export (9단계 요건: export --out <csv> [--month | --from & --to])
    exp_parser = subparsers.add_parser("export", help="조건에 맞는 거래 내역을 CSV 파일로 내보냅니다.")
    exp_parser.add_argument("--out", required=True, help="저장할 CSV 파일 경로 (필수)")
    exp_parser.add_argument("--month", help="내보낼 대상 월 (YYYY-MM)")
    exp_parser.add_argument("--from", dest="from_date", help="시작일 (YYYY-MM-DD)")
    exp_parser.add_argument("--to", dest="to_date", help="종료일 (YYYY-MM-DD)")

    # 10. import (9단계 요건: import --from <csv>)
    imp_parser = subparsers.add_parser("import", help="CSV 파일로부터 거래 내역을 일괄 가져옵니다.")
    imp_parser.add_argument("--from", dest="input_file", required=True, help="가져올 CSV 파일 경로 (필수)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    repo = FileRepository(data_dir=args.data_dir)
    service = BudgetService(repo=repo)

    # 분기 1: add
    if args.command == "add":
        print("========================================")
        print("         새로운 거래 내역 추가          ")
        print("========================================")
        tx_date = prompt_date()
        tx_type = prompt_type()
        tx_category = prompt_category(repo.load_categories())
        tx_amount = prompt_amount()
        tx_memo = prompt_memo()
        tx_tags = prompt_tags()

        new_id = service.create_transaction(
            date_str=tx_date,
            tx_type=tx_type,
            category=tx_category,
            amount=tx_amount,
            memo=tx_memo,
            tags=tx_tags
        )
        print("========================================")
        print("✔ 거래가 성공적으로 저장되었습니다.")
        print(f"✔ 생성된 거래 ID: {new_id}")
        print("========================================")

    # 분기 2: list
    elif args.command == "list":
        results = service.list_transactions(limit=args.limit)
        if not results:
            print("조회할 거래 내역이 없습니다.")
            return

        print(f"\n=== 최신 거래 내역 (최대 {args.limit}건) ===")
        print(f"{'ID':<10} {'날짜':<12} {'구분':<8} {'카테고리':<10} {'금액':>10}원  {'메모'} (태그)")
        print("-" * 75)
        for tx in results:
            tag_str = f"({', '.join(tx.tags)})" if tx.tags else ""
            print(f"{tx.id:<10} {tx.date:<12} {tx.type:<8} {tx.category:<10} {tx.amount:>10,}원  {tx.memo} {tag_str}")
        print("-" * 75)

    # 분기 3: search
    elif args.command == "search":
        results = service.search_transactions(
            from_date=args.from_date,
            to_date=args.to_date,
            category=args.category,
            tx_type=args.type,
            keyword=args.keyword,
            tag=args.tag
        )
        if not results:
            print("검색 조건과 일치하는 거래 내역이 없습니다.")
            return

        print(f"\n=== 거래 검색 결과 (총 {len(results)}건) ===")
        print(f"{'ID':<10} {'날짜':<12} {'구분':<8} {'카테고리':<10} {'금액':>10}원  {'메모'} (태그)")
        print("-" * 75)
        for tx in results:
            tag_str = f"({', '.join(tx.tags)})" if tx.tags else ""
            print(f"{tx.id:<10} {tx.date:<12} {tx.type:<8} {tx.category:<10} {tx.amount:>10,}원  {tx.memo} {tag_str}")
        print("-" * 75)

    # 분기 4: delete
    elif args.command == "delete":
        success = service.delete_transaction(tx_id=args.id)
        if success:
            print(f"✔ 거래 ID '{args.id}' 내역이 성공적으로 삭제되었습니다.")
        else:
            print(f"[안내] ID '{args.id}'에 해당하는 거래 데이터가 존재하지 않습니다.")

    # 분기 5: update
    elif args.command == "update":
        tags_list = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else None
        success = service.update_transaction(
            tx_id=args.id,
            date_str=args.date,
            tx_type=args.type,
            category=args.category,
            amount=args.amount,
            memo=args.memo,
            tags=tags_list
        )
        if success:
            print(f"✔ 거래 ID '{args.id}' 내역이 성공적으로 수정되었습니다.")
        else:
            print(f"[안내] ID '{args.id}'에 해당하는 거래 데이터가 존재하지 않습니다.")

    # 분기 6: category
    elif args.command == "category":
        if not args.category_action:
            cat_parser.print_help()
            return

        if args.category_action == "list":
            categories = service.list_categories()
            print("\n=== 등록된 카테고리 목록 ===")
            for idx, c in enumerate(categories, 1):
                print(f"{idx}. {c}")
            print("-" * 30)

        elif args.category_action == "add":
            service.add_category(name=args.name)
            print(f"✔ 카테고리 '{args.name}'이(가) 성공적으로 추가되었습니다.")

        elif args.category_action == "remove":
            service.remove_category(name=args.name)
            print(f"✔ 카테고리 '{args.name}'이(가) 성공적으로 삭제되었습니다.")

    # 분기 7: budget
    elif args.command == "budget":
        if args.budget_action == "set":
            service.set_budget(month=args.month, amount=args.amount)
            print(f"✔ {args.month}월 예산이 {args.amount:,}원으로 설정되었습니다.")
        else:
            budget_parser.print_help()

    # 분기 8: summary
    elif args.command == "summary":
        summary = service.get_monthly_summary(month=args.month, top_n=args.top)

        if summary is None:
            print(f"\n[안내] {args.month}월에는 등록된 거래 데이터가 없습니다.")
            return

        print(f"\n========================================")
        print(f"         {args.month} 가계부 요약 리포트         ")
        print(f"========================================")
        print(f"• 총 수입 : {summary['income']:>12,}원")
        print(f"• 총 지출 : {summary['expense']:>12,}원")
        print(f"• 잔   액 : {summary['balance']:>12,}원 (총수입 - 총지출)")
        print(f"----------------------------------------")
        print(f"▶ 지출 카테고리 TOP {args.top}")
        if not summary["top_categories"]:
            print("  (지출 내역이 없습니다.)")
        else:
            for rank, (cat_name, cat_amt) in enumerate(summary["top_categories"], 1):
                print(f"  {rank}. {cat_name:<10}: {cat_amt:>10,}원")

        budget_info = summary["budget"]
        print(f"----------------------------------------")
        if budget_info:
            b_amount = budget_info.amount
            usage_rate = (summary["expense"] / b_amount) * 100
            print(f"• 설정 예산 : {b_amount:>12,}원")
            print(f"• 예산 사용률: {usage_rate:>11.1f}%")

            if summary["expense"] > b_amount:
                over_amount = summary["expense"] - b_amount
                print(f"\n※ [경고] 설정한 월 예산을 초과했습니다! (초과액: {over_amount:,}원)")
            else:
                remaining_budget = b_amount - summary["expense"]
                print(f"• 남은 예산 : {remaining_budget:>12,}원")
        else:
            print("• 설정된 월 예산이 없습니다. ('budget set' 명령어로 설정 가능)")
        print(f"========================================\n")

    # 분기 9: export (9단계 요건 충족)
    elif args.command == "export":
        count = service.export_transactions_csv(
            out_path=args.out,
            month=args.month,
            from_date=args.from_date,
            to_date=args.to_date
        )
        print(f"✔ 내보내기 성공: 총 {count}건의 거래 내역이 '{args.out}' 파일로 저장되었습니다.")

    # 분기 10: import (9단계 요건 충족)
    elif args.command == "import":
        count = service.import_transactions_csv(file_path=args.input_file)
        print(f"✔ 가져오기 성공: 총 {count}건의 거래 내역이 성공적으로 반영되었습니다.")