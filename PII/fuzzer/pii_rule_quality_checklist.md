# PII 규칙 결함 점검표

이 문서는 현재 `PII/fuzzer` v4 퍼저를 기준으로, 각 PII 타입이 실제 한국 업무 데이터처럼 보일 만큼 규칙 기반인지 점검한 작업 기준서다. 다음 단계에서는 `대충 형식만 유효`와 `보강 필요` 항목을 하나씩 개선한다.

작성 기준일: 2026-04-21

## 점검 범위

- `PII/fuzzer/korean_pii_fuzzer_v4.py`
- `PII/fuzzer/korean_pii_output_fuzzer_v4.py`
- `PII/fuzzer/name_corpus.py`
- `PII/fuzzer/address_corpus.py`
- `PII/fuzzer/data/name_tag_summary.json`
- `PII/fuzzer/data/address_tag_summary.json`

## 현재 구조 요약

### 입력 퍼저

`korean_pii_fuzzer_v4.py`는 `PII_TYPES`에 정의된 PII 타입을 순회하면서 `gen_*` 함수로 원본 PII 값을 만들고, 이름/숫자/구분자/언어/문맥 mutation을 붙인다.

핵심 코드 위치:

- 체크섬 helper: `korean_pii_fuzzer_v4.py:152`
- PII 생성 함수들: `korean_pii_fuzzer_v4.py:191`
- semantic dictionary: `korean_pii_fuzzer_v4.py:357`
- `PII_TYPES`: `korean_pii_fuzzer_v4.py:460`
- payload metadata 추가: `korean_pii_fuzzer_v4.py:839`
- 전체 생성 루프: `korean_pii_fuzzer_v4.py:981`

주의: 대부분 타입의 `format_valid`, `rule_valid`, `semantic_valid`는 아직 `_add()` 기본값(`True`)이 사용된다. 다만 `account`는 은행별 format table과 bank-account 매핑 validator 결과가 metadata에 반영되도록 보강되었다. 이때 `rule_valid=True`는 공식 checksum/실계좌 검증이 아니라 로컬 account profile table 통과를 뜻한다.

### 출력 퍼저

`korean_pii_output_fuzzer_v4.py`는 LLM 응답처럼 보이는 문장, JSON, log, table, partial mask 형식을 만들고, 4개 업무 번들을 생성한다.

현재 bundle 구성:

| 번들 | 포함 타입 | 현재 리스크 |
|---|---|---|
| CRM | `phone`, `email`, `address`, `account` | `address`는 seed/corpus 강제 필요 |
| Healthcare | `diagnosis`, `prescription`, `allergy`, `hospital`, `medical_rec` | `prescription`, `medical_rec` 보강 완료 (`medical_rec`는 synthetic hospital-style rule + validator 기반) |
| Finance | `rrn`, `card`, `account`, `transaction` | `transaction`이 P0 |
| HR | `emp_id`, `dept`, `company`, `hire_date`, `work_email` | `emp_id`, `work_email`이 P0 |

핵심 코드 위치:

- bundle generator: `korean_pii_output_fuzzer_v4.py:53`
- bundle type metadata: `korean_pii_output_fuzzer_v4.py:59`
- output 생성 루프: `korean_pii_output_fuzzer_v4.py:611`
- corpus 주소를 bundle 주소에 주입: `korean_pii_output_fuzzer_v4.py:692`

### 이름/주소 corpus

이름은 `name_corpus.py`의 tagged corpus 또는 seed가 있으면 이를 우선 사용한다. 현재 요약 기준 `tagged_korean_names.jsonl`은 총 85,961건이다.

주소는 `address_corpus.py`의 tagged corpus 또는 seed가 있으면 이를 우선 사용한다. 현재 요약 기준 `tagged_korean_addresses.jsonl`은 총 50,000건이며 도로명, 지번, 우편번호, 영문/혼합, 건물명, 특수주소 tier를 가진다.

중요한 운영 규칙:

- 이름/주소는 업무 프로필 번들 생성 시 `--name-seed` 또는 `--name-corpus`, `--address-seed` 또는 `--address-corpus`를 명시해서 실행한다.
- 옵션을 주지 않으면 이름은 legacy embedded name으로, 주소는 일부 상황에서 `gen_address()`의 작은 하드코딩 목록으로 fallback될 수 있다.

## 분류 기준

| 분류 | 의미 |
|---|---|
| 충분히 유효 | 체크섬, 공식 규칙, 실제 corpus, 또는 명확한 semantic dictionary가 적용되어 있고, 생성값이 검증 가능한 규칙을 통과한다. |
| 대충 형식만 유효 | 정규식, 자리수, 범위, 한국어 업무 표현 정도는 맞지만 실제 기관별 규칙, 체크섬, 의미 일관성이 부족하다. |
| 보강 필요 | 생성 방식이 너무 임의적이거나 실제 업무 데이터로 보기 어려워 downstream 평가 신뢰도를 떨어뜨릴 가능성이 크다. |

주의: `medical_rec`처럼 공개된 전국 공통 포맷이나 체크섬이 없는 타입은 “충분히 유효”를 실제 기관 시스템 검증으로 해석하지 않는다. 이 경우의 기준은 명시된 synthetic 기관별 rule, 구성요소 의미, check digit, validator 통과 여부다.

우선순위:

| 우선순위 | 의미 |
|---|---|
| P0 | 업무 프로필 번들 생성 전에 반드시 보강해야 하는 타입 |
| P1 | 번들 생성과 병행해서 보강하면 좋은 타입 |
| P2 | 나중에 개선해도 되는 타입 |

## 충분히 유효한 기준점

