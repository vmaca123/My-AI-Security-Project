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

## 33종 PII 탐지 카테고리

**정규식 기반 (17)**: rrn(주민번호), brn(사업자번호), frn(외국인등록번호), driver, passport, phone, landline, account, card, jwt, ssh, session, gps, mac, ip, vin, plate

**키워드 사전 기반 (16, 텍스트형 PII)**: allergy(알레르기), prescription(처방), surgery(수술), diagnosis(진단), blood(혈액형), body(신체정보), salary(연봉), retirement(퇴직), company(회사), job_title(직책), dept(부서), degree(학위), gpa, family(가족관계), marital(혼인), religion(종교)
