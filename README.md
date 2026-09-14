# 콘솔 가계부 앱

Python 3.10+ 기반의 파일 저장형 가계부 CLI 프로젝트입니다.

이 앱은 터미널에서 다음 작업을 수행합니다.

- 거래 추가 / 수정 / 삭제
- 조건 검색
- 월별 요약
- 예산 설정 및 비교
- 카테고리 관리
- CSV import / export
- JSONL 기반 영구 저장

---

## 1. 프로젝트 구조

```text
budget_app/
├── __init__.py
├── __main__.py          # python -m budget_app 진입점
├── cli.py               # argparse 기반 CLI
├── decorators.py        # 공통 관심사 데코레이터
├── models.py            # 데이터 모델
├── repositories.py      # 파일 I/O 및 저장소 로직
├── services.py          # 비즈니스 로직
├── data/                # 기본 저장 폴더
│   ├── transactions.jsonl
│   ├── categories.jsonl
│   └── budgets.jsonl
├── test_data/           # 샘플 데이터
│   ├── transactions.jsonl
│   ├── categories.jsonl
│   └── budgets.jsonl
├── README.md
├── may_backup.csv
├── q2_backup.csv
└── ...
```

---

## 2. 실행 방법

프로젝트 루트에서 아래 명령을 실행합니다.

```bash
# 전체 도움말
python -m budget_app --help

# 특정 명령 도움말
python -m budget_app search --help
python -m budget_app category --help
```

공통 옵션:

```bash
python -m budget_app --data-dir ./data list
```

- `--data-dir PATH`: 데이터 저장 디렉터리를 지정합니다.
- 기본값: `./data`

---

## 3. 명령어 요약

### 기본 명령

| 명령 | 설명 | 주요 옵션 |
| --- | --- | --- |
| `add` | 거래 추가 | 없음(대화형 입력) |
| `list` | 최신 거래 조회 | `--limit` |
| `search` | 조건 기반 검색 | `--from`, `--to`, `--category`, `--type`, `--q`, `--tag` |
| `delete` | 거래 삭제 | `--id` |
| `update` | 거래 수정 | `--id`, `--date`, `--type`, `--category`, `--amount`, `--memo`, `--tags` |
| `category` | 카테고리 관리 | `list`, `add`, `remove` |
| `budget` | 예산 설정 | `set --month --amount` |
| `summary` | 월별 요약 리포트 | `--month`, `--top` |
| `export` | CSV 내보내기 | `--out`, `--month`, `--from`, `--to` |
| `import` | CSV 불러오기 | `--from` |

### 세부 설명

#### `add`
거래를 대화형으로 추가합니다.

- 입력 항목: 날짜, 타입, 카테고리, 금액, 메모, 태그
- 타입: `income` 또는 `expense`
- 카테고리는 미리 등록된 값이어야 합니다.

```bash
python -m budget_app add
```

#### `list`
최신 거래를 조회합니다.

```bash
python -m budget_app list
python -m budget_app list --limit 20
```

- `--limit N`: 출력할 최대 거래 개수
- 기본값: `10`

#### `search`
여러 조건으로 거래를 검색합니다.

```bash
python -m budget_app search --from 2026-09-01 --to 2026-09-30
python -m budget_app search --category 식비
python -m budget_app search --type expense
python -m budget_app search --q 점심
python -m budget_app search --tag 외식
```

옵션:
- `--from YYYY-MM-DD`: 시작일
- `--to YYYY-MM-DD`: 종료일
- `--category NAME`: 카테고리 필터
- `--type {income,expense}`: 수입/지출 필터
- `--q KEYWORD`: 메모 키워드 검색
- `--tag TAG`: 태그 포함 검색

#### `delete`
특정 거래를 삭제합니다.

```bash
python -m budget_app delete --id a1b2c3d4
```

- `--id ID` (필수)
- 존재하지 않는 ID는 안내 메시지를 출력합니다.

#### `update`
특정 거래를 수정합니다.

```bash
python -m budget_app update --id a1b2c3d4 --amount 15000 --memo "점심 특식"
python -m budget_app update --id a1b2c3d4 --date 2026-09-02 --category 식비
```

옵션:
- `--id ID` (필수)
- `--date YYYY-MM-DD`
- `--type {income,expense}`
- `--category NAME`
- `--amount N`
- `--memo TEXT`
- `--tags "tag1,tag2"`

#### `category`
카테고리를 관리합니다.

```bash
python -m budget_app category list
python -m budget_app category add 문화생활
python -m budget_app category remove 문화생활
```

하위 명령:
- `list`: 전체 카테고리 목록 보기
- `add NAME`: 새 카테고리 추가
- `remove NAME`: 카테고리 삭제

