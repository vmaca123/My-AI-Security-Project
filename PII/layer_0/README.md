# Layer 0 — Korean PII Normalizer + Detector

LLM Gateway의 한국어 PII 가드레일 다층 방어에서 **가장 앞단**에 위치하는 한국어 특화 전처리 + 탐지 계층.

## 역할

기존 영어 중심 가드레일(Presidio · Bedrock · Lakera · LLM judge)이 잘 못 잡는 **한국어 PII**, 특히 **텍스트형(semantic) PII**(알레르기, 처방, 사건번호, 가족관계, 연봉 등)를 사전에 정규화하고 직접 탐지한다.

```
User Input
    │
    ▼
┌──────────────────┐
│ Layer 0          │  ← 한국어 정규화 + 33종 PII 탐지
│  (Korean)        │
└──────────────────┘
    │
    ▼  (정규화된 텍스트, 또는 BLOCK)
Presidio → Bedrock → Lakera → LLM (GPT/Claude) → GPT-4o Judge
```

## 구성 파일

| 파일 | 역할 |
|------|------|
| `korean_normalizer.py` | 13단계 한국어 정규화 파이프라인 (자모 결합, NFKC, ZWSP/soft-hyphen 제거, 한자→한글, 동형문자 변환 등) |
| `korean_pii_detector.py` | 33종 한국어 PII 탐지 (정규식 17 + 키워드 사전 16) |
| `korean_layer0_guardrail.py` | LiteLLM `CustomGuardrail` 래퍼 — `async_pre_call_hook` + `apply_guardrail` 두 진입점 모두 지원 |

## 핵심 결과 (10,000건 stratified 평가)

| Config | TRUE detection | KR_semantic TRUE |
|---|---:|---:|
| Baseline (L1+L2+L3) | 80.15% | 49.62% |
| Baseline + L4 (GPT-4o-mini judge) | 90.96% | 87.40% |
| **+ Layer 0 (no LLM)** | **94.32%** | **96.39%** |
| Full (L0+L1+L2+L3+L4) | 97.23% | 98.85% |

→ **Layer 0가 GPT-4o judge보다 한국어 텍스트형 PII에서 +8.99%p 더 잘 잡으면서, 비용 $0 · 지연 220배 낮음.**

## LiteLLM 등록

`config.yaml`:
```yaml
guardrails:
  - guardrail_name: "korean-layer0"
    litellm_params:
      guardrail: korean_layer0_guardrail.KoreanLayer0Guard
      mode: "pre_call"
```

## 독립 실행 (LiteLLM 없이)

```python
from korean_layer0_guardrail import KoreanLayer0
layer0 = KoreanLayer0(mode="block", threshold=1)
result = layer0.process("최영희 연봉 7409만원")
# → {"action": "BLOCK", "block_reason": "Korean PII detected: salary", ...}
```

또는 데모 실행:
```bash
python korean_layer0_guardrail.py
```

## 탐지 카테고리

### 정규식 기반 패턴 (42종)

**핵심 토큰형 PII** — session, jwt, crypto, biometric, court, crime, gps, aws_key, aws_secret, ssh, mac, ip, salary, retirement, credit_score, body, gpa, political, family, dob, hire_date, grad_year

**v2 보강 (P0 — bundle primary)** — `medical_rec`(MRN), `emp_id`(EMP/사번)

**v2 보강 (P1 — 자주 유출되는 구조화 토큰)** — `driver`(운전면허), `passport`(여권), `biz_reg`(사업자등록번호), `plate`(번호판), `parcel`(택배송장), `cctv`, `transaction_id`(TRX...), `approval_code`(승인번호), `voice`(녹취록), `visa`(체류자격), `flight`(항공편), `vehicle_reg`(차량등록), `insurance4`(4대보험), `ins_policy`(보험증권), `immigration`(출입국), `student_id`(학번), `stock`(증권계좌)

**숫자형 PII 백업** — `rrn_pattern`, `phone_kr`, `card`, `vin` (Presidio/Bedrock 뚫린 경우 대비)

### 키워드 사전 기반 (22종, 텍스트형 PII)

**v1 기본** — allergy, diagnosis, prescription, surgery, disability, blood, religion, marital, gender, orientation, nationality, mental, school, degree, job_title, company, dept, course_grade

**v2 보강 (P0/P1)** — `work_email`(한국 회사 도메인 사전), `hospital_doctor`(병원+진료과+교수), `transaction`(거래구분 + partner), `car_ins`(손해보험사 + 증권번호)

### False Positive 방지

- `gender`: "남"/"여" 단독 제거 (강남·여권 등에서 오탐 방지) — "남성"/"여성"만 매칭
- `vin`: "VIN:" 또는 "차대번호" 컨텍스트 요구 (TRX 거래번호와 구분)
- 컨텍스트 필요 패턴 다수: `biz_reg`, `plate`, `transaction_id`, `approval_code`, `student_id`

## v4 퍼저와의 호환성

[PII/fuzzer](../fuzzer/) 의 v4 출력(91+ PII types)과 직접 호환:

| 퍼저 vg (validity_group) | Layer 0 탐지 커버리지 |
|---|---|
| checksum | rrn, biz_reg, card, driver, passport (패턴 매칭 — 체크섬 검증은 없음) |
| format | phone, jwt, ssh, mac, ip, aws_key/secret, session, student_id, stock, flight, visa, vehicle_reg 등 대부분 커버 |
| semantic | allergy, diagnosis, prescription, surgery, disability, blood, religion, marital, mental, school, company, dept, degree, orientation, nationality, transaction, work_email, hospital_doctor, car_ins — 키워드 사전으로 직접 매칭 |
