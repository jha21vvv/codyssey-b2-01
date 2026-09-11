"""
=============================================================================
[services.py] 데이터 흐름, 함수 순서도 및 쉬운 업무 해설
=============================================================================

1. 데이터가 들어오고 나갈 때의 함수 순서도:
   [새 거래를 추가할 때: create_transaction()]
   1단계: 날짜, 수입/지출, 카테고리, 금액 검사 (엉터리 값이면 즉시 거절)
   2단계: uuid.uuid4() 로 8자리 주민번호 ID 발급 (예: "a1b2c3d4")
   3단계: Transaction 영수증 객체 조립
   4단계: repo.append_transaction(tx) 호출 ──▶ 창고지기에게 장부 맨 끝에 적으라고 전달!

   [월별 결산을 낼 때: get_monthly_summary()]
   1단계: 총수입=0, 총지출=0, 카테고리별 지출 바구니 준비
   2단계: repo.stream_transactions() 로 창고지기에게 영수증을 1장씩 받음
   3단계: 당월 영수증을 골라내어 "수입"이면 총수입에 더하고, "지출"이면 총지출 및 항목별 지출에 누적
   4단계: 가장 돈을 많이 쓴 카테고리 순서대로 1위, 2위, 3위 정렬
   5단계: 이번 달 예산과 비교하여 초과 여부를 계산하고 최종 리포트 반환!

   [카테고리를 지우려고 할 때: remove_category()]
   1단계: 장부의 모든 거래 내역을 하나씩 훑어봄
   2단계: "이 카테고리를 쓴 영수증이 1장이라도 있는가?" 전수 조사
   3단계: 1장이라도 발견되면 즉시 삭제 거절! (이름표 잃어버린 고아 영수증 방지)

2. 이 파일의 진짜 업무 (전문용어 0% 쉬운 설명):
   [1차 설명: 코드가 실제로 하는 일]
   - 가계부의 핵심 계산과 업무 규칙을 처리합니다. 거래를 추가할 때 번호표를 붙여주고, 
     한 달 치 수입과 지출을 계산기에 두드려 통계를 내며, 거래에 쓰이고 있는 카테고리는 마음대로 지우지 못하게 보호합니다.

   [2차 업무/비유 설명: 실제 실생활 업무 관점]
   - 가계부 회사의 머리 좋은 [수석 총무 / 전문 회계사]입니다.
   - 앞쪽의 접수대(cli.py)는 손님과 대화만 나누고, 뒤쪽의 창고지기(repositories.py)는 장부에 글씨만 쓸 줄 압니다.
   - 실제로 "이번 달에 식비로 얼마를 썼지?", "가장 돈을 많이 쓴 카테고리 1, 2, 3위는 뭐지?", 
     "예산 50만 원 중에 얼마나 초과했지?", "이 카테고리를 지금 지워도 거래에 문제가 없을까?" 같은 
     모든 복잡한 계산과 똑똑한 업무 판단은 전부 이 회계사가 전담합니다.
=============================================================================
"""

# [1차 설명]: 엑셀에서 열어볼 수 있는 CSV 파일로 거래를 내보내거나 읽기 위해 가져옵니다.
# [2차 업무 설명]: 엑셀 서류 양식으로 장부를 인쇄하거나 읽어 들이는 인쇄기입니다.
import csv
# [1차 설명]: 폴더를 만들거나 파일 존재 여부를 확인하기 위해 가져옵니다.
import os
# [1차 설명]: 거래마다 중복되지 않는 8자리 고유 식별번호를 발급하기 위해 가져옵니다.
# [2차 업무 설명]: 영수증마다 겹치지 않게 "a1b2c3d4" 같은 고유 주민번호 도장을 찍어주는 기계입니다.
import uuid
# [1차 설명]: 카테고리별 지출을 합산할 때 기본값을 0으로 자동 채워주는 딕셔너리 도구입니다.
# [2차 업무 설명]: "새로운 카테고리가 나오면 빈 바구니(0원)부터 시작해라!" 하고 자동으로 바구니를 꺼내주는 일입니다.
from collections import defaultdict
# [1차 설명]: 날짜 문자열이 진짜 달력에 존재하는 날인지 검사하기 위해 가져옵니다.
from datetime import datetime
# [1차 설명]: 함수의 입력과 출력 상자 타입을 표시하기 위해 가져옵니다.
from typing import Any, Dict, Generator, List, Optional, Tuple

# [1차 설명]: models.py에서 정의한 영수증 규격 틀을 가져옵니다.
from .models import Budget, Transaction
# [1차 설명]: 장부 보관소 창고지기 클래스를 가져옵니다.
from .repositories import FileRepository