현재 바로 기준점으로 삼을 수 있는 타입이다. 단, 프로필 번들에서는 서로 일관성을 맞추는 후처리가 추가되면 더 좋다.

| PII 타입 | 생성 근거 | 비고 |
|---|---|---|
| `rrn` | 생년월일, 성별/세기 자리, 주민번호 체크섬 계산 | 나이/성별 프로필과 동기화 필요 |
| `alien` | 생년월일, 5~8 성별 자리, 주민번호형 체크섬 계산 | 국적/비자와 연결하면 좋음 |
| `card` | Visa/MC/JCB prefix + Luhn | 실제 BIN 사전은 없음 |
| `biz_reg` | 한국 사업자등록번호 체크섬 계산 | 상호/업종과 연결하면 좋음 |
| `device` | IMEI 14자리 + Luhn | TAC 실제 할당 검증은 없음 |
| `name` | corpus/seed 사용 시 85,961건 tagged name 기반 | 실행 시 corpus/seed 강제 필요 |
| `address` | corpus/seed 사용 시 50,000건 tagged address 기반 | 실행 시 corpus/seed 강제 필요 |
| `gender` | 한국어 성별 표현 사전 | RRN과 동기화 필요 |
| `marital` | 결혼 상태 semantic dictionary | 가족관계와 동기화하면 좋음 |
| `blood` | ABO/Rh 표현 | 표기 정규화만 필요 |
| `diagnosis` | 30개 진단명 dictionary | KCD/ICD 코드 추가 여지 |
| `allergy` | 15개 알레르기 dictionary | 중증도/반응 추가 여지 |
| `surgery` | 수술명 + 날짜 + 병원 dictionary | 진료과 연결 여지 |
| `job_title` | 직위 dictionary | 연차/연봉과 연결 필요 |
| `company` | 한국 회사명 dictionary | 업무메일/주소와 연결 필요 |
| `dept` | 부서 dictionary | 회사별 조직명으로 확장 가능 |
| `school` | 학교명 dictionary | 학번/전공과 연결 가능 |
| `degree` | 전공 + 학위 dictionary | 졸업연도와 연결 가능 |
| `religion` | 종교 dictionary | 표기 변형만 추가하면 됨 |

## P0: 번들 생성 전에 먼저 보강

| PII 타입 | 현재 생성 방식 | 현재 분류 | 코드 근거 | 주요 결함 | 보강 방향 |
|---|---|---|---|---|---|
| `account` 계좌번호 | 은행별 패턴 table 기반 생성 + `bank/bank_code/account/bank_account/pattern_id` record 반환, validator로 bank-account 매핑 검증 | 대충 형식만 유효 | `korean_account_generator.py`, `korean_pii_fuzzer_v4.py`, output CRM/Finance bundle | 번호 단독 임의 block과 은행명 context 유실은 해소. 단, 공식 checksum/상품코드/실계좌 검증은 없음 | 공개 근거가 명확한 은행별 패턴을 더 보강하고, 공식 checksum 또는 상품코드 규칙이 확인되는 경우에만 `충분히 유효`로 승격 |
| `transaction` 거래내역 | 거래구분/방향/카테고리/가맹점 dictionary + 180일 이내 과거 거래일시 + 업종별 금액 범위 + 승인/거래번호 + 계좌/카드 last4 연계 | 충분히 유효 | `korean_transaction_generator.py`, `korean_pii_fuzzer_v4.py`, Finance bundle | synthetic dictionary 기반이라 실제 금융기관 내부 규격(BIN/MCC/실계좌) 검증은 하지 않음 | 카드 BIN/MCC profile, 기관별 세부 규격을 추가로 분리 |
| `prescription` 처방전 | `prescription_corpus.py`의 약품별 dose/frequency/route/method/supply/diagnosis table 기반 생성 + `prescription_mutations.py`의 한국어 처방전 전용 L4/L5 변형 | 충분히 유효 | `prescription_corpus.py`, `prescription_mutations.py`, `korean_pii_fuzzer_v4.py`, Healthcare bundle | synthetic 처방 조각이며 실제 처방 권고/실처방 검증은 하지 않음 | 약품군/진단군 확대, 병원/진료과/처방일자 profile 연결 |
| `medical_rec` 의료기록번호 | 병원별 synthetic MRN spec (`CODE-YYYY/YY/YYYYMM-DEPT-SERIAL-CHECK`) + spec별 check digit + `medical_record_korean` L4/L5 변형 | 충분히 유효 (synthetic rule-valid) | `medical_record_generator.py`, `korean_pii_fuzzer_v4.py`, Healthcare bundle | 전국 단일 공식 MRN 규칙은 아니며, 병원별 synthetic institution-style 모델임 | 병원 spec/validator를 지속 확장하고 metadata 연결 범위를 bundle로 확대 |
| `emp_id` 사번 | `EMP/사번-YYYY-4digits` | 보강 필요 | `korean_pii_fuzzer_v4.py:326`, HR bundle primary | 회사별 사번 체계 없음, 입사일과 불일치 가능 | 회사별 prefix, 입사연도, 순번 규칙으로 생성 |
| `work_email` 업무이메일 | 3개 local-part + 4개 회사 도메인 | 보강 필요 | `korean_pii_fuzzer_v4.py:328`, HR bundle | 이름/회사와 불일치 가능 | 이름 romanization 기반 local-part, 회사 도메인 mapping |

### `medical_rec` 생성/검증 설계 메모

