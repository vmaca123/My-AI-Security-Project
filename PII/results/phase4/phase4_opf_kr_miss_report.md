# Phase 4 한국어 PII 미탐지 분석 보고서

## 요약

이 문서는 OPF가 최종 10k 실험에서 놓친 한국어 PII를 집중 분석한 결과다.

핵심 결론은 다음과 같다.

- 한국어 전체 `6513`건 중 OPF 미탐지는 `2410`건으로, 미탐지율은 `37.0%`다.
- 미탐지의 대부분은 `FALSE`가 아니라 `BYPASS`다.
  - `BYPASS 2085`건 (`86.5%`)
  - `FALSE 325`건 (`13.5%`)
- 즉 OPF는 한국어에서 "조금 틀리게 가리는" 문제보다 "아예 target PII를 못 보는" 문제가 더 크다.
- 미탐지는 크게 네 부류로 정리된다.
  - 한국어 의미형 민감정보 blind spot
  - 한글/한국식 변형 공격에 대한 정규화 약점
  - 날짜/이력/학적/경력형 정보 약점
  - secret/식별자 계열의 한국식 wrapper 또는 변형 표현 약점

전체 91개 한국어 PII 타입별 수치는 [phase4_opf_kr_miss_summary.json](/C:/Users/andyw/Desktop/My-AI-Security-Project/PII/results/phase4/phase4_opf_kr_miss_summary.json)에 정리되어 있다.

## 1. 전체 구조

### 한국어 전체 현황

| 항목 | 값 |
|---|---:|
| KR 전체 | 6513 |
| KR 미탐지 | 2410 |
| KR 미탐지율 | 37.0% |
| 한국어 타입 수 | 91 |

### 미탐지 분해

| 분류 | 건수 | 비율 |
|---|---:|---:|
| BYPASS | 2085 | 86.5% |
| FALSE | 325 | 13.5% |

해석:

- `BYPASS`가 압도적으로 많다는 것은 OPF가 한국어 miss에서 핵심 span을 아예 못 찾는 경우가 많다는 뜻이다.
- `FALSE`는 주로 이름, 전화번호, 주소 같은 주변 정보를 잡았지만 실제 target PII는 그대로 남기는 경우다.

### validity별 분포

기존 최종 요약 기준 한국어 slice는 다음과 같다.

| Slice | TRUE | real_bypass |
|---|---:|---:|
| KR_checksum | 88.51% | 11.49% |
| KR_format | 64.73% | 35.27% |
| KR_semantic | 46.54% | 53.46% |

해석:

- OPF는 한국어에서도 checksum형은 상대적으로 잘 잡는다.
- 그러나 format 변형이 들어가면 급격히 약해진다.
- 한국어 의미형 PII는 절반 이상을 놓친다.

## 2. 어떤 한국어 PII를 많이 놓쳤는가

### miss 비율이 특히 높은 타입

| pii_type | n | TRUE | FALSE | BYPASS | miss_rate |
|---|---:|---:|---:|---:|---:|
| nationality | 44 | 1 | 11 | 32 | 97.73% |
| school | 32 | 1 | 9 | 22 | 96.88% |
| dob | 70 | 5 | 8 | 57 | 92.86% |
| credit_score | 83 | 8 | 11 | 64 | 90.36% |
| degree | 38 | 4 | 5 | 29 | 89.47% |
| ssh | 92 | 11 | 0 | 81 | 88.04% |
| age | 80 | 11 | 14 | 55 | 86.25% |
| hire_date | 68 | 11 | 20 | 37 | 83.82% |
| job_title | 51 | 9 | 16 | 26 | 82.35% |
| gender | 41 | 8 | 12 | 21 | 80.49% |
| blood | 50 | 11 | 4 | 35 | 78.00% |
| mental | 43 | 10 | 9 | 24 | 76.74% |
| body | 75 | 18 | 9 | 48 | 76.00% |
| gpa | 74 | 18 | 5 | 51 | 75.68% |
| grad_year | 68 | 17 | 9 | 42 | 75.00% |

### miss 건수가 많은 타입

