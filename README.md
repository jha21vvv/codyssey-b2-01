# 1. 파일구조

'''
budget_app/
├── __init__.py
├── __main__.py          # python -m budget_app 진입점
├── models.py            # 데이터 모델 (dataclass)
├── decorators.py        # 공통 관심사 데코레이터
├── repositories.py      # 파일 I/O 및 스트리밍 제너레이터
├── services.py          # 비즈니스 로직
└── cli.py               # argparse CLI 인터페이스
'''

# 2.
# 콘솔 가계부 애플리케이션 (`budget_app`)

순수 Python 3.10+ 표준 라이브러리만을 활용하여 구축한 파일 기반의 견고한 CLI 가계부 서비스입니다.  
대용량 데이터 환경에서도 안정적으로 동작하도록 **제너레이터 스트리밍 파이프라인**, **원자적 파일 쓰기(Atomic Replace)**, **계층화 아키텍처(Layered Architecture)**를 적용했습니다.

---

## 1. 프로젝트 아키텍처 (계층 분리)

단일 책임 원칙(SRP)에 따라 역할을 명확히 분리한 4계층 구조로 설계되었습니다:

- **모델 (`models.py`)**: `dataclass` 기반 거래(`Transaction`), 예산(`Budget`) 데이터 구조 및 불변 유효성 검증
- **저장소 (`repositories.py`)**: JSONL 파일 영구 저장, `yield` 기반 라인 스트리밍 I/O, 원자적 교체(`os.replace`)를 통한 데이터 손상 방지
- **서비스 (`services.py`)**: 거래 CRUD, 복합 조건 검색, 월별 수지 집계, 예산 초과 계산, 카테고리 참조 무결성 검증, CSV 처리
- **CLI 프레젠테이션 (`cli.py`, `decorators.py`)**: `argparse` 기반 명령어/옵션 파싱, 대화형(`input()`) 순차 입력, 스택트레이스를 차단하고 종료 코드(`exit code 1`)를 제어하는 에러 핸들러

---

## 2. 데이터 저장 정책 및 포맷

- **저장 위치**: `./data/` (명령 실행 시 `--data-dir <경로>` 옵션으로 자유롭게 변경 가능)
- **저장 포맷**: 라인 단위 JSONL (UTF-8 인코딩)
- **분리 저장되는 3대 영구 파일**:
  1. `transactions.jsonl`: 전체 수입 및 지출 거래 내역[cite: 1]
  2. `categories.jsonl`: 등록된 카테고리 명단 (최초 실행 시 기본 카테고리 자동 시딩)[cite: 1]
  3. `budgets.jsonl`: 월별 설정 예산 데이터[cite: 1]

---

## 3. 실행 방법 및 주요 명령어 가이드

### 공통 옵션 및 도움말 확인
모든 명령어는 리눅스 표준인 `--` 접두사를 사용하며, `--help`를 통해 상세 설명을 확인할 수 있습니다[cite: 1].


**구현 요건 최종 점검**

* **책임 분리 아키텍처**: Model, Repository, Service, CLI, Decorator가 최소 3개 이상(총 6개)의 모듈로 분리되었습니다[cite: 1].
* **CLI 표준 규약 준수**: 모든 플래그가 `--` 형태로 일원화되었으며, `--help` 동작이 자동 구성되었습니다[cite: 1].
* **패키지 진입점 완성**: `python -m budget_app` 호출 시 `__main__.py` $\rightarrow$ `cli.py` $\rightarrow$ `@handle_cli_errors` 순으로 제어 흐름이 이어져 안전한 종료와 직관적인 오류 메시지를 보장합니다[cite: 1].
* **문서화 요건 완료**: 실행 명령, 파일 저장 정책, CSV 스키마 테이블을 포함하는 `README.md`가 완비되었습니다[cite: 1].
```bash
# 전체 명령어 도움말
python -m budget_app --help

# 특정 하위 명령어 도움말 (예: search)
python -m budget_app search --help
```

```bash
프로젝트 초기 폴더 구성부터 모든 기능(10개)을 순차적으로 테스트하고 검증할 수 있는 터미널 명령어 전체 흐름입니다.

---

**0. 환경 준비 및 디렉터리 세팅**

터미널을 열고 코드가 들어있는 `budget_app` 패키지 바로 바깥(상위 폴더) 위치에서 실행합니다.

```bash
# 1. 파이썬 버전 확인 (3.10 이상 필수)
python --version

# 2. 패키지 도움말 및 전체 커맨드 목록 확인
python -m budget_app --help

```

---

**1. 거래 추가 (`add`) - 대화형 입력**

프롬프트를 실행하면 6단계 질문이 순차적으로 나타납니다.

```bash
python -m budget_app add