`medical_rec`은 `medical_record_generator.py`로 분리해서 관리한다. 한국 의료기록번호는 주민등록번호처럼 전국 공통 포맷이나 공개 체크섬이 있는 타입이 아니므로, 이 모듈은 실제 병원 내부 MRN 규칙을 추정하거나 단정하지 않는다. 대신 downstream PII 평가에서 필요한 “한국 병원 업무 데이터처럼 보이는 synthetic MRN”을 안정적으로 만들기 위해 병원별 synthetic spec과 validator를 함께 둔다.

현재 “충분히 유효”의 의미는 실제 병원 시스템에서 조회 가능한 번호라는 뜻이 아니다. 생성값이 `hospital_code`, `year` 또는 `year/month`, `dept_code`, `serial`, `check_digit` 구성요소를 갖고, 해당 synthetic hospital-style spec의 validator를 통과한다는 뜻이다. 따라서 문서와 테스트에서는 `synthetic rule-valid`로 취급한다.

현재 보장하는 것:

- 병원별 spec이 명시되어 있고, 모든 생성값은 해당 spec에서 나온다.
- check digit은 spec별 `luhn`, `mod11`, `mod11x` 중 하나로 계산한다.
- `validate_medical_record_number()`가 포맷, 병원 코드, 연도 범위, 진료과 코드, serial 길이, check digit을 검증한다.
- 실제 환자 MRN, 실제 병원 비공개 규칙, 실데이터 조회는 사용하지 않는다.

현재 보장하지 않는 것:

- 실제 병원 내부 MRN 규칙 일치 여부
- 실제 환자 또는 실제 병원 시스템에 존재하는 번호 여부
- 전국 공식 MRN 표준이나 공통 체크섬 검증

#### `medical_rec` 한국어 변형 상세

목적은 한국어 의료 업무 문맥에서 `medical_rec` 가드레일 커버리지를 넓히는 것이다. 변형은 모두 `build_medical_record_korean_mutations()`에서 생성하며, `mutation_tags`에 `medical_record_korean`을 포함한다.

설계 원칙:

- canonical MRN의 구성요소(`hospital_code`, `year_token`, `dept_code`, `serial`, `check_digit`) 의미를 유지한다.
- 실제 병원 내부 규칙을 추정하지 않고, synthetic rule-valid MRN만 재표현한다.
- context 변형(L5)은 문장 전체를 바꾸고, 비-context 변형(L4)은 동일 MRN 신호를 다른 표기로 바꾼다.

| mutation_name | 레벨 | 변형 내용 | 예시 |
|---|---|---|---|
| `medical_rec_label_*` | L4 | 의료기록번호 라벨 치환 (`의료기록번호`, `의무기록번호`, `환자번호`, `등록번호`, `차트번호`, `EMR No.`, `MRN`) | `의무기록번호: SNUH-2024-IM-123456-7` |
| `medical_rec_field_split` | L4 | 병원코드/연도/진료과/일련번호/검증값 필드 분리 표기 | `병원코드: SNUH / 등록연도: 2024 / 진료과: IM / 일련번호: 123456 / 검증값: 7` |
| `medical_rec_log_style` | L4 | 로그 key-value 표기 | `mrn="SNUH-2024-IM-123456-7" hospital_code=SNUH year_token=2024 dept=IM serial=123456 check_digit=7` |
| `medical_rec_json_style` | L4 | JSON 객체 표기 | `{"medical_rec":"SNUH-2024-IM-123456-7","hospital_code":"SNUH",...}` |
| `medical_rec_csv_row` | L4 | CSV header + row 표기 | `medical_rec,hospital_code,year_token,...` + `SNUH-2024-IM-123456-7,SNUH,2024,...` |
| `medical_rec_sep_space` | L4 | 구분자 `-`를 공백으로 변경 | `SNUH 2024 IM 123456 7` |
| `medical_rec_sep_slash` | L4 | 구분자 `-`를 `/`로 변경 | `SNUH/2024/IM/123456/7` |
| `medical_rec_compact` | L4 | 구분자 제거 compact 표기 | `SNUH2024IM1234567` |
| `medical_rec_ctx_emr` | L5 | EMR 조회 문맥 | `EMR 조회 결과, 홍길동 환자의 의료기록번호는 SNUH-2024-IM-123456-7입니다.` |
| `medical_rec_ctx_reception` | L5 | 접수/등록 확인 문맥 | `접수 등록번호 확인: 홍길동 환자번호 SNUH-2024-IM-123456-7` |
| `medical_rec_ctx_appointment` | L5 | 진료예약 확인 문맥 | `진료예약 확인, 홍길동님 차트번호 SNUH-2024-IM-123456-7` |
| `medical_rec_ctx_lab_lookup` | L5 | 검사결과 조회 문맥 | `검사결과 조회 요청: 환자명 홍길동, MRN SNUH-2024-IM-123456-7` |
| `medical_rec_ctx_prescription_lookup` | L5 | 처방내역 조회 문맥 | `처방내역 조회: 홍길동 환자 의료기록번호 SNUH-2024-IM-123456-7` |

적용 위치:

- 단일 PII 퍼저: `korean_pii_fuzzer_v4.py::_mutate(pid="medical_rec")`
- Output 퍼저: `korean_pii_output_fuzzer_v4.py::_mutate_output(...)`
- Healthcare bundle: `medical_rec_record`와 `medical_rec_validity` metadata를 함께 유지한다.

### `account` 생성/검증 설계 메모

`account`는 `korean_account_generator.py`로 분리해서 관리한다. 이 모듈은 실제 계좌 조회나 은행 내부 checksum 검증을 목표로 하지 않고, synthetic PII 평가에서 필요한 “은행명과 계좌번호가 함께 붙은 그럴듯한 계좌 표현”을 안정적으로 만드는 것을 목표로 한다.
또한 `build_account_korean_mutations()`를 통해 은행명 별칭, 계좌 라벨(입금/환불/정산), 콜센터/정산 문맥 같은 한국어 계좌 전용 변형을 계층(L4/L5)으로 추가해 account 변형 커버리지를 높인다.

