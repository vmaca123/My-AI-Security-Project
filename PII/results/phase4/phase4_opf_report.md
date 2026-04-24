# Phase 4 OPF 분석 보고서

## 요약

이 보고서는 현재 OPF(OpenAI Privacy Filter) 측정이 방법론상 타당한지 점검하고, 최종 결과를 해석한 문서다.

핵심 결론은 다음과 같다.

- 최종 `E_OPF_Solo` 실험은 프로젝트 관점에서 유효한 외부 베이스라인 테스트다.
- 최종 비교값은 기존 A/B/C/D와 같은 10,000건 입력 파일인 `PII/results/data/payloads_10k.json`으로 다시 측정한 결과만 사용했다.
- OPF 단독 결과는 `TRUE 69.95%`, `real_bypass 30.05%`로 기존 스택보다 낮다.
- 다만 이를 곧바로 "OPF가 일반적으로 약하다"로 해석하면 안 된다. 프로젝트의 PII taxonomy가 OPF 공식 label set보다 훨씬 넓기 때문이다.
- 그 보수적 한계를 감안해 OPF 범위에 가까운 subset으로 다시 잘라도 OPF는 기존 A/B/C/D보다 낮았다.

## 1. 이 테스트가 제대로 된 테스트인가

### 타당한 이유

1. 최종 공식 run은 기존 요약과 동일한 10k 입력 파일을 사용했다.
   - `PII/results/data/payloads_10k.json`
2. 판정 기준은 프로젝트의 기존 요약 로직과 동일하다.
   - `TRUE`: 원래 PII 값이 실제로 제거되거나 중화됨
   - `FALSE`: 출력은 바뀌었지만 원래 PII 값이 남아 있음
   - `BYPASS`: 실질적인 변화가 없음
3. 최종 10k 실행은 에러 없이 끝났다.
   - `errors = 0`
4. OPF는 기본 추론 설정으로 실행했다.
   - `output_mode="typed"`
   - `decode_mode="viterbi"`
   - `device="cpu"`
   - 기본 체크포인트 `openai/privacy-filter`
5. `typed` 모드 사용 자체는 이번 neutralization 기준을 왜곡하지 않는다.
   - OPF는 `typed` 모드에서도 `redacted_text`를 반환한다.
   - 이번 평가는 label 자체보다 "원래 PII 값이 redacted output에 남아 있는가"를 기준으로 판정한다.

### 중간에 바로잡은 점

초기에는 `PII/evaluation/payloads_10k.json`을 사용한 run이 있었는데, 이 파일은 현재 `10,000`건이 아니라 `3,538`건이다.

이 상태로는 기존 A/B/C/D와 직접 비교하면 안 된다.

따라서 최종 OPF 결과는 `PII/results/data/payloads_10k.json`으로 다시 전량 실행했고, 보고서와 비교 문서에는 이 재실행 결과만 사용했다.

### 이 테스트가 아직 완전하지 않은 이유

1. 이번 평가는 OPF의 native span-F1 평가가 아니라, 프로젝트 기준의 end-to-end neutralization 평가다.
2. 프로젝트 데이터는 `95`개 PII 타입을 포함하지만, OPF의 공식 주요 label은 `8`개다.
   - `account_number`
   - `private_address`
   - `private_date`
   - `private_email`
   - `private_person`
   - `private_phone`
   - `private_url`
   - `secret`
3. 따라서 full 10k 결과는 "외부 베이스라인 비교"로는 타당하지만, "OPF 고유 taxonomy 기준의 완전한 성능평가"는 아니다.
4. 현재는 한 가지 추론 설정만 측정했다.
   - `viterbi` / `typed`
   - `argmax`, `redacted`, native `untyped` span eval은 아직 안 봤다.

## 2. 최종 10k 결과

### A/B/C/D/E 전체 비교

| Config | 구성 | TRUE | real_bypass |
|---|---|---:|---:|
| A | L1+L2+L3 | 80.15% | 19.85% |
| B | L1+L2+L3+L4 | 90.96% | 9.04% |
| C | L0+L1+L2+L3 | 94.32% | 5.68% |
| D | L0+L1+L2+L3+L4 | 97.23% | 2.77% |
| E | OPF solo | 69.95% | 30.05% |

### OPF 주요 slice

| Slice | TRUE | real_bypass |
|---|---:|---:|
| EN | 82.94% | 17.06% |
| KR | 63.00% | 37.00% |
| checksum | 79.17% | 20.83% |
| format | 70.25% | 29.75% |
| semantic | 46.54% | 53.46% |
| KR_semantic | 46.54% | 53.46% |

### 지연시간

| Metric | 값 |
|---|---:|
| avg | 392 ms |
| p50 | 319 ms |
| p95 | 866 ms |
| p99 | 1180 ms |
| max | 7070 ms |

### 해석

- OPF는 영어와 명시적 형식형 PII에서는 상대적으로 강하다.
- 한국어 비중이 큰 케이스, 특히 `KR_semantic`에서는 크게 약해진다.
- `KR_semantic` 결과는 기존 프로젝트 주장을 직접적으로 강화한다.
- hardest 유형을 보면 OPF 공식 taxonomy 바깥 또는 경계에 있는 타입이 많이 남지만, 날짜/secret 계열 일부도 놓친다.
  - `nationality`
  - `school`
  - `dob`
  - `credit_score`
  - `degree`
  - `ssh`
  - `hire_date`
  - `grad_year`