#### `budget`
월별 예산을 설정합니다.

```bash
python -m budget_app budget set --month 2026-09 --amount 500000
```

옵션:
- `--month YYYY-MM` (필수)
- `--amount N` (필수)

#### `summary`
월별 수입/지출 요약을 보여줍니다.

```bash
python -m budget_app summary --month 2026-09
python -m budget_app summary --month 2026-09 --top 5
```

옵션:
- `--month YYYY-MM` (필수)
- `--top N`: 지출 상위 카테고리 수, 기본값 `3`

출력 항목:
- 총 수입
- 총 지출
- 잔액
- 지출 상위 카테고리 TOP N
- 설정된 예산이 있으면 사용률과 초과 여부도 함께 표시

#### `export`
CSV 파일로 거래를 내보냅니다.

```bash
python -m budget_app export --out ./may_backup.csv --month 2026-09
python -m budget_app export --out ./q2_backup.csv --from 2026-07-01 --to 2026-09-30
```

옵션:
- `--out PATH` (필수)
- `--month YYYY-MM`
- `--from YYYY-MM-DD`
- `--to YYYY-MM-DD`

#### `import`
CSV 파일에서 거래를 일괄 불러옵니다.

```bash
python -m budget_app import --from ./may_backup.csv
```

옵션:
- `--from PATH` (필수): 불러올 CSV 파일 경로

---

## 4. 사용 예시

아래는 전체 흐름을 한 번에 보는 예시입니다.

```bash
# 1) 전체 도움말
python -m budget_app --help

# 2) 거래 추가
python -m budget_app add

# 3) 목록 조회
python -m budget_app list --limit 10

# 4) 검색
python -m budget_app search --category 식비 --type expense

# 5) 월별 요약
python -m budget_app summary --month 2026-09 --top 3

# 6) 예산 설정
python -m budget_app budget set --month 2026-09 --amount 500000

# 7) CSV 내보내기
python -m budget_app export --out ./backup.csv --month 2026-09

# 8) CSV 불러오기
python -m budget_app import --from ./backup.csv
```

---

## 5. 데이터 저장 방식

기본 저장 디렉터리는 `./data` 입니다.

저장 파일:
- `transactions.jsonl`
- `categories.jsonl`
- `budgets.jsonl`

파일 기반 JSONL 저장 방식을 사용하며, 데이터는 프로그램 종료 후에도 유지됩니다.

### 기본 카테고리
초기 실행 시 카테고리가 비어 있으면 기본 카테고리 목록을 자동 생성하거나, 사용자에게 추가를 유도하는 방식으로 처리할 수 있습니다.

---

## 6. CSV 스키마

`export` / `import`는 아래 구조를 기준으로 동작합니다.

| 컬럼 | 필수 | 설명 |
| --- | --- | --- |
| `date` | Y | 거래 날짜 (`YYYY-MM-DD`) |
| `type` | Y | `income` 또는 `expense` |
| `category` | Y | 카테고리 이름 |
| `amount` | Y | 양수 정수 |
| `memo` | N | 메모 문자열 |
| `tags` | N | 쉼표 구분 태그 문자열 |

- 인코딩: UTF-8
- 헤더 포함: O

예시:

```csv
date,type,category,amount,memo,tags
2026-09-01,expense,식비,12000,점심,외식,점심
2026-09-03,income,급여,3500000,월급,급여
```

---

## 7. 아키텍처

프로젝트는 책임을 분리한 구조로 구성되어 있습니다.

- `models.py`: 데이터 구조 (`Transaction`, `Budget` 등)
- `repositories.py`: 파일 입출력 및 저장소 로직
- `services.py`: CRUD, 검색, 요약, 예산 계산 등 비즈니스 로직
- `cli.py`: `argparse` 기반 명령어 해석 및 사용자 인터랙션
- `decorators.py`: 예외 처리, 로그, 실행 시간 측정

이 구조를 통해 유지보수성과 확장성을 확보합니다.

---

## 8. 참고 사항

- 잘못된 날짜, 0 이하 금액, 허용되지 않은 타입은 에러 메시지로 처리됩니다.
- 오류 발생 시 스택트레이스 대신 사용자 친화적인 안내 메시지를 출력합니다.
- 정상 종료 시 `exit code 0`, 오류 발생 시 `0이 아닌 값`으로 종료됩니다.
- 외부 라이브러리 없이 표준 라이브러리만 사용합니다.

---

## 9. 요약

이 프로젝트는 단순한 가계부 앱이 아니라, 다음 조건을 갖춘 작은 서비스 형태의 CLI 프로그램입니다.