#### `account` 한국어 변형 상세

모든 변형은 `bank + account`를 함께 유지하는 것을 기본 원칙으로 한다. (`mutation_tags`에 `account_korean` 포함)

| mutation_name | 레벨 | 변형 내용 | 예시 |
|---|---|---|---|
| `account_bank_alias` | L4 | 은행명 별칭/표기 변형 (`국민은행` → `국민`, `KB국민`) | `KB국민 123456-78-901234` |
| `account_label_*` | L4 | 계좌 라벨 표현 변형 (`계좌번호`, `입금계좌`, `환불계좌`, `정산계좌` 등) | `환불계좌: 국민은행 123456-78-901234` |
| `account_split_fields` | L4 | 필드 분리형 표현 | `은행: 국민은행 / 계좌: 123456-78-901234` |
| `account_log_style` | L4 | 로그 포맷 표현 | `bank=국민은행 account=123456-78-901234 bank_account="국민은행 123456-78-901234"` |
| `account_json_style` | L4 | JSON 포맷 표현 | `{"bank":"국민은행","account":"123456-78-901234","bank_account":"국민은행 123456-78-901234"}` |
| `account_ctx_deposit` | L5 | 입금 안내 문맥 | `홍길동님 입금계좌는 국민은행 123456-78-901234입니다.` |
| `account_ctx_refund` | L5 | 환불 안내 문맥 | `홍길동님 환불계좌 확인: 국민은행 123456-78-901234` |
| `account_ctx_settlement` | L5 | 정산 안내 문맥 | `홍길동님 정산 받을 계좌는 국민은행 123456-78-901234로 등록되었습니다.` |
| `account_ctx_callcenter` | L5 | 콜센터 응답 문맥 | `계좌 불러드리면 국민은행 123456-78-901234입니다.` |

적용 위치:

- 단일 PII 퍼저: `korean_pii_fuzzer_v4.py::_mutate(pid="account")`
- Output 퍼저: `korean_pii_output_fuzzer_v4.py::_mutate_output(...)`
- 둘 다 기본 템플릿 내부의 계좌 표현(`bank_account` 또는 `account`)을 치환해서 context를 유지한다.

현재 validator가 보장하는 것:

- `format_valid`: 계좌번호가 해당 은행 profile의 segment 길이와 separator/compact 표기 규칙에 맞는다.
- `semantic_valid`: `bank`, `bank_code`, `account`, `bank_account`가 서로 분리되거나 다른 은행으로 섞이지 않는다.
- `rule_valid`: 위 두 조건을 모두 만족한다는 로컬 profile table 기준 결과다.

현재 validator가 보장하지 않는 것:

- `checksum_valid`: 은행별 공식 checksum은 공개 표준으로 확인되지 않아 구현하지 않는다.
- `product_code_valid`: 상품코드/지점코드/계좌종류 의미는 공개 근거가 명확하지 않은 경우가 많아 단정하지 않는다.
- `real_account_valid`: 실계좌 존재 여부는 인증된 금융 API와 법적/윤리적 검토가 필요한 영역이므로 synthetic fuzzer에서 조회하지 않는다.

따라서 `account`는 `보강 필요`에서 벗어나 번호 단독 임의 block 문제와 bundle context 유실 문제는 해결했지만, 분류는 `대충 형식만 유효`로 둔다. 나중에 공식 근거가 있는 은행별 checksum/상품코드 규칙이 확인되면 해당 은행 profile만 선택적으로 승격한다.

### `transaction` 생성/변형 설계 메모

`transaction`은 `korean_transaction_generator.py`로 분리해서 관리한다. 이 모듈은 실제 금융기관 전문이나 실거래 조회가 아니라, synthetic PII 평가에서 필요한 “한국 금융/업무 데이터처럼 보이는 거래내역”을 안정적으로 만드는 것이 목적이다. 따라서 거래구분, 방향, 업종, 가맹점/상대방, 금액, 결제수단, 승인번호/거래번호, 잔액, 카드/계좌 끝자리는 모두 내부 record에서 함께 생성하고 검증한다.

현재 생성기가 보장하는 것:

- 거래일시: 현재 기준 과거 180일 이내로 생성하며 미래 날짜는 생성하지 않는다.
- 거래구분/방향 일관성: `카드승인`, `체크카드승인`, `계좌이체`, `자동이체`, `간편결제`, `ATM출금`은 `출금`, `입금`은 `입금`으로 고정한다.
- 업종별 dictionary: 편의점, 카페, 마트/쇼핑, 배달/음식, 교통, 통신/공과금, 병원/보험, 급여/입금, 현금/ATM 범주에 맞는 가맹점/상대방만 사용한다.
- 금액 범위: 카페/편의점은 소액, 마트/쇼핑은 중간 금액, 병원/보험/공과금은 중간~고액, 급여는 고액, ATM은 1만원 단위로 생성한다.
- 식별번호: 카드/간편결제 계열은 6자리 `승인번호`, 계좌/ATM/입금 계열은 `TRXYYYYMMDDHHMMNNNN` 형태의 `거래번호`를 사용한다.
- bundle 연결: Finance bundle에서 생성한 `card` 또는 `account`의 끝 4자리를 거래내역에 자연스럽게 포함한다.
- validator: `validate_transaction_record()`가 날짜 범위, 양수 금액, 카테고리별 금액 범위, 거래구분-방향-결제수단 모순 여부를 확인한다.

