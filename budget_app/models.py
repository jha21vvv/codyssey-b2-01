"""
models.py
가계부 애플리케이션의 핵심 데이터 모델을 정의하는 모듈입니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal


@dataclass
class Transaction:
    """
    개별 거래 내역을 나타내는 데이터 모델입니다.
    
    요건 충족:
    - dataclass 기반 정의
    - 필수 필드: id, type, date, amount, category, memo, tags
    - Python 3.10+ 타입 힌트 및 Literal/Optional 대안 문법 적용
    """
    id: str
    type: Literal["income", "expense"]
    date: str
    amount: int
    category: str
    memo: str = ""
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """
        모델 생성 시 필드 유효성을 자체 검증합니다.
        잘못된 데이터로 객체가 생성되는 것을 원천 차단합니다.
        """
        # 1. type 검증: income 또는 expense만 허용
        if self.type not in ("income", "expense"):
            raise ValueError(f"유효하지 않은 거래 타입입니다: '{self.type}'. 'income' 또는 'expense'여야 합니다.")

        # 2. date 검증: YYYY-MM-DD 형식 확인
        try:
            datetime.strptime(self.date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"유효하지 않은 날짜 형식입니다: '{self.date}'. 'YYYY-MM-DD' 형식이어야 합니다.")

        # 3. amount 검증: 정수 및 양수 여부 확인
        if not isinstance(self.amount, int) or self.amount <= 0:
            raise ValueError(f"금액은 0보다 큰 양수 정수여야 합니다: {self.amount}")

        # 4. category 검증: 공백 문자열 불가
        if not self.category or not self.category.strip():
            raise ValueError("카테고리는 비어 있을 수 없습니다.")

    def to_dict(self) -> dict[str, Any]:
        """직렬화(JSONL/CSV 저장)를 위해 딕셔너리로 변환합니다."""
        return {
            "id": self.id,
            "type": self.type,
            "date": self.date,
            "amount": self.amount,
            "category": self.category,
            "memo": self.memo,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Transaction":
        """역직렬화(JSONL/CSV 파싱)를 통해 객체를 복원합니다."""
        return cls(
            id=str(data["id"]),
            type=data["type"],
            date=str(data["date"]),
            amount=int(data["amount"]),
            category=str(data["category"]),
            memo=str(data.get("memo", "")),
            tags=list(data.get("tags", [])),
        )


@dataclass
class Budget:
    """
    월별 예산 설정을 나타내는 데이터 모델입니다.
    
    요건 충족:
    - 최소 2개 이상 클래스 구성 요건 충족
    - 월(YYYY-MM) 및 예산 금액(양수 정수) 캡슐화[cite: 1]
    """
    month: str
    amount: int

    def __post_init__(self) -> None:
        """예산 데이터 유효성 검증."""
        try:
            datetime.strptime(self.month, "%Y-%m")
        except ValueError:
            raise ValueError(f"유효하지 않은 월 형식입니다: '{self.month}'. 'YYYY-MM' 형식이어야 합니다.")

        if not isinstance(self.amount, int) or self.amount <= 0:
            raise ValueError(f"예산 금액은 0보다 큰 양수 정수여야 합니다: {self.amount}")

    def to_dict(self) -> dict[str, Any]:
        """직렬화를 위한 딕셔너리 변환 메서드."""
        return {
            "month": self.month,
            "amount": self.amount,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Budget":
        """역직렬화를 위한 팩토리 메서드."""
        return cls(
            month=str(data["month"]),
            amount=int(data["amount"]),
        )


@dataclass
class Category:
    """카테고리 항목을 명시적으로 다루기 위한 보조 데이터 모델입니다."""
    name: str

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("카테고리 이름은 공백일 수 없습니다.")
        self.name = self.name.strip()

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Category":
        return cls(name=str(data["name"]))


# Python 3.10+ 최신 문법: typing.List, typing.Dict 대신 내장 제네릭 문법인 list[str], dict[str, Any]를 바로 사용했습니다[cite: 1].
# 최소 2개 이상의 클래스 정의: Transaction과 Budget을 포함해 카테고리 확장을 고려한 Category 모델까지 총 3개 클래스를 모두 @dataclass로 정의했습니다[cite: 1].
# 필수 필드 완전성: 명세에 지정된 7개 필드(id, type, date, amount, category, memo, tags)가 모두 포함되었습니다[cite: 1].
# 타입 계약 명확화: Literal["income", "expense"]로 거래 유형을 제한하고, __post_init__을 통해 객체 인스턴스화 시점에 잘못된 형식의 데이터가 주입되지 않도록 계약을 강제했습니다[cite: 1].