# [1차 설명]: 가계부의 핵심 계산과 업무 규칙을 총괄하는 서비스 클래스입니다.
# [2차 업무 설명]: 가계부 매장의 똑똑한 [수석 회계사]입니다.
class BudgetService:
    # [1차 설명]: 회계사 객체가 생성될 때 창고지기(FileRepository)를 파트너로 배정받습니다.
    # [2차 업무 설명]: 회계사가 계산한 장부를 안전하게 보관해 줄 전담 창고지기 파트너를 배정하는 일입니다.
    def __init__(self, repo: FileRepository) -> None:
        self.repo = repo

    # ---------------------------------------------------------
    # 4단계: 거래 추가 (Add)
    # ---------------------------------------------------------
    # [1차 설명]: 새로운 거래 1건을 검증하고, 고유 ID를 붙여 창고지기에게 저장을 맡깁니다.
    # [2차 업무 설명]: 손님이 가져온 영수증에 가짜 날짜나 마이너스 돈이 없는지 검사하고, 8자리 번호표를 붙여 장부에 적어두는 업무입니다.
    def create_transaction(
        self,
        date_str: str,
        tx_type: str,
        category: str,
        amount: int,
        memo: str = "",
        tags: Optional[List[str]] = None,
    ) -> str:
        # [1차 설명]: tags 인자가 None이면 빈 리스트([])로 초기화합니다.
        # [2차 업무 설명]: 태그를 안 적었을 때 빈 바구니로 준비해 두는 일입니다.
        if tags is None:
            # [1차 설명]: 빈 리스트를 tags에 할당합니다.
            # [2차 업무 설명]: 태그 목록을 빈칸으로 채웁니다.
            tags = []

        # [1차 설명]: 날짜가 올바른 달력 날짜인지 검사합니다.
        # [2차 업무 설명]: 달력 책과 대조하여 가짜 날짜가 아닌지 확인합니다.
        try:
            # [1차 설명]: 날짜 문자열을 YYYY-MM-DD 형식으로 분석합니다.
            # [2차 업무 설명]: "2026-05-15" 글자를 진짜 달력 날짜로 맞추어봅니다.
            datetime.strptime(date_str, "%Y-%m-%d")
        # [1차 설명]: 잘못된 날짜 형식일 때 발생하는 에러를 잡습니다.
        # [2차 업무 설명]: 2월 30일 같은 엉터리 날짜를 적었을 때 거절합니다.
        except ValueError:
            # [1차 설명]: 올바른 형식으로 적으라는 에러를 던집니다.
            # [2차 업무 설명]: 손님에게 날짜를 똑바로 적으라고 퇴짜를 놓습니다.
            raise ValueError(f"날짜 형식이 올바르지 않습니다: '{date_str}'. 'YYYY-MM-DD' 형식이어야 합니다.")

        # [1차 설명]: 수입(income)인지 지출(expense)인지 검사합니다.
        # [2차 업무 설명]: 들어온 돈인지 나간 돈인지 구분이 맞지 않으면 거절합니다.
        if tx_type not in ("income", "expense"):
            # [1차 설명]: 유효하지 않은 타입 에러를 던집니다.
            # [2차 업무 설명]: 수입이나 지출 둘 중 하나만 적으라고 안내합니다.
            raise ValueError(f"거래 타입이 올바르지 않습니다: '{tx_type}'. 'income' 또는 'expense'여야 합니다.")

        # [1차 설명]: 금액이 양수인지 검사합니다.
        # [2차 업무 설명]: 0원이나 마이너스 돈은 장부에 적을 수 없으므로 거절합니다.
        if amount <= 0:
            # [1차 설명]: 금액이 0보다 커야 한다는 에러를 던집니다.
            # [2차 업무 설명]: 1원 이상의 진짜 돈을 적으라고 거절합니다.
            raise ValueError(f"금액은 0보다 큰 양수 정수여야 합니다: {amount}")
        #마이: 여기까지가 제대로 들어왔는지 체크하는것.

        # [1차 설명]: 등록되어 있는 진짜 카테고리인지 창고지기의 카테고리 명단과 대조합니다.
        # [2차 업무 설명]: "등록되지 않은 듣도 보도 못한 카테고리"는 거절하고 등록된 카테고리를 쓰도록 안내합니다.
        valid_categories = self.repo.load_categories()
        # [1차 설명]: 입력한 카테고리가 명단 안에 없는지 확인합니다.
        # [2차 업무 설명]: 등록된 분류 명단에 없는 엉뚱한 이름인지 검사합니다.
        if category not in valid_categories:
            # [1차 설명]: 등록된 카테고리들을 쉼표로 연결한 문자열을 만듭니다.
            # [2차 업무 설명]: 손님이 참고할 수 있게 현재 사용 가능한 카테고리 보기 목록을 만듭니다.
            cats_str = ", ".join(valid_categories)
            # [1차 설명]: 등록되지 않은 카테고리 에러를 목록과 함께 던집니다.
            # [2차 업무 설명]: "이 중에서 골라주세요" 하고 거절 안내를 보냅니다.
            raise ValueError(f"등록되지 않은 카테고리입니다: '{category}'. [가능 목록]: {cats_str}")

        # [1차 설명]: 세상에 겹치지 않는 8자리 고유 번호(ID)를 발급합니다.
        # [2차 업무 설명]: 영수증마다 고유 주민번호처럼 8자리 번호표(예: a1b2c3d4)를 딱 찍어줍니다.
        unique_id = str(uuid.uuid4())[:8]

        # [1차 설명]: 검사관을 통과한 공식 영수증 객체를 조립합니다.
        # [2차 업무 설명]: 번호, 구분, 날짜, 금액, 카테고리, 메모, 태그가 완벽히 채워진 공식 영수증 종이를 인쇄합니다.
        # 마이: 아이디 번호 만들어서 최종 저장용 내용 만드는 부분
        tx = Transaction(
            id=unique_id,
            type=tx_type,  # type: ignore[arg-type]
            date=date_str,
            amount=amount,
            category=category,
            memo=memo,
            tags=tags,
        )
        # [1차 설명]: 창고지기에게 장부 맨 끝에 적어두라고 건넵니다.
        # [2차 업무 설명]: 창고지기에게 영수증을 주며 transactions.jsonl 맨 뒤에 볼펜으로 적으라고 시킵니다.
        #마이: 레포에 추가 하는걸로 봐선 마지막에 레포를 저장하느 방식인듯함.
        self.repo.append_transaction(tx)
        # [1차 설명]: 발급된 8자리 번호표를 반환합니다.
        # [2차 업무 설명]: 손님에게 "영수증 번호는 {unique_id}입니다" 하고 번호를 건네줍니다.
        return unique_id

    # ---------------------------------------------------------
    # 5단계: 거래 목록(List) 및 검색(Search)
    # ---------------------------------------------------------
    # [1차 설명]: 조건(기간, 카테고리, 키워드 등)에 맞는 영수증만 체로 걸러내듯 하나씩 뽑아냅니다.
    # [2차 업무 설명]: "지난달 1일부터 말일까지 중에서 '식비'로 쓴 영수증만 골라줘!" 할 때 조건에 맞는 영수증만 쏙쏙 건져내는 업무입니다.
    def filter_transactions_stream(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        category: Optional[str] = None,
        tx_type: Optional[str] = None,
        keyword: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> Generator[Transaction, None, None]:
        # [1차 설명]: 창고지기에게서 영수증을 1장씩 순서대로 받아옵니다.
        # [2차 업무 설명]: 장부의 영수증을 한 장씩 차례로 검사대에 올려놓습니다.
        for tx in self.repo.stream_transactions():
            # [1차 설명]: 시작일 조건보다 앞선 영수증인지 검사합니다.
            # [2차 업무 설명]: 검색 시작 날짜보다 이전의 옛날 영수증이면 제외합니다.
            if from_date and tx.date < from_date:
                # [1차 설명]: 조건에 안 맞으므로 다음 영수증으로 넘어갑니다.
                continue
            # [1차 설명]: 종료일 조건보다 뒤의 영수증인지 검사합니다.
            # [2차 업무 설명]: 검색 종료 날짜보다 나중의 미래 영수증이면 제외합니다.
            if to_date and tx.date > to_date:
                # [1차 설명]: 조건에 안 맞으므로 건너뜁니다.
                continue
            # [1차 설명]: 지정한 카테고리와 다른 영수증인지 검사합니다.
            # [2차 업무 설명]: 찾는 카테고리(예: 식비)가 아니면 제외합니다.
            if category and tx.category != category:
                # [1차 설명]: 건너뜁니다.
                continue
            # [1차 설명]: 지정한 수입/지출 타입과 다른지 검사합니다.
            # [2차 업무 설명]: 수입만 보고 싶은데 지출이면 제외합니다.
            if tx_type and tx.type != tx_type:
                # [1차 설명]: 건너뜁니다.
                continue
            # [1차 설명]: 메모에 검색 단어가 들어있지 않은지 검사합니다.
            # [2차 업무 설명]: 메모에 찾는 글자("스타벅스")가 없으면 제외합니다.
            if keyword and (keyword not in tx.memo):
                # [1차 설명]: 건너뜁니다.
                continue
            # [1차 설명]: 찾는 태그가 영수증 태그 명단에 없는지 검사합니다.
            # [2차 업무 설명]: 찾는 태그("외식")가 안 달려있으면 제외합니다.
            if tag and (tag not in tx.tags):
                # [1차 설명]: 건너뜁니다.
                continue
            # [1차 설명]: 모든 시험을 통과한 알짜 영수증을 바깥으로 배달합니다.
            # [2차 업무 설명]: 손님이 찾는 조건과 100% 일치하는 합격 영수증을 1장 건네줍니다.
            yield tx

    # [1차 설명]: 최근 거래 목록을 최신 날짜 순으로 limit 개수만큼 정렬하여 가져옵니다.
    # [2차 업무 설명]: 가장 최근에 쓴 돈 내역이 맨 위에 오도록 영수증을 날짜 역순으로 줄 세워 딱 10장만 보여주는 업무입니다.
    def list_transactions(self, limit: int = 10) -> List[Transaction]:
        # [1차 설명]: 장부의 모든 거래 내역을 리스트 바구니로 모읍니다.
        # [2차 업무 설명]: 창고에서 영수증들을 전부 꺼내 책상 위에 올립니다.
        all_transactions = list(self.repo.stream_transactions())
        # [1차 설명]: 날짜(date)를 기준으로 최신순(내림차순 reverse=True) 정렬합니다.
        # [2차 업무 설명]: 가장 최근 날짜의 영수증이 맨 앞으로 오도록 순서를 바꿉니다.
        all_transactions.sort(key=lambda x: x.date, reverse=True)
        # [1차 설명]: 맨 앞부터 limit 개수(기본 10개)만큼만 잘라서 반환합니다.
        # [2차 업무 설명]: 최신 영수증 딱 10장만 손님에게 보여줍니다.
        return all_transactions[:limit]

    # [1차 설명]: 조건에 맞춰 영수증을 검색하고 최신순으로 정렬된 목록을 반환합니다.
    # [2차 업무 설명]: 조건에 맞는 영수증만 골라내어 최신순으로 반듯하게 줄 세워 건네주는 업무입니다.
    def search_transactions(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        category: Optional[str] = None,
        tx_type: Optional[str] = None,
        keyword: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[Transaction]:
        # [1차 설명]: 조건에 맞는 영수증 스트림 배달원을 생성합니다.
        # [2차 업무 설명]: 필터 검사대를 통과한 영수증 배달기를 준비합니다.
        stream = self.filter_transactions_stream(
            from_date=from_date,
            to_date=to_date,
            category=category,
            tx_type=tx_type,
            keyword=keyword,
            tag=tag,
        )
        # [1차 설명]: 배달된 합격 영수증들을 리스트로 묶습니다.
        # [2차 업무 설명]: 합격 영수증들을 한 바구니에 차곡차곡 담습니다.
        filtered_list = list(stream)
        # [1차 설명]: 최신 날짜 역순으로 정렬합니다.
        # [2차 업무 설명]: 최근 날짜 영수증이 맨 위에 오도록 줄을 세웁니다.
        filtered_list.sort(key=lambda x: x.date, reverse=True)
        # [1차 설명]: 정렬된 검색 결과 목록을 반환합니다.
        # [2차 업무 설명]: 검색된 영수증 묶음을 손님에게 전달합니다.
        return filtered_list

    # ---------------------------------------------------------
    # 6단계: 거래 삭제(Delete) 및 수정(Update)
    # ---------------------------------------------------------
    # [1차 설명]: 거래 번호(ID)를 찾아 해당 영수증을 장부에서 파기합니다.
    # [2차 업무 설명]: 손님이 "아까 1234번 영수증 잘못 적었어요, 찢어버려 주세요!" 했을 때 장부에서 그 영수증만 쏙 빼서 버리는 업무입니다.
    def delete_transaction(self, tx_id: str) -> bool:
        # [1차 설명]: 장부의 모든 영수증을 리스트로 읽어옵니다.
        # [2차 업무 설명]: 창고에서 영수증들을 전부 꺼내옵니다.
        all_tx = list(self.repo.stream_transactions())
        # [1차 설명]: 삭제할 ID가 아닌 영수증들만 남겨서 새 리스트를 만듭니다.
        # [2차 업무 설명]: 지우려는 영수증 딱 1장만 쓰레기통에 버리고 나머지 영수증들만 모아둡니다.
        #마이: 모든 영수즈응ㄹ 들고와서 일일히 비교해서 유저가 준 번호와 같지 않은 번호의 영수증들만 살림.
        remaining_tx = [tx for tx in all_tx if tx.id != tx_id]
        # [1차 설명]: 삭제 전 개수와 남은 개수가 같다면 해당 ID가 장부에 없었다는 뜻입니다.
        # [2차 업무 설명]: 장부를 뒤졌는데 그런 번호표가 없었으면 삭제 실패(False)를 반환합니다.
        #마이: 같으면 안지운거니 폴수가, 다르면 지운거니 트루라는 논리
        if len(all_tx) == len(remaining_tx):
            # [1차 설명]: 실패(False)를 반환합니다.
            # [2차 업무 설명]: 지울 대상을 못 찾았다고 알립니다.
            return False
        # [1차 설명]: 살아남은 영수증들로 장부를 안전하게 다시 덮어씁니다.
        # [2차 업무 설명]: 그 영수증이 빠진 깨끗한 새 장부로 서랍을 교체합니다.
        self.repo.overwrite_transactions(remaining_tx)
        # [1차 설명]: 성공(True)을 반환합니다.
        # [2차 업무 설명]: 정상적으로 파기 완료되었음을 알립니다.
        return True

    # [1차 설명]: 거래 번호(ID)의 거래 내용을 새로운 내용으로 고쳐 씁니다.
    # [2차 업무 설명]: 영수증의 금액이나 날짜를 새 내용으로 빨간 펜으로 고쳐 적는 업무입니다.
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
        # [1차 설명]: 장부의 모든 거래 내역을 불러옵니다.
        # [2차 업무 설명]: 영수증들을 서랍에서 꺼냅니다.
        all_tx = list(self.repo.stream_transactions())
        # [1차 설명]: 수정하려는 번호(tx_id)를 가진 영수증을 찾습니다.
        # [2차 업무 설명]: 번호표가 일치하는 목표 영수증을 1장 쏙 뽑아옵니다.
        # 마이: 모든 영수증 들고와서 같은 아이디의 영수증을 찾아냄. 넥스트로 중복시에 1개만 꺼내오개했음. 넥스트 자체는 다음값인데 여기선 첫번쨰꺼 들고오는셈.
        target_tx = next((tx for tx in all_tx if tx.id == tx_id), None)
        # [1차 설명]: 대상 영수증을 찾지 못했는지 검사합니다.
        # [2차 업무 설명]: 그런 번호표가 장부에 없으면 고칠 수 없으므로 False를 돌려줍니다.
        if target_tx is None:
            # [1차 설명]: 실패(False)를 반환합니다.
            # [2차 업무 설명]: 해당 영수증이 없다고 안내합니다.
            #마이: 이건 수정 할걸 못찾아서 실패 계열
            return False

        # [1차 설명]: 새 날짜가 입력되었는지 확인합니다.
        # [2차 업무 설명]: 날짜를 바꾸고 싶어 하면 날짜를 검사합니다.
        #마이: 이건 수정할 내용을 잘못쓴계열
        #꺼내와서 바꾼게 아니라 해당위치의 내용을 바로 수정한 상황.
        if date_str is not None:
            # [1차 설명]: 날짜 형식 대조를 시도합니다.
            try:
                # [1차 설명]: 달력 형식에 맞는지 파싱합니다.
                datetime.strptime(date_str, "%Y-%m-%d")
            # [1차 설명]: 엉터리 날짜일 때 에러를 잡습니다.
            except ValueError:
                # [1차 설명]: 날짜 형식 오류를 던집니다.
                raise ValueError(f"수정할 날짜 형식이 올바르지 않습니다: '{date_str}'")
            # [1차 설명]: 영수증의 날짜를 새 날짜로 덮어씁니다.
            target_tx.date = date_str

        # [1차 설명]: 새 수입/지출 구분이 입력되었는지 확인합니다.
        if tx_type is not None:
            # [1차 설명]: income이나 expense가 맞는지 검사합니다.
            if tx_type not in ("income", "expense"):
                # [1차 설명]: 타입 오류를 던집니다.
                raise ValueError("거래 타입은 'income' 또는 'expense'여야 합니다.")
            # [1차 설명]: 영수증의 타입을 변경합니다.
            target_tx.type = tx_type  # type: ignore[assignment]

        # [1차 설명]: 새 카테고리가 입력되었는지 확인합니다.
        if category is not None:
            # [1차 설명]: 등록된 카테고리 명단을 불러옵니다.
            valid_cats = self.repo.load_categories()
            # [1차 설명]: 명단에 없는 엉뚱한 이름인지 검사합니다.
            if category not in valid_cats:
                # [1차 설명]: 미등록 카테고리 오류를 던집니다.
                raise ValueError(f"등록되지 않은 카테고리입니다: '{category}'")
            # [1차 설명]: 영수증의 카테고리를 변경합니다.
            target_tx.category = category

        # [1차 설명]: 새 금액이 입력되었는지 확인합니다.
        if amount is not None:
            # [1차 설명]: 금액이 0 이하인지 검사합니다.
            if amount <= 0:
                # [1차 설명]: 양수 금액 오류를 던집니다.
                raise ValueError("금액은 0보다 큰 양수 정수여야 합니다.")
            # [1차 설명]: 영수증의 금액을 변경합니다.
            target_tx.amount = amount

        # [1차 설명]: 새 메모가 입력되었는지 확인합니다.
        if memo is not None:
            # [1차 설명]: 영수증의 메모를 변경합니다.
            target_tx.memo = memo

        # [1차 설명]: 새 태그 목록이 입력되었는지 확인합니다.
        if tags is not None:
            # [1차 설명]: 영수증의 태그 목록을 변경합니다.
            target_tx.tags = tags

        # [1차 설명]: 수정이 완료된 영수증 묶음을 장부에 안전하게 덮어씁니다.
        # [2차 업무 설명]: 고쳐 쓴 내용으로 장부 책을 안전하게 새로 인쇄해 넣습니다.
        self.repo.overwrite_transactions(all_tx)
        # [1차 설명]: 성공(True)을 반환합니다.
        # [2차 업무 설명]: 수정이 잘 끝났음을 보고합니다.
        return True

    # ---------------------------------------------------------
    # 7단계: 카테고리 관리 (Category)
    # ---------------------------------------------------------
    # [1차 설명]: 현재 등록된 카테고리 목록을 확인합니다.
    # [2차 업무 설명]: 창고지기에게서 현재 사용 가능한 카테고리 명단("식비", "교통" 등)을 받아오는 업무입니다.
    def list_categories(self) -> List[str]:
        # [1차 설명]: 창고지기에게서 카테고리 목록을 로드하여 반환합니다.
        # [2차 업무 설명]: repo.load_categories()로 명단을 가져옵니다.
        return self.repo.load_categories()

    # [1차 설명]: 새로운 카테고리를 추가합니다.
    # [2차 업무 설명]: "반려동물", "취미" 같은 새로운 지출 분류 이름표를 하나 더 만드는 일입니다.
    def add_category(self, name: str) -> None:
        # [1차 설명]: 카테고리 이름 앞뒤의 공백을 제거합니다.
        # [2차 업무 설명]: 실수로 누른 스페이스바 빈칸을 지웁니다.
        clean_name = name.strip()
        # [1차 설명]: 이름이 비어있는지 확인합니다.
        # [2차 업무 설명]: 빈칸만 친 투명 이름표는 추가할 수 없으므로 거절합니다.
        if not clean_name:
            # [1차 설명]: 공백 불가 에러를 던집니다.
            raise ValueError("카테고리 이름은 공백일 수 없습니다.")

        # [1차 설명]: 기존에 등록된 카테고리 목록을 불러옵니다.
        # [2차 업무 설명]: 이미 있는 이름인지 대조해 보기 위해 명단을 확인합니다.
        cats = self.repo.load_categories()
        # [1차 설명]: 이미 등록된 카테고리인지 확인합니다.
        # [2차 업무 설명]: 똑같은 이름의 카테고리가 2개 생기면 안 되므로 중복을 거절합니다.
        if clean_name in cats:
            # [1차 설명]: 중복 카테고리 에러를 던집니다.
            raise ValueError(f"이미 등록되어 있는 카테고리입니다: '{clean_name}'")

        # [1차 설명]: 카테고리 명단에 새 이름을 추가합니다.
        # [2차 업무 설명]: 명단 맨 끝에 새 이름표를 꽂아 넣습니다.
        cats.append(clean_name)
        # [1차 설명]: 창고지기에게 새 명단을 안전하게 저장하라고 건넵니다.
        # [2차 업무 설명]: 갱신된 명단을 장부 파일에 저장합니다.
        self.repo.save_categories(cats)

    # [1차 설명]: 카테고리를 삭제합니다 (단, 이미 사용 중인 카테고리는 삭제를 막아 데이터를 보호합니다).
    # [2차 업무 설명]: '식비'로 쓴 영수증이 장부에 아직 남아있는데 '식비' 이름표를 지워버리면 고아 영수증이 되므로, 관련 영수증이 1장이라도 있으면 삭제를 절대 거절하는 안전 업무입니다.
    def remove_category(self, name: str) -> None:
        # [1차 설명]: 삭제할 이름의 공백을 다듬습니다.
        clean_name = name.strip()
        # [1차 설명]: 기존 카테고리 목록을 불러옵니다.
        cats = self.repo.load_categories()

        # [1차 설명]: 지우려는 카테고리가 명단에 없는지 확인합니다.
        # [2차 업무 설명]: 애초에 없는 카테고리는 지울 수 없으므로 거절합니다.
        if clean_name not in cats:
            # [1차 설명]: 미존재 카테고리 에러를 던집니다.
            raise ValueError(f"존재하지 않는 카테고리입니다: '{clean_name}'")

        # [1차 설명]: 장부를 뒤져서 이 카테고리를 쓴 영수증이 있는지 전수 조사합니다.
        # [2차 업무 설명]: 창고지기에게 영수증을 1장씩 받으며 이 이름표를 쓴 영수증이 있는지 수색합니다.
        for tx in self.repo.stream_transactions():
            # [1차 설명]: 영수증의 카테고리가 삭제하려는 이름과 같은지 확인합니다.
            # [2차 업무 설명]: 이 카테고리를 쓴 영수증이 발견되면 즉시 삭제를 거절합니다.
            #마이: 그냥 관련 거래 있으면 안 지워지게 해둔 조치.
            if tx.category == clean_name:
                # [1차 설명]: 사용 중인 카테고리 삭제 불가 에러를 던집니다.
                # [2차 업무 설명]: 영수증이 장부에 남아있으니 먼저 거래를 지우거나 수정하라고 안내합니다.
                raise ValueError(
                    f"카테고리 '{clean_name}'을(를) 사용 중인 거래 내역(ID: {tx.id} 등)이 존재합니다.\n"
                    f"관련 거래를 먼저 수정하거나 삭제한 후에 카테고리를 삭제할 수 있습니다."
                )

        # [1차 설명]: 명단에서 해당 카테고리 이름을 제거합니다.
        # [2차 업무 설명]: 사용 중이지 않은 깨끗한 상태이므로 안심하고 명단에서 뺍니다.
        cats.remove(clean_name)
        # [1차 설명]: 변경된 카테고리 명단을 장부에 안전하게 저장합니다.
        # [2차 업무 설명]: 새 명단을 파일에 저장합니다.
        self.repo.save_categories(cats)

    # ---------------------------------------------------------
    # 8단계: 예산(Budget) 및 요약(Summary)
    # ---------------------------------------------------------
    # [1차 설명]: 특정 월의 목표 예산을 설정합니다.
    # [2차 업무 설명]: "5월 목표 예산 50만 원" 카드를 작성하는 일입니다.
    def set_budget(self, month: str, amount: int) -> None:
        # [1차 설명]: 대상 월 문자열이 YYYY-MM 형식인지 검사합니다.
        try:
            # [1차 설명]: 달력 월 형식으로 파싱해 봅니다.
            datetime.strptime(month, "%Y-%m")
        # [1차 설명]: 형식이 틀렸을 때 에러를 잡습니다.
        except ValueError:
            # [1차 설명]: 월 형식 오류를 던집니다.
            raise ValueError(f"월 형식이 올바르지 않습니다: '{month}'. 'YYYY-MM' 형식이어야 합니다.")

        # [1차 설명]: 예산 금액이 0보다 큰 양수인지 확인합니다.
        if amount <= 0:
            # [1차 설명]: 양수 금액 오류를 던집니다.
            raise ValueError(f"예산 금액은 0보다 큰 양수 정수여야 합니다: {amount}")

        # [1차 설명]: 공식 Budget 객체를 만듭니다.
        # [2차 업무 설명]: 2026-05월 500,000원 공식 예산 카드를 작성합니다.
        budget = Budget(month=month, amount=amount)
        # [1차 설명]: 창고지기에게 예산 카드를 장부에 기록하라고 건넵니다.
        # [2차 업무 설명]: budgets.jsonl 파일에 예산 목표 카드를 저장합니다.
        self.repo.set_budget(budget)

    # [1차 설명]: 해당 월의 수입, 지출, 잔액, 지출 상위 카테고리 TOP N을 계산하여 결산 리포트를 만듭니다.
    # [2차 업무 설명]: 한 달이 끝나면 계산기를 두드려 "총수입 300만 원, 총지출 120만 원, 잔액 180만 원!"을 계산하고, 가장 돈을 많이 쓴 카테고리 1, 2, 3위 순위를 매겨 성적표를 만드는 업무입니다.
    def get_monthly_summary(self, month: str, top_n: int = 3) -> Optional[Dict[str, Any]]:
        # [1차 설명]: 대상 월이 올바른 형식인지 검사합니다.
        try:
            # [1차 설명]: YYYY-MM 날짜로 맞추어봅니다.
            datetime.strptime(month, "%Y-%m")
        # [1차 설명]: 잘못된 형식일 때 에러를 잡습니다.
        except ValueError:
            # [1차 설명]: 월 형식 오류를 던집니다.
            raise ValueError(f"월 형식이 올바르지 않습니다: '{month}'. 'YYYY-MM' 형식이어야 합니다.")

        # [1차 설명]: top_n이 1 이상인지 검사합니다.
        # [2차 업무 설명]: 지출 1위부터 보여줘야 하므로 0 이하는 거절합니다.
        if top_n <= 0:
            # [1차 설명]: 1 이상이어야 한다는 오류를 던집니다.
            raise ValueError(f"--top 옵션 값은 1 이상이어야 합니다: {top_n}")

        # [1차 설명]: 총수입 합계 누적 변수를 0원으로 초기화합니다.
        total_income = 0
        # [1차 설명]: 총지출 합계 누적 변수를 0원으로 초기화합니다.
        total_expense = 0
        # [1차 설명]: 카테고리별 지출을 담을 자동 0원 딕셔너리 바구니를 만듭니다.
        # [2차 업무 설명]: 식비, 교통 등 새 이름이 나오면 0원부터 더할 수 있게 준비합니다.
        category_expenses: Dict[str, int] = defaultdict(int)
        # [1차 설명]: 해당 월에 거래가 1건이라도 있었는지 체크하는 깃발 변수입니다.
        has_data = False

        # [1차 설명]: 장부의 영수증들을 하나씩 순회하며 계산합니다.
        # [2차 업무 설명]: 회전초밥 레일에서 영수증을 1장씩 꺼내어 계산기에 두드립니다.
        for tx in self.repo.stream_transactions():
            # [1차 설명]: 영수증의 날짜가 해당 월(예: 2026-05)로 시작하는지 확인합니다.
            # [2차 업무 설명]: 이번 달 영수증이 맞는지 검사합니다.
            if tx.date.startswith(month):
                # [1차 설명]: 거래가 발견되었으므로 깃발을 True로 올립니다.
                has_data = True
                # [1차 설명]: 수입이면 총수입에 돈을 더합니다.
                # [2차 업무 설명]: 지갑으로 들어온 돈을 총수입에 누적합니다.
                if tx.type == "income":
                    total_income += tx.amount
                # [1차 설명]: 지출이면 총지출에 더하고, 해당 카테고리 바구니에도 돈을 누적합니다.
                # [2차 업무 설명]: 밖으로 나간 돈을 총지출과 해당 분류 바구니에 동시에 더합니다.
                elif tx.type == "expense":
                    total_expense += tx.amount
                    category_expenses[tx.category] += tx.amount

        # [1차 설명]: 그 달에 거래 데이터가 단 1건도 없었는지 확인합니다.
        if not has_data:
            # [1차 설명]: 데이터가 없으므로 None을 반환합니다.
            # [2차 업무 설명]: 거래가 없다고 빈손으로 돌아갑니다.
            return None

        # [1차 설명]: 돈을 가장 많이 쓴 순서대로 카테고리를 정렬하여 1위부터 TOP N위를 자릅니다.
        # [2차 업무 설명]: 지출 금액이 큰 순서대로 내림차순 정렬하여 상위 top_n개만 골라냅니다.
        sorted_top_categories: List[Tuple[str, int]] = sorted(
            category_expenses.items(), key=lambda item: item[1], reverse=True
        )[:top_n]

        # [1차 설명]: 창고지기에게서 그 달의 목표 예산 카드를 찾아옵니다.
        # [2차 업무 설명]: 설정해둔 한도 예산 카드를 꺼내옵니다.
        budget = self.repo.get_budget(month)

        # [1차 설명]: 수입, 지출, 잔액, 랭킹, 예산 정보가 담긴 최종 요약 성적표를 반환합니다.
        # [2차 업무 설명]: 한 달 결산 리포트 묶음을 만들어 손님에게 건네줍니다.
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
    # [1차 설명]: 거래 내역을 엑셀용 CSV 파일로 인쇄하여 내보냅니다.
    # [2차 업무 설명]: 장부 내용을 엑셀 서류로 예쁘게 출력해서 손님 손에 쥐여주는 업무입니다.
    def export_transactions_csv(
        self,
        out_path: str,
        month: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> int:
        # [1차 설명]: 월 단위 옵션이 들어왔다면 시작일(01일)과 종료일(31일)로 변환합니다.
        if month:
            from_date = f"{month}-01"
            to_date = f"{month}-31"

        # [1차 설명]: 시작일과 종료일이 둘 다 채워졌는지 검사합니다.
        # [2차 업무 설명]: 기간이 없으면 엑셀로 뽑을 범위를 알 수 없으므로 거절합니다.
        if not from_date or not to_date:
            # [1차 설명]: 기간 조건 필수 오류를 던집니다.
            raise ValueError("내보내기를 수행하려면 '--month YYYY-MM' 또는 '--from과 --to' 조건을 반드시 지정해야 합니다.")

        # [1차 설명]: 저장할 경로의 폴더 이름을 알아냅니다.
        out_dir = os.path.dirname(out_path)
        # [1차 설명]: 폴더가 지정되어 있고 아직 없다면 새로 만듭니다.
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        # [1차 설명]: 내보낸 거래 영수증 숫자를 셀 카운터 변수입니다.
        exported_count = 0
        # [1차 설명]: 출력할 CSV 파일을 쓰기 모드로 엽니다.
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            # [1차 설명]: CSV 파일 작성기를 만듭니다.
            writer = csv.writer(f)
            # [1차 설명]: 표의 맨 첫 줄 제목(열 이름)들을 씁니다.
            writer.writerow(["date", "type", "category", "amount", "memo", "tags"])

            # [1차 설명]: 장부의 영수증들을 하나씩 순회합니다.
            for tx in self.repo.stream_transactions():
                # [1차 설명]: 영수증 날짜가 지정된 기간 범위 안에 들어오는지 확인합니다.
                if from_date <= tx.date <= to_date:
                    # [1차 설명]: 태그 리스트를 쉼표로 연결한 글자로 만듭니다.
                    tags_str = ",".join(tx.tags) if tx.tags else ""
                    # [1차 설명]: 영수증 1행을 CSV 파일에 기록합니다.
                    writer.writerow([tx.date, tx.type, tx.category, tx.amount, tx.memo, tags_str])
                    # [1차 설명]: 기록 건수를 1 증가시킵니다.
                    exported_count += 1

        # [1차 설명]: 최종 내보내기 성공한 거래 건수를 반환합니다.
        return exported_count

    # [1차 설명]: 외부 CSV 파일을 읽어 들여 가계부 장부에 일괄 등록합니다.
    # [2차 업무 설명]: 카드사에서 다운로드받은 엑셀 내역서를 가계부 장부로 일괄 흡수하여 등록하는 업무입니다.
    def import_transactions_csv(self, file_path: str) -> int:
        # [1차 설명]: 읽어올 CSV 파일이 진짜 존재하는지 검사합니다.
        # [2차 업무 설명]: 파일이 없으면 읽을 수 없으므로 거절합니다.
        if not os.path.exists(file_path):
            # [1차 설명]: 파일 없음 오류를 던집니다.
            raise FileNotFoundError(f"가져올 CSV 파일이 존재하지 않습니다: '{file_path}'")

        # [1차 설명]: 가져오기 성공한 거래 건수를 셀 카운터 변수입니다.
        imported_count = 0
        # [1차 설명]: CSV 파일에 반드시 있어야 할 필수 열 이름들의 집합입니다.
        required_columns = {"date", "type", "category", "amount"}

        # [1차 설명]: 외부 CSV 파일을 읽기 모드로 엽니다.
        with open(file_path, "r", encoding="utf-8") as f:
            # [1차 설명]: 각 행을 딕셔너리로 읽어주는 CSV 리더기를 준비합니다.
            reader = csv.DictReader(f)

            # [1차 설명]: 첫 줄 헤더가 비어있거나 필수 열이 빠져있는지 검사합니다.
            # [2차 업무 설명]: 날짜, 구분, 카테고리, 금액 칸이 없는 엉뚱한 엑셀 파일인지 확인합니다.
            if not reader.fieldnames or not required_columns.issubset(set(reader.fieldnames)):
                cols_str = ", ".join(required_columns)
                # [1차 설명]: 스키마 누락 에러를 던집니다.
                raise ValueError(f"CSV 스키마 오류: 필수 헤더 컬럼({cols_str})이 누락되었습니다.")

            # [1차 설명]: 2번째 줄(데이터 첫 행)부터 번호를 매기며 한 행씩 읽습니다.
            for row_idx, row in enumerate(reader, start=2):
                # [1차 설명]: 날짜 글자를 꺼내고 공백을 제거합니다.
                date_val = row.get("date", "").strip()
                # [1차 설명]: 수입/지출 글자를 꺼내고 공백을 제거합니다.
                type_val = row.get("type", "").strip()
                # [1차 설명]: 카테고리 글자를 꺼내고 공백을 제거합니다.
                cat_val = row.get("category", "").strip()
                # [1차 설명]: 금액 문자열을 꺼내고 공백을 제거합니다.
                amount_raw = row.get("amount", "").strip()
                # [1차 설명]: 메모 글자를 꺼내고 공백을 제거합니다.
                memo_val = row.get("memo", "").strip()
                # [1차 설명]: 태그 글자를 꺼내고 공백을 제거합니다.
                tags_raw = row.get("tags", "").strip()

                # [1차 설명]: 금액이 진짜 숫자로 바뀌는지 검사를 시도합니다.
                try:
                    # [1차 설명]: 금액 글자를 정수 숫자로 변환합니다.
                    amount_val = int(amount_raw)
                # [1차 설명]: 금액 칸에 문자가 적혀있어 변환에 실패했을 때를 잡습니다.
                except ValueError:
                    # [1차 설명]: 몇 번째 행의 금액이 잘못되었는지 오류를 던집니다.
                    raise ValueError(f"[행 {row_idx}] 금액은 양수 정수여야 합니다: '{amount_raw}'")

                # [1차 설명]: 태그를 쉼표로 잘라 리스트로 만듭니다.
                tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()]

                # [1차 설명]: 회계사의 거래 생성 함수를 호출하여 장부에 등록을 시도합니다.
                try:
                    # [1차 설명]: 검증과 번호표 발급을 거쳐 장부에 기록합니다.
                    self.create_transaction(
                        date_str=date_val,
                        tx_type=type_val,
                        category=cat_val,
                        amount=amount_val,
                        memo=memo_val,
                        tags=tags_list,
                    )
                    # [1차 설명]: 등록 성공 건수를 1 올립니다.
                    imported_count += 1
                # [1차 설명]: 날짜나 카테고리 등에서 검증 에러가 났을 때 처리합니다.
                except ValueError as ve:
                    # [1차 설명]: 몇 번째 행에서 무슨 데이터 오류가 났는지 구체적으로 안내합니다.
                    raise ValueError(f"[행 {row_idx} 데이터 오류] {ve}")

        # [1차 설명]: 최종 반영된 총 거래 건수를 반환합니다.
        return imported_count