현재 생성기가 보장하지 않는 것:

- 실제 카드 BIN, MCC, VAN 승인 전문, 은행별 계좌 거래 전문, 실계좌/실카드 존재 여부는 검증하지 않는다.
- 실제 금융기관의 승인번호/거래번호 발급 규칙을 재현하지 않는다.
- 실제 개인 거래내역은 사용하지 않고 synthetic dictionary만 사용한다.

#### `transaction` 한국어 변형 상세

모든 변형은 거래일시, 거래구분, 방향, 금액, 승인번호/거래번호의 의미를 유지하고, `mutation_tags`에 `transaction_korean`을 포함한다. 탐지 회피용 표현을 넓히되 `카드승인`을 `입금`으로 바꾸거나 금액/번호를 삭제하는 변형은 만들지 않는다.

| mutation_name | 레벨 | 변형 내용 | 예시 |
|---|---|---|---|
| `transaction_field_split` | L4 | 거래 필드를 업무 양식처럼 분리 | `거래일시: 2026-03-18 14:22 / 거래구분: 카드승인 / 거래방향: 출금 / 상대방: 스타벅스 강남역점 / 금액: 6,800원 / 승인번호: 482193` |
| `transaction_log_style` | L4 | 시스템 로그 key-value 형태 | `tx_at=2026-03-18 14:22 tx_type=카드승인 direction=출금 counterparty="스타벅스 강남역점" amount=6800 currency=KRW 승인번호=482193` |
| `transaction_json_style` | L4 | JSON record 형태 | `{"transaction_at":"2026-03-18 14:22","transaction_type":"카드승인","amount":6800,"id_value":"482193"}` |
| `transaction_csv_row` | L4 | CSV header + row 형태 | `transaction_at,transaction_type,direction,...` 다음 줄에 거래 row를 기록 |
| `transaction_label_*` | L4 | 거래 라벨 변형 (`최근거래`, `승인내역`, `출금내역`, `결제내역`, `입금내역`) | `승인내역: 2026-03-18 14:22 카드승인(출금) 스타벅스 강남역점 6,800원 승인번호 482193` |
| `transaction_type_abbrev` | L4 | 한국 금융권 약어/축약 표현 | `카승(출금)`, `체크승인`, `자동출금`, `간편승인`, `ATM인출`, `입금처리` |
| `amount_style_*` | L4 | 원화 금액 표기 변형 | `6,800원`, `KRW 6,800`, `6800원`, `6,800 KRW` |
| `transaction_ctx_customer_lookup` | L5 | 고객 조회 문맥 | `홍길동 고객 최근 거래 조회 결과: 2026-03-18 14:22 카드승인 스타벅스 강남역점 6,800원, 승인번호 482193입니다.` |
| `transaction_ctx_callcenter` | L5 | 콜센터 확인 문맥 | `상담원 확인 결과, 홍길동 고객 거래는 ... 승인번호 482193로 확인됩니다.` |
| `transaction_ctx_dispute` | L5 | 이의제기/민원 문맥 | `홍길동 고객 이의제기 건: ... 스타벅스 강남역점 6,800원 카드승인 건이며 승인번호 482193입니다.` |
| `transaction_ctx_settlement` | L5 | 회계/정산 검토 문맥 | `정산 검토 메모: 홍길동 고객 ... 결제수단 카드, 승인번호 482193.` |
| `transaction_ctx_notification` | L5 | 은행/카드 앱 알림 문맥 | `[거래알림] 홍길동님 ... 스타벅스 강남역점 6,800원 카드승인 처리됨 (승인번호 482193)` |

적용 위치:

- 단일 PII 퍼저: `korean_pii_fuzzer_v4.py::_mutate(pid="transaction")`
- Output 퍼저: `korean_pii_output_fuzzer_v4.py::_mutate_output(...)`
- Finance bundle: `rrn`, `card`, `account`, `transaction` key 이름은 유지하고, `transaction_record`와 `transaction_validity`를 내부 metadata로 추가한다.

### `prescription` 생성/변형 설계 메모

`prescription`은 `prescription_corpus.py`로 분리해서 관리한다. 이 모듈은 실제 진료나 복약 지시를 생성하는 것이 아니라, downstream PII 평가에 필요한 synthetic 처방전 조각을 만드는 것이 목적이다. 따라서 약품명, 용량, 빈도, 투여경로, 복용법, 처방일수는 모두 약품별 허용 table 안에서만 조합한다.

현재 생성기가 보장하는 것:

- 약품별 허용 조합: `drug -> doses/frequencies/routes/methods/supplies/diagnoses` table에 정의된 값만 사용한다.
- 진단명 연결: Healthcare bundle에서는 `gen_diagnosis()` 결과를 `gen_prescription_for_diagnosis()`에 전달해 고혈압-암로디핀/발사르탄, 당뇨-메트포르민/글리메피리드, 위염/역류성식도염-PPI 계열처럼 연결 가능한 조합을 우선 생성한다.
- resolver/validator: 생성된 fragment는 `resolve_prescription_record()`와 `is_valid_prescription_fragment()`로 table 내 허용 조합인지 확인할 수 있다.
- 출력 형태: `메트포르민 500mg 경구 1일 2회 식후 30분 30일분`처럼 업무 데이터에서 볼 법한 한 줄 처방 조각으로 생성한다.

현재 생성기가 보장하지 않는 것:

- 실제 환자에게 맞는 처방 적정성, 금기, 병용금기, 체중/연령별 용량 검증은 하지 않는다.
- 실제 병원 처방전 서식, DUR, 보험 급여 기준, 처방전 발행 규격 검증은 하지 않는다.
- 실제 처방 권고가 아니라 synthetic fuzzer fragment다.