- 파일 기반 영구 저장
- CRUD 및 조건 검색
- 월별 요약 및 예산관리
- 카테고리 관리
- CSV import/export
- 모듈 분리와 데코레이터 기반 공통 로직 처리

## 10. 추가 질문
### 데코레이터로 분리한 공통 기능이 무엇이며, "왜" 분리가 필요했는지 설명할 수 있는가?
- 모든 함수마다 시작과 끝에 time.perf_counter()를 재고, try-except 블록으로 에러를 감싸고, print로 디버그 로그를 찍는 코드를 수십 줄씩 중복 작성해야 합니다. 이로 인해 실제 핵심 비즈니스 로직(거래 추가, 합계 계산 등)이 부가 기능 코드에 파묻혀 가독성이 떨어지고 유지보수가 극도로 어려워집니다.

### 타입 힌트를 적용해 얻는 이점을 실제 코드 예로 "어떻게" 확인했고 "왜" 도움이 되는지 설명할 수 있는가?
- 만약 실수로 calculate_summary(["2026-05-15", 10000])처럼 Transaction 객체가 아닌 단순 문자열/숫자 리스트를 넘기면, 프로그램을 직접 실행해 보지 않고도 에디터와 mypy 검사기가 사전에 타입 불일치 에러
### JSONL과 CSV 중 선택한 저장 포맷의 장단점을 비교하고, "왜" 그 포맷을 택했는지 근거를 말할 수 있는가?
- CSV: 장점: 엑셀 등 외부 스프레드시트 툴에서 즉시 열어볼 수 있고 파일 용량이 비교적 작습니다.
- 단점: 쉼표(,)나 따옴표(")가 메모/태그 문자열에 포함될 때 이스케이프 처리가 번거로우며, 복수 태그(tags: list[str]) 같은 중첩/리스트형 자료구조를 표준적으로 표현하기 어렵습니다. 또한 컬럼 순서 변경에 취약합니다.
- JSONL: 장점: 한 줄이 독립된 완전한 JSON 객체이므로 json.loads()/dumps()로 파이썬 딕셔너리와 직관적으로 1:1 변환됩니다. tags 같은 리스트 필드를 별도 문자열 파싱 없이 원형 그대로 유지할 수 있고, 나중에 새로운 필드가 추가되어도 스키마 확장이 자유롭습니다.
- 단점: 각 행마다 키 이름(예: "category", "amount")이 중복 기록되므로 파일 용량이 CSV 대비 약간 더 큽니다.
- 가계부 데이터 모델에는 태그 목록(tags: list[str])과 같은 비정형/컬렉션 필드가 존재합니다. CSV에서는 tags를 콤마로 이어붙인 뒤 다시 분리하는 번거로운 과정과 이스케이프 파싱 오류 위험이 있지만, JSONL은 내장 json 모듈만으로 객체 직렬화/역직렬화를 안전하고 완전하게 수행할 수 있어 데이터 무결성과 코드 안정성 관점에서 선택
### 거래가 10만 건으로 늘어난다면, 현재 구조에서 병목이 어디이며 "어떻게" 개선할지 설명할 수 있는가?
- 최신순 정렬 및 검색/요약 시 풀스캔(Full Scan) 아이디등을 일일히 대조하는 방식이라 병목, 수정/삭제 시 파일 전체 재작성(Full Rewrite) 전부 다시 써서 만든 방식이라 디스크 쓰기 병목이 급증 병목:
- 해결책: 월별/연도별 파일 샤딩(Partitioning): 단일 transactions.jsonl 대신 transactions_2026_05.jsonl처럼 월별로 분할 저장하여 summary --month 2026-05 호출 시 해당 월 파일만 읽도록 조회 범위를 축소합니다
- 해결책: RDBMS/SQLite 전환: 파일 기반 저장의 한계를 넘어 인덱스(B-Tree)와 트랜잭션을 지원하는 표준 내장 라이브러리 sqlite3로 저장소(repositories.py) 엔진을 교체합니다.
### import CSV에 일부 깨진 행이 섞이면, "어떻게" 처리해 사용자 신뢰를 지킬지(부분 성공/롤백/리포트) 설명할 수 있는가? 
- 롤백: 단 하나의 행이라도 스키마 위반(날짜 형식 오류, 음수 금액, 필수 컬럼 누락 등)이 발생하면 파일 전체 반영을 취소(Rollback)합니다.
- 부분 성공: 유효한 행들만 정상 등록
- 에러 리포트: 실패 행은 [행 번호, 실패 원인, 원본 내용]을 별도 failed_rows 목록에 수집, 분석하여 내용 작성