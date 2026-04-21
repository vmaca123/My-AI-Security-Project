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

주의: `format_valid`, `rule_valid`, `semantic_valid`는 현재 실제 validator 결과가 아니라 `_add()`에서 항상 `True`로 기록된다. 따라서 이 문서의 판정은 metadata가 아니라 생성 로직을 기준으로 한다.

### 출력 퍼저

`korean_pii_output_fuzzer_v4.py`는 LLM 응답처럼 보이는 문장, JSON, log, table, partial mask 형식을 만들고, 4개 업무 번들을 생성한다.

현재 bundle 구성:

| 번들 | 포함 타입 | 현재 리스크 |
|---|---|---|
| CRM | `phone`, `email`, `address`, `account` | `account`가 P0, `address`는 seed/corpus 강제 필요 |
| Healthcare | `diagnosis`, `prescription`, `allergy`, `hospital`, `medical_rec` | `prescription`, `medical_rec`가 P0 |
| Finance | `rrn`, `card`, `account`, `transaction` | `account`, `transaction`이 P0 |
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
| `account` 계좌번호 | 은행별로 보이는 임의 숫자 block 생성, `PII_TYPES`에서는 번호만 사용 | 보강 필요 | `korean_pii_fuzzer_v4.py:298`, output CRM/Finance bundle | 은행별 실제 계좌 규칙/체크섬 없음, 은행명 context가 bundle에서 사라짐 | 은행별 패턴 사전, 은행명+계좌번호 pair 유지, 가능하면 체크 digit/상품코드 반영 |
| `transaction` 거래내역 | 2026년 임의 날짜 + 5개 가맹점 + 금액 | 보강 필요 | `korean_pii_fuzzer_v4.py:305`, Finance bundle | 현재일 이후 미래 날짜 가능, 카드/계좌/가맹점/MCC와 무관 | 기준일 이전 날짜, 업종별 금액 분포, 계좌/카드와 연결 |
| `prescription` 처방전 | 약품 20개, 용량 10개, 빈도 6개를 무작위 결합 | 보강 필요 | `korean_pii_fuzzer_v4.py:365`, `korean_pii_fuzzer_v4.py:438`, Healthcare bundle | 약품별 허용 용량/빈도가 맞지 않을 수 있음 | 약품별 dose/frequency table, 진단명과 처방 연결 |
| `medical_rec` 의료기록번호 | `MRN-YYYY-6digits` | 보강 필요 | `korean_pii_fuzzer_v4.py:313`, Healthcare bundle | 병원별 MRN 규칙이 없음 | 병원별 prefix/자리수/연도 포함 여부를 profile schema로 관리 |
| `emp_id` 사번 | `EMP/사번-YYYY-4digits` | 보강 필요 | `korean_pii_fuzzer_v4.py:326`, HR bundle primary | 회사별 사번 체계 없음, 입사일과 불일치 가능 | 회사별 prefix, 입사연도, 순번 규칙으로 생성 |
| `work_email` 업무이메일 | 3개 local-part + 4개 회사 도메인 | 보강 필요 | `korean_pii_fuzzer_v4.py:328`, HR bundle | 이름/회사와 불일치 가능 | 이름 romanization 기반 local-part, 회사 도메인 mapping |

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

1. 먼저 bundle primary 또는 bundle 포함 타입부터 고친다: `account`, `medical_rec`, `emp_id`, `work_email`, `prescription`, `transaction`.
2. 한국 기준의 실제 제도/기관별 규칙이 있는 타입은 임의 숫자 생성을 줄이고, 기관별 pattern table 또는 checker를 둔다.
3. profile bundle에서는 독립 `gen_*` 호출을 줄이고, 하나의 profile object에서 파생한다.
4. 체크섬형은 generator와 validator를 같이 둔다.
5. semantic dictionary는 작은 하드코딩이면 최소한 출처/도메인/사용 맥락을 metadata로 남긴다.
6. metadata의 `format_valid`, `rule_valid`, `semantic_valid`는 최종적으로 실제 validator 결과로 기록되게 바꾼다.

## 바로 사용 가능한 bundle 후보

현재 상태에서 안전하게 시작하려면 아래처럼 제한한다.

| 도메인 | 권장 구성 |
|---|---|
| CRM | `name`, corpus `address`, `phone`, 이름 기반 `email` 보강 후 사용. `account`는 보강 전 제외 |
| Healthcare | `name`, `diagnosis`, `allergy`, `surgery`, `hospital`. `prescription`, `medical_rec`는 보강 후 사용 |
| Finance | `name`, `rrn`, `card`, corpus `address`. `account`, `transaction`은 보강 후 사용 |
| HR | `name`, `company`, `dept`, `job_title`, `hire_date`. `emp_id`, `work_email`은 보강 후 사용 |

## 추적용 Top 5

1. `account`: 은행별 실규칙과 bank context를 붙인다.
2. `emp_id`: 회사별 사번 체계와 입사일을 연결한다.
3. `medical_rec`: 병원별 MRN 규칙을 만든다.
4. `prescription`: 약품별 용량/빈도 table을 만든다.
5. `work_email`: 이름 romanization과 회사 도메인을 연결한다.