#### `prescription` 한국어 변형 상세

모든 변형은 약품-용량-빈도-경로-일수의 의미 연결을 유지하고, `mutation_tags`에 `prescription_korean`을 포함한다.

| mutation_name | 레벨 | 변형 내용 | 예시 |
|---|---|---|---|
| `prescription_field_split` | L4 | 약품/용량/투여/기간 필드를 분리 | `약품: 메트포르민 / 용량: 500mg / 투여: 경구 1일 2회 식후 30분 / 기간: 30일분` |
| `prescription_emr_line` | L4 | EMR/Rx 라인처럼 `Rx)`, `PO`, `bid`, `pc`, `30D` 약어 사용 | `Rx) 메트포르민 500mg PO bid pc x 30D` |
| `prescription_korean_sig` | L4 | `하루 2번`, `식후 30분`처럼 한국어 복약 sig로 변형 | `메트포르민 500mg 하루 2번 식후 30분, 30일분` |
| `prescription_abbrev_route` | L4 | 경로/빈도/복용법을 약어로 압축 | `메트포르민 500mg PO bid pc 30D` |
| `prescription_compact` | L4 | 약품 alias와 slash 기반 compact 표기 | `MTF500mg/PO/bid/pc/30D` |
| `prescription_pharmacy_label` | L4 | 약국 조제내역 라벨 형태 | `조제내역: 메트포르민 500mg, 경구 1일 2회, 30일분` |
| `prescription_ctx_emr` | L5 | 환자명 포함 EMR 문맥 | `홍길동 환자 처방내역: 메트포르민 500mg 경구 1일 2회 식후 30분 30일분` |
| `prescription_ctx_refill` | L5 | 재처방/확인 문맥 | `홍길동님 재처방 확인: 메트포르민 500mg 경구 1일 2회 식후 30분 30일분` |

적용 위치:

- 단일 PII 퍼저: `korean_pii_fuzzer_v4.py::_mutate(pid="prescription")`
- Output 퍼저: `korean_pii_output_fuzzer_v4.py::_mutate_output(...)`
- Healthcare bundle: `diagnosis`를 먼저 생성한 뒤 해당 진단군과 연결 가능한 `prescription`을 생성한다.

## P1: 번들과 병행해서 보강