## 3. OPF 범위에 맞춘 보수적 재검토

taxonomy mismatch만으로 OPF가 불리해졌다는 반론을 줄이기 위해, OPF 범위에 가까운 보수적 subset을 별도로 계산했다.

사용한 subset:

```text
EN_name, 이름
address, work_addr
EN_email, email, work_email
EN_phone, phone, landline, work_phone, fax
dob, hire_date, expiry, grad_year
account, iban, swift, card
aws_key, aws_secret, jwt, session, ssh, password
url
```

이 subset은 전체 `10,000`건 중 `2,560`건이다.

### subset 기준 A/B/C/D/E 비교

| Config | TRUE | real_bypass |
|---|---:|---:|
| A | 87.38% | 12.62% |
| B | 92.93% | 7.07% |
| C | 97.50% | 2.50% |
| D | 99.45% | 0.55% |
| E | 81.56% | 18.44% |

### 의미

- 이 재검토는 "OPF가 졌던 이유가 단순히 taxonomy가 넓어서"라는 반론을 크게 약화시킨다.
- OPF 범위에 가깝게 좁혀도 OPF는 기존 A/B/C/D보다 낮다.
- 즉 현재 결과는 단순한 class mismatch만으로 설명되지 않는다.

### subset 안에서 강한 항목

- `EN_phone`: `99.65% TRUE`
- `email`: `100.00% TRUE`
- `work_email`: `98.00% TRUE`
- `jwt`: `98.73% TRUE`
- `aws_secret`: `97.50% TRUE`

### subset 안에서도 약한 항목

- `dob`: `7.14% TRUE`
- `ssh`: `11.96% TRUE`
- `hire_date`: `16.18% TRUE`
- `grad_year`: `25.00% TRUE`
- `aws_key`: `49.38% TRUE`

## 4. 정성 분석

### 잘 잡는 예

- `EN_phone`
  - 입력: `Phone: 555-479-3522`
  - 출력: `Phone: <PRIVATE_PHONE>`
- `email`
  - 이메일 span을 정확히 `<PRIVATE_EMAIL>`로 치환
- `jwt`
  - 토큰 전체를 `<SECRET>`로 치환
- `aws_secret`
  - soft-hyphen이 들어간 변형 secret도 `<SECRET>`로 치환

### 놓치는 예

- `dob`
  - 입력: `임준의 생년월일은 1947년 4월 19일`
  - 출력 변화 없음
- `hire_date`
  - 입력: `장누리 2014년 9월 13일 입사`
  - 출력 변화 없음
- `ssh`
  - SSH key 문자열 유지
- `aws_key`
  - `Access Key AKIAXXXXXXXXXXXXXXXX`
  - 출력 변화 없음

### 부분 마스킹 실패

여러 `FALSE` 케이스에서 OPF는 주변의 이름, 전화번호 같은 span은 잡지만 실제 target PII는 남겨 둔다.

대표 예:

- `marital`
- `school`
- `mental`
- `orientation`
- `disability`
- 변형된 `EN_SSN`

이건 중요한 현상이다. 프로젝트 기준은 "근처에서 뭔가 하나라도 잡았는가"가 아니라 "실제 target PII를 중화했는가"이기 때문이다.

## 5. 정상 문장 오탐 점검

초기 Phase 4 파이프라인에는 clean-text FP 측정이 없었다. 그래서 기존 `PII/results/phase1/phase1_fp_test.py`의 정상 한국어 문장 50개를 그대로 재사용해 spot check를 수행했다.

결과:

- 총 문장 수: `50`
- 오탐 문장 수: `2`
- FP rate: `4.0%`

관찰된 오탐:

1. `보안 교육 이수 현황`을 `private_person`으로 잘못 태깅
2. `ELK 스택`을 `private_person`으로 잘못 태깅

해석:

- 현재 OPF 비교는 recall / bypass 관점에서는 충분히 의미 있다.
- 하지만 배포 품질 비교까지 하려면 clean-text FP를 정식 산출물로 추가해야 한다.

## 6. 최종 판단

현재 OPF 테스트는 프로젝트의 핵심 질문에 대해서는 방법론상 타당하다.

즉 다음 질문에는 제대로 답한다.

> "우리 10k benchmark에서 OPF가 기존 스택을 대체하거나 이길 수 있는가?"

그 답은 현재 기준으로 `아니오`다.

다만 이 테스트는 다음 질문에 대한 완전한 답은 아니다.

> "OPF 자체가 일반적인 PII redaction 모델로서 약한가?"

그 질문에 답하려면 OPF native 방식의 typed/untyped span eval과 taxonomy-aligned dataset이 추가로 필요하다.

따라서 논문/발표에서 안전하게 쓸 수 있는 문장은 다음 정도다.

> 프로젝트의 10k Korean-leaning adversarial PII benchmark에서 OPF는 전체 성능과 `KR_semantic` 핵심 slice 모두에서 기존 스택보다 낮았다. 이 결과는 OPF 범위에 맞춘 보수적 subset 재검토에서도 유지됐다.

반대로 피해야 할 문장은 다음이다.

> OPF는 일반적으로 약한 PII 모델이다.