```

* **터미널 입력 예시**:
* `1. 날짜 (YYYY-MM-DD):` `2026-05-01`
* `2. 타입 (income/expense):` `expense`
* `3. 카테고리:` `식비`
* `4. 금액 (양수 정수):` `12000`
* `5. 메모 (선택 사항, 없으면 Enter):` `점심 김치찌개`
* `6. 태그 (선택 사항, 쉼표로 구분):` `외식,점심`
* *출력: 거래가 성공적으로 저장되었습니다. (생성된 ID: `a1b2c3d4`)*




*(몇 가지 테스트 데이터를 더 추가해 둡니다)*

```bash
# 수입 등록
python -m budget_app add
# (날짜: 2026-05-10, 타입: income, 카테고리: 급여, 금액: 3500000, 메모: 5월 월급, 태그: 월급)

# 추가 지출 등록
python -m budget_app add
# (날짜: 2026-05-15, 타입: expense, 카테고리: 교통, 금액: 1500, 메모: 지하철 이용, 태그: 출근)

```

---

**2. 거래 목록 조회 (`list`)**

최신순(날짜 역순)으로 정렬되어 출력됩니다.

```bash
# 기본값(최대 10건) 조회
python -m budget_app list

# 건수 제한 옵션 (--limit N)
python -m budget_app list --limit 2

```

---

**3. 거래 조건 검색 (`search`)**

모든 옵션은 조합해서 사용할 수 있습니다.

```bash
# 기간 검색 (--from, --to)
python -m budget_app search --from 2026-05-01 --to 2026-05-10

# 카테고리 일치 검색 (--category)
python -m budget_app search --category 식비

# 수입/지출 타입 필터링 (--type)
python -m budget_app search --type income

# 메모 키워드 검색 (--q)
python -m budget_app search --q 김치찌개

# 태그 검색 (--tag)
python -m budget_app search --tag 외식

# 여러 조건 동시 검색
python -m budget_app search --category 식비 --type expense --q 점심

```

---

**4. 거래 수정 (`update`)**

수정할 대상의 `id`를 지정하고, 바꾸려는 필드만 옵션으로 전달합니다. (여기서 `a1b2c3d4`는 실제 발급된 ID로 변경하세요.)

```bash
# 금액과 메모만 수정
python -m budget_app update --id a1b2c3d4 --amount 13000 --memo "점심 특식"

# 날짜와 카테고리 수정
python -m budget_app update --id a1b2c3d4 --date 2026-05-02 --category 식비

```

---

**5. 거래 삭제 (`delete`)**

```bash
# 특정 ID 삭제
python -m budget_app delete --id a1b2c3d4

# 없는 ID 입력 시 안전 처리 확인
python -m budget_app delete --id nonexistent_id

```

---

**6. 카테고리 관리 (`category`)**

```bash
# 1. 등록된 전체 카테고리 목록 확인
python -m budget_app category list

# 2. 새 카테고리 추가
python -m budget_app category add 문화생활

# 3. 중복 추가 차단 검증 (에러 메시지 및 종료 코드 1 확인)
python -m budget_app category add 문화생활

# 4. 미사용 카테고리 삭제
python -m budget_app category remove 문화생활

# 5. 기존 거래에서 사용 중인 카테고리 삭제 시도 (참조 무결성 차단 검증)
python -m budget_app category remove 식비

```

---

**7. 예산 설정 (`budget`) 및 월별 요약 (`summary`)**

```bash
# 1. 2026년 5월 예산 500,000원으로 설정
python -m budget_app budget set --month 2026-05 --amount 500000

# 2. 2026년 5월 가계부 요약 리포트 조회 (기본 상위 3개 카테고리)
python -m budget_app summary --month 2026-05

# 3. 상위 카테고리 개수 변경 옵션 (--top)
python -m budget_app summary --month 2026-05 --top 5

# 4. 거래 내역이 없는 달 조회 (데이터 없음 안내 확인)
python -m budget_app summary --month 2020-01

```

---

**8. CSV 내보내기 (`export`) 및 가져오기 (`import`)**

```bash
# 1. 월 지정 내보내기 (UTF-8, 헤더 포함 고정)
python -m budget_app export --out ./may_backup.csv --month 2026-05

# 2. 기간 지정 내보내기
python -m budget_app export --out ./q2_backup.csv --from 2026-04-01 --to 2026-06-30

# 3. CSV 파일로부터 거래 내역 일괄 가져오기
python -m budget_app import --from ./may_backup.csv

```

---

**9. 저장 데이터 디렉터리 변경 옵션 (`--data-dir`)**

모든 커맨드 앞이나 뒤에 `--data-dir`를 붙이면 기본 `./data` 대신 다른 폴더를 사용할 수 있습니다.

```bash
# test_data 폴더를 저장소로 사용하여 목록 조회
python -m budget_app --data-dir ./test_data list