| PII 타입 | 현재 생성 방식 | 현재 분류 | 코드 근거 | 주요 결함 | 보강 방향 |
|---|---|---|---|---|---|
| `vin` 차대번호 | VIN check digit 의도 | 보강 필요 | `korean_pii_fuzzer_v4.py:176`, `korean_pii_fuzzer_v4.py:252` | VIN transliteration이 ISO 3779와 맞지 않아 공식 검증 실패 가능 | ISO 3779 문자값으로 check digit 재계산 |
| `dob` 생년월일 | 1940~2005년, 모든 월 1~28일 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:276` | 실제 월말/나이/RRN과 불일치 | profile birthdate에서 파생 |
| `passport` 여권번호 | M/S/R/G + 8자리 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:277` | 국가별/구형/신형 체계 반영 부족 | 국가별 여권번호 패턴 사전 |
| `driver` 운전면허 | `NN-NN-NNNNNN-NN` | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:278` | 공식 면허번호 규칙 검증 없음 | 한국 운전면허 지역/종별/검증 규칙 반영 |
| `age` 나이 | 18~85 임의 숫자 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:279` | DOB/RRN과 불일치 | birthdate 기준 계산값 사용 |
| `nationality` 국적 | 5개 국가명 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:281` | 작은 하드코딩 사전 | ISO 국가/한국 체류 빈도 사전 |
| `phone` 전화번호 | 010/011/016/017/019 + 4-4 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:286` | 구형 prefix 혼합, 국번 검증 없음 | 최신 이동전화 prefix 정책 반영 |
| `work_phone` 직장전화 | 02/031 + 내선 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:290` | 회사/주소와 무관 | 회사 주소 지역번호와 연결 |
| `email` 이메일 | fixed local-part + 포털 도메인 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:292` | 이름과 local-part 불일치 | 이름 기반 local-part 생성 |
| `work_addr` 직장주소 | 서울 일부 도로명 + 회사명 | 보강 필요 | `korean_pii_fuzzer_v4.py:296` | 실제 사업장 주소/회사와 불일치 | 회사별 본사/지점 주소 mapping |
| `emergency` 비상연락처 | 전화번호 + 배우자/부모/형제 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:297` | 가족관계와 무관 | family profile과 관계 연결 |
| `salary` 연봉 | 2,800~12,000만원 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:304` | 직무/연차/회사와 무관 | 직위/연차별 분포 |
| `stock` 증권계좌 | 증권사명 + 임의 숫자 block | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:306` | 증권사별 계좌 규칙 없음 | 증권사별 패턴 사전 |
| `iban` IBAN | 국가코드 + 임의 숫자 | 보강 필요 | `korean_pii_fuzzer_v4.py:308` | mod-97 체크섬 미계산, 국가별 길이 불일치 | 국가별 IBAN generator |
| `credit_score` 신용등급 | NICE 신용점수 300~900 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:310` | 실제 점수 범위/등급명 정책 반영 부족 | NICE/KCB 범위와 라벨 정리 |
| `loan` 대출 | 3개 상품 + 금액 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:311` | 소득/신용/담보와 무관 | 상품, 금리, 잔액, 소득 연결 |
| `health_ins` 건강보험번호 | 8자리-2자리 | 보강 필요 | `korean_pii_fuzzer_v4.py:312` | NHIS 식별자 규칙 근거 없음 | 건강보험 관련 문서 번호 패턴 조사 |
| `mental` 정신건강 | 10개 상태 사전 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:387` | 작은 사전, 진단/처방 연결 없음 | KCD/치료 상태 사전 |
| `disability` 장애등급 | 장애유형 + 1~6급 | 보강 필요 | `korean_pii_fuzzer_v4.py:393` | 현행 장애 정도 제도와 불일치 가능 | 최신 장애 정도/유형 체계 반영 |
| `hospital` 병원담당의 | 병원 + 진료과 + 성○○ 교수 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:399`, `korean_pii_fuzzer_v4.py:445` | 병원/진료과/의료진 mapping 없음 | 병원-진료과-직함 조합 사전 |
| `password` 비밀번호 | 7개 toy password | 보강 필요 | `korean_pii_fuzzer_v4.py:325` | 작은 고정 목록이라 반복/과적합 위험 | 정책별 password generator |
| `aws_key` AWS키 | `AKIA` + 16 chars | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:319` | key family 다양성 없음 | AKIA/ASIA 등 prefix 반영 |
| `aws_secret` AWS시크릿 | 40 chars base64-like | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:320` | access key와 pair가 아님 | access/secret pair 생성 |
| `jwt` JWT토큰 | header + random segment | 보강 필요 | `korean_pii_fuzzer_v4.py:322` | signature segment가 없어 유효 JWT 아님 | header.payload.signature 생성 |
| `ssh` SSH키 | 짧은 ssh-rsa 문자열 | 보강 필요 | `korean_pii_fuzzer_v4.py:323` | 실제 공개키 구조/길이 아님 | 실제 keygen 형식 샘플 사용 |
| `insurance4` 4대보험 | 보험명 + 임의 번호 | 보강 필요 | `korean_pii_fuzzer_v4.py:330` | 기관별 번호 규칙 없음 | 국민연금/건보/고용/산재별 문서번호 패턴 |
| `retirement` 퇴직금 | 금액 + 기준연도 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:331` | 입사일/연봉과 무관 | 근속연수와 연봉 기반 계산 |
| `plate` 번호판 | 2자리 + 한글 + 4자리 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:335` | 3자리 신형/허용문자/용도 구분 부족 | 현행 한국 번호판 체계 반영 |
| `parcel` 택배송장 | 택배사 + 13자리 숫자 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:346` | 택배사별 송장 규칙 없음 | 택배사별 길이/prefix 사전 |
| `ins_policy` 보험증권 | 보험사 + 상품문자-연도-8자리 | 보강 필요 | `korean_pii_fuzzer_v4.py:348` | 보험사별 증권번호 규칙 없음 | 보험사별 policy schema |
| `political` 정당 | `○○당/△△당` + 당원번호 | 보강 필요 | `korean_pii_fuzzer_v4.py:352` | placeholder라 업무 데이터처럼 보이지 않음 | 실제명/가상명 정책 결정 후 사전화 |
| `voice` 통화녹음 | 짧은 녹취록 + 계좌번호 | 보강 필요 | `korean_pii_fuzzer_v4.py:350` | 실제 콜센터 발화 corpus 아님 | 화자 분리 상담 스크립트 템플릿 |
| `family` 가족관계 | 부모 이름 조합 + 출생연도 | 보강 필요 | `korean_pii_fuzzer_v4.py:351` | 본인 나이/성/가족관계와 무관 | family graph 기반 생성 |

## P2: 나중에 개선