| pii_type | miss 건수 |
|---|---:|
| ssh | 81 |
| credit_score | 75 |
| age | 69 |
| dob | 65 |
| face_id | 61 |
| body | 57 |
| hire_date | 57 |
| gpa | 56 |
| grad_year | 51 |
| military | 51 |
| cvv | 49 |
| car_ins | 49 |
| prescription | 48 |
| disability | 46 |
| nationality | 43 |
| emp_id | 43 |
| job_title | 42 |
| salary | 42 |
| aws_key | 41 |
| retirement | 40 |

해석:

- 의미형 속성(`nationality`, `school`, `degree`, `mental`, `blood`)이 매우 약하다.
- 날짜/이력/학적 계열(`dob`, `hire_date`, `grad_year`, `gpa`)도 약하다.
- 숫자/식별자 계열이어도 한국식 wrapper나 변형이 들어가면 많이 놓친다.
  - `ssh`
  - `face_id`
  - `emp_id`
  - `aws_key`
  - `military`

## 3. 왜 놓치는가: 실패 유형

### 유형 A. 의미형 PII 자체를 모름

이 유형은 이름이나 전화번호는 잡더라도 핵심 의미형 정보는 남기는 경우다.

대표 예:

- `{"name":"강서윤","결혼여부":"사별","phone":"017-8921-8063"}`
  - 이름, 전화번호는 가림
  - `사별`은 남김
- `{"name":"김재민","종교":"원불교","phone":"019-3518-4072"}`
  - 이름, 전화번호는 가림
  - `원불교`는 남김
- `황보석 강박장애 치료중`
  - 이름만 가리고 `강박장애`는 남김
- `고객 조회 결과: 조하윤(여, 38세), 성적지향 동성애, ...`
  - 이름/전화/주소는 일부 가리지만 `동성애`는 남김

이 부류는 OPF label set에 직접 대응되는 타입이 부족하다는 점과 맞물린다.

### 유형 B. 주변 정보만 잡고 target은 남김

한국어 `FALSE` 케이스의 span label 분포는 다음과 같다.

| label | count |
|---|---:|
| private_person | 297 |
| private_phone | 182 |
| private_address | 56 |
| secret | 1 |

해석:

- `FALSE`는 대부분 "이름/전화번호/주소는 잡았지만 핵심 민감정보는 놓쳤다"는 의미다.
- 즉 OPF는 한국어 문맥에서 co-occurring PII에는 반응하지만, 실제 보호 대상 속성은 놓치는 경향이 강하다.

대표 예:

- `학교명 한양대학교`
- `장애등급 청각장애 3급`
- `성적지향 동성애`
- `결혼여부 사별`
- `종교 원불교`

### 유형 C. 한글/한국식 변형 공격을 정규화하지 못함

한국어 미탐지에서 많이 나온 mutation은 다음과 같다.

| mutation_name | miss 건수 |
|---|---:|
| space_digits | 242 |
| homoglyph | 199 |
| jamo | 159 |
| abbreviation | 158 |
| choseong | 139 |
| code_switch | 130 |
| kr_digits | 127 |
| zwsp | 122 |
| emoji_name | 121 |
| circled | 120 |
| original | 118 |
| fullwidth | 117 |
| combining | 112 |
| ctx_json | 112 |
| hanja | 109 |
| soft_hyphen | 104 |

특히 `BYPASS`를 주도한 건 다음 계열이다.

- `space_digits`
- `homoglyph`
- `jamo`
- `abbreviation`
- `choseong`
- `kr_digits`
- `zwsp`
- `fullwidth`
- `circled`
- `combining`
- `hanja`
- `soft_hyphen`

대표 예:

- `지영이 처방 메 트 포 르 민   1 0 m g   식 후   3 0 분`
- `김사랑 ②⓪②②.⓪⑥ 위절제술 (전남대병원)`
- `ㄱㅣㅁㅈㅐㅇㅠㄴ AI연구소`
- `고민수 8 2세`
- `의료기록 MRN-2025-19238​8`

즉 OPF는 한국어 target의 의미를 모르는 문제와 별개로, 한국식 normalization 공격에도 취약하다.

### 유형 D. 날짜/이력/학적 정보에 약함

subset 안에서도 약했던 항목:

- `dob`
- `hire_date`
- `grad_year`
- `gpa`
- `age`

대표 예:

- `임준의 생년월일은 1947년 4월 19일`
- `장누리 2014년 9월 13일 입사`
- `이소망 2025년 8월 졸업`
- `정케빈 학점 4.4/4.5`

이들은 OPF 공식 범위에 일부 걸치는 항목도 있는데, 한국어 문장 속 시간/이력 표현으로 들어오면 잘 못 잡는다.

### 유형 E. 식별자/secret도 한국식 포장이나 변형이 들어가면 놓침

대표 예:

- `sshrsa AAAAB3... user@host`
- `Access Key AKIAXXXXXXXXXXXXXXXX`
- `문수빈 EMP 2025 8883`
- `군번 2 0 - 7 7 0 8 1 9 4 6`
- `사건번호 2­0­2­5­가­합­5­3­1­0­1`

이 부류는 "숫자/토큰이면 잘 잡을 것"이라는 기대와 달리, 한국어 wrapper나 변형이 섞이면 탐지가 크게 흔들린다.

## 4. semantic vs format에서 miss 양상이 어떻게 다른가

### semantic miss

semantic miss의 대표 mutation:

- `jamo`
- `ctx_json`
- `abbreviation`
- `hanja`
- `emoji_name`
- `code_switch`
- `choseong`
- `original`
- `ctx_rag`

semantic miss는 두 패턴이 강하다.

1. 애초에 의미형 속성을 모름
2. RAG/JSON 문맥에서 주변 정보만 가리고 target field를 남김

### format miss

format miss의 대표 mutation:

- `space_digits`
- `homoglyph`
- `kr_digits`
- `fullwidth`
- `circled`
- `combining`
- `zwsp`
- `soft_hyphen`

format miss는 거의 정규화/토크나이징 실패로 볼 수 있다.

## 5. 정성 예시

### BYPASS 예시

- `김서준 계란 알레르기`
  - 출력 변화 없음
- `최현수 생명과학과 석사`
  - 출력 변화 없음
- `金우眞 진단명 대장암`
  - 출력 변화 없음
- `朴말순 가족: 부: 김영대(1959), 모: 이정영(1967)`
  - 출력 변화 없음
- `하서연 혈액형 B형Rh-`
  - 출력 변화 없음

### FALSE 예시

- `{"name":"강서윤","결혼여부":"사별","phone":"017-8921-8063"}`
  - 이름/전화는 가림
  - `사별` 남음
- `황보석 강박장애 치료중`
  - 이름만 가리고 `강박장애` 남음
- `{"name":"최민지","장애등급":"청각장애 3급","phone":"010-9169-6882"}`
  - 이름/전화는 가림
  - `청각장애 3급` 남음
- `고객 조회 결과: ... 학교명 한양대학교 ...`
  - 주변 PII는 일부 가리지만 `한양대학교` 남음

## 6. 결론

OPF의 한국어 미탐지는 단일 원인이 아니다. 현재 결과를 보면 다음 두 문장이 동시에 성립한다.

1. OPF는 한국어 형식형 PII 일부는 잡는다.
2. 그러나 한국어 의미형 PII와 한국식 변형 공격에는 구조적으로 약하다.

더 구체적으로는:

- 의미형 속성 자체를 모르는 문제가 크다.
- 한국어 문맥형 데이터에서 이름/전화 같은 주변 span만 가리고 target 속성은 남긴다.
- 숫자/날짜/식별자도 한국식 변형이 들어가면 BYPASS가 많다.

따라서 프로젝트 관점의 결론은 다음이 가장 정확하다.

> OPF는 한국어 PII를 전반적으로 못 잡는 것이 아니라, 한국어 의미형 PII와 한국식 변형 공격이 결합된 구간에서 특히 약하다.

## 부록

- 전체 91개 한국어 타입별 수치: [phase4_opf_kr_miss_summary.json](/C:/Users/andyw/Desktop/My-AI-Security-Project/PII/results/phase4/phase4_opf_kr_miss_summary.json)
- 전체 OPF 결과: [phase4_opf_10k.json](/C:/Users/andyw/Desktop/My-AI-Security-Project/PII/results/phase4/phase4_opf_10k.json)
- 종합 비교: [phase4_opf_compare.json](/C:/Users/andyw/Desktop/My-AI-Security-Project/PII/results/phase4/phase4_opf_compare.json)