# test_data 폴더에 6월 예산 설정
python -m budget_app --data-dir ./test_data budget set --month 2026-06 --amount 1000000

```
## 안전 저장 과정 설명
좋아요. 물리적으로는 “같은 파일 경로를 덮어쓰는 것”이 아니라, “새 파일을 완성한 뒤 그 경로를 새 파일 쪽으로 가리키게 바꾸는 것”이에요.

단계별로 보면:

1. 메모리 버퍼에 데이터가 쌓임
- `tf.write(...)`는 하드디스크에 바로 가는 게 아니라
- Python이 관리하는 메모리 버퍼에 문자열을 적어둠
- 이건 “메모리 안의 임시 저장소”에 넣는 것

2. `flush()`
- 이때 `flush()`는
  “메모리 버퍼 안에 남아 있는 내용을 운영체제(OS) 쪽 파일 버퍼로 넘겨줘”
- 즉, 프로그램 메모리 → OS cache로 이동
- 아직 하드디스크까지 간 건 아니지만, 이제 파일 시스템이 관리하는 영역으로 옮긴 상태

3. `fsync()`
- 이건
  “OS가 가진 캐시(페이지 캐시)를 강제로 디스크로 내려줘”
- 실제로 하드디스크/SSD에 쓰기 완료를 보장
- 그래서 갑자기 전원 끊겨도 파일이 깨지지 않게 됨

4. `temp_path`와 `self.tx_file`은 서로 다른 경로
- 예:
  - transactions.jsonl (원본)
  - `/data/tmpabcd1234` (임시 파일)
- 둘은 서로 다른 파일 공간에 저장될 수 있음
- 즉, “같은 파일을 덮어쓰기”가 아니라 “새 파일을 만들고 그 다음 경로 연결을 바꾸는 방식”

5. `os.replace(temp_path, self.tx_file)`의 물리적 의미
- 이 함수는 파일 시스템의 디렉터리 엔트리를 바꾸는 작업
- 디렉터리(폴더)는
  - 파일 이름 → 실제 파일 위치(인덱스/블록 주소)
  를 연결해주는 표 같은 역할을 함
- 원래는:
  - `transactions.jsonl` → old_inode
- 새로는:
  - `transactions.jsonl` → new_inode
- 즉, 경로 이름이 가리키는 대상만 새 파일로 바뀌는 것
- 그래서 사용자는 마치 “덮어썼다”처럼 보이지만, 실제로는 “경로를 새 파일로 교체”한 것

간단한 그림:

Before:
- `transactions.jsonl` -> old file data
- `tmpabcd1234` -> new file data

After `os.replace(...)`:
- `transactions.jsonl` -> new file data
- old file data는 거의 그대로 남아 있거나, 이후 정리됨
- 사용자 입장에서는 원본 파일이 새 내용으로 바뀐 것처럼 보임

왜 안전하냐?
- 원본 파일이 완전히 새 내용으로 덮어써지는 순간이 아니라
- 새 파일이 완전히 준비된 뒤에 경로 연결만 바꾸기 때문에
- 중간 상태가 드러나지 않음
- 이것을 “atomic replace”라고 부름

즉:
- “같은 파일을 직접 수정 중에 깨뜨리는 것”이 아니라
- “완성된 새 버전 파일을 먼저 만들고 경로만 전환”
- 그래서 파일 손상 위험이 적음

핵심만 말하면:

- `flush` = 메모리 버퍼 → OS 버퍼
- `fsync` = OS 버퍼 → 디스크
- `os.replace` = 경로가 가리키는 대상만 새 파일로 스위치
- 그래서 서로 저장 위치가 달라도 “원본 자리에 새 파일이 들어온 것처럼” 보이는 것

비유로 하면:

- 원본 파일은 문서철
- 임시 파일은 새로 작성한 수정본
- `os.replace`는 문서철 표지에 “새 수정본”으로 라벨을 교체하는 것
- 표지만 바꾸고, 문서철 자체는 같은 위치에 있음

원하시면 다음으로
- “디렉터리 엔트리/inode”를 실제 파일 구조 관점으로 그림으로 더 자세히
- 아니면 “flush/fsync/replace가 왜 꼭 필요한지”를 트랜잭션 관점으로
같이 설명해줄게.

- Python이 관리하던 버퍼 = Python의 파일 객체 내부 버퍼, 보통 프로그램 메모리(RAM)에 있음
- OS 캐시 = 운영체제가 디스크 작업을 빠르게 하려고 보관하는 RAM 영역
- 디스크 = 실제 저장 장치(SSD/HDD)