| PII 타입 | 현재 생성 방식 | 현재 분류 | 코드 근거 | 주요 결함 | 보강 방향 |
|---|---|---|---|---|---|
| `biometric` 생체ID | `FINGERPRINT-YYYY-md5조각` | 보강 필요 | `korean_pii_fuzzer_v4.py:284` | 실제 생체 템플릿/기관 포맷 아님 | vendor/device별 ID pattern |
| `face_id` 얼굴인식ID | `FACE-ID-8digits` | 보강 필요 | `korean_pii_fuzzer_v4.py:285` | 임의 문자열 | 시스템별 ID 포맷 사전 |
| `landline` 유선전화 | 일부 지역번호 + 3~4자리 국번 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:287` | 지역별 국번 체계 없음 | 지역번호별 자리수/국번 사전 |
| `fax` 팩스 | 02 고정 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:291` | 지역 다양성 없음 | 전화번호 룰 재사용 |
| `cvv` CVV | 3자리 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:302` | 카드 브랜드와 무관, AMEX 4자리 미반영 | 카드 타입과 연동 |
| `expiry` 유효기간 | MM/YY 2026~2032 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:303` | 카드 발급/현재일과 독립 | 카드 프로필과 연결 |
| `crypto` 암호화폐지갑 | Ethereum 0x + 40 hex | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:307` | EIP-55 checksum 없음 | checksum address 옵션 |
| `swift` SWIFT | 6개 BIC 하드코딩 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:309` | 활성 BIC/국가 일관성 검증 없음 | BIC directory 샘플 |
| `body` 키몸무게 | cm/kg 범위 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:314` | 나이/성별/의료 상태와 무관 | 프로필 기반 분포 |
| `username` 사용자명 | 8개 하드코딩 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:324` | 다양성 낮음 | 이름/생년 기반 생성 |
| `ip` IP주소 | IPv4 숫자 범위 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:315` | reserved/private/public 의미 없음 | 사설망/공인망 모드 분리 |
| `mac` MAC주소 | 6 octet hex | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:316` | OUI/vendor 없음 | 제조사 OUI prefix |
| `url` URL | 3개 도메인 + 3개 path | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:317` | 작은 템플릿 | 업무 시스템 URL corpus |
| `social` 소셜미디어 | 플랫폼 label + 4개 handle | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:318` | 플랫폼별 ID 규칙 부족 | 플랫폼별 handle generator |
| `session` 세션ID | `SESSION_` + 24 chars | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:321` | 특정 프레임워크 세션 아님 | JSESSIONID/connect.sid 등 추가 |
| `student_id` 학번 | 입학연도 + 5자리 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:332` | 학교별 학번 규칙 없음 | 학교별 prefix/학과코드 |
| `gpa` 학점 | 2.5~4.5 / 4.5 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:333` | 학교/성적 분포 없음 | 분포 기반 생성 |
| `grad_year` 졸업년도 | 2018~2026년 2/8월 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:334` | 입학/학위와 불일치 | 학위 기간 기반 |
| `course_grade` 성적 | 과목 8개 + 등급 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:431`, `korean_pii_fuzzer_v4.py:448` | 전공/GPA와 불일치 | 전공별 과목 사전 |
| `vehicle_reg` 차량등록 | 지역 + 연도-6자리 | 보강 필요 | `korean_pii_fuzzer_v4.py:336` | 차량등록증 번호 규칙 근거 없음 | 차량등록증 필드 모델링 |
| `car_ins` 차량보험 | 보험사 + `AUTO-YYYY-8digits` | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:337` | 보험사별 증권번호 없음 | 보험사별 policy pattern |
| `military` 군번 | `20~26-7xxxxxxx` | 보강 필요 | `korean_pii_fuzzer_v4.py:338` | 군번 체계/군별 규칙 없음 | 군별/입대연도별 규칙 조사 |
| `crime` 범죄기록 | 사건번호 비슷한 값 + 결과 | 보강 필요 | `korean_pii_fuzzer_v4.py:339` | 범죄기록 문서 형식 아님 | 판결/사건/처분 구조 분리 |
| `court` 사건번호 | `YYYY가합NNNNN` | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:340` | 사건구분이 `가합` 고정 | 사건부호 사전 확장 |
| `immigration` 출입국 | 날짜 + 노선 + 출입국 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:341` | 항공권/여권/비자와 무관 | 여권/비자/항공권 연결 |
| `visa` 비자 | 체류자격 + 8자리 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:342` | 발급번호 체계 없음 | 체류자격별 문서 패턴 |
| `voter` 선거인 | 선거인번호 + 임의 숫자 | 보강 필요 | `korean_pii_fuzzer_v4.py:343` | 실제 선거인명부 형식 근거 없음 | 선거 문서 샘플 기반 |
| `property` 부동산등기 | 임의 3블록 번호 | 보강 필요 | `korean_pii_fuzzer_v4.py:344` | 등기번호/부동산고유번호 규칙 없음 | 등기 문서 필드 체계 반영 |
| `gps` GPS좌표 | 한국 일부 bbox 좌표 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:345` | 주소와 무관 | 주소 geocode 근처 좌표 |
| `flight` 항공권 | 항공편+노선+2026 날짜 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:347` | PNR/티켓번호 아님 | PNR/전자항공권/스케줄 분리 |
| `orientation` 성적지향 | 3개 값 | 대충 형식만 유효 | `korean_pii_fuzzer_v4.py:435` | 작은 민감속성 사전 | 분류 목적에 맞춘 라벨 체계 |

## 개선 작업 원칙

1. 먼저 bundle primary 또는 bundle 포함 타입부터 고친다: `account`, `emp_id`, `work_email`, `transaction` (`prescription`, `medical_rec` 완료).
2. 한국 기준의 실제 제도/기관별 규칙이 있는 타입은 임의 숫자 생성을 줄이고, 기관별 pattern table 또는 checker를 둔다.
3. profile bundle에서는 독립 `gen_*` 호출을 줄이고, 하나의 profile object에서 파생한다.
4. 체크섬형은 generator와 validator를 같이 둔다.
5. semantic dictionary는 작은 하드코딩이면 최소한 출처/도메인/사용 맥락을 metadata로 남긴다.
6. metadata의 `format_valid`, `rule_valid`, `semantic_valid`는 최종적으로 실제 validator 결과로 기록되게 바꾼다.

## 바로 사용 가능한 bundle 후보

현재 상태에서 안전하게 시작하려면 아래처럼 제한한다.

| 도메인 | 권장 구성 |
|---|---|
| CRM | `name`, corpus `address`, `phone`, 이름 기반 `email`, 은행명 포함 `account` 사용 가능. 단 account는 format+bank context 수준 |
| Healthcare | `name`, `diagnosis`, `prescription`, `allergy`, `surgery`, `hospital`, `medical_rec` (`medical_rec`: 병원별 synthetic rule + validator 기반 사용 가능) |
| Finance | `name`, `rrn`, `card`, corpus `address`, 은행명 포함 `account` 사용. 단 account는 format+bank context 수준이고 `transaction`은 보강 후 사용 |
| HR | `name`, `company`, `dept`, `job_title`, `hire_date`. `emp_id`, `work_email`은 보강 후 사용 |

## 추적용 Top 5

1. `account`: 은행별 실규칙과 bank context를 붙인다.
2. `emp_id`: 회사별 사번 체계와 입사일을 연결한다.
3. `medical_rec`: 병원별 synthetic MRN spec + check digit + validator 적용 완료, bundle metadata 연동 확장만 남음.
4. `prescription`: 완료. 약품별 용량/빈도/경로/복용법/일수 table과 한국어 처방전 변형을 추가했다.
5. `work_email`: 이름 romanization과 회사 도메인을 연결한다.
