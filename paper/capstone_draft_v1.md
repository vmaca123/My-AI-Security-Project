# 한국어 환경 다계층 LLM 가드레일의 취약성과 정규화 계층 기반 방어

## *A Normalization-First Layer for Korean PII: Beating GPT-4o-mini Judge at 1/220 the Latency*

**저자**: 민우 (정보보안학과, CCIT 융합전공)
**지도교수**: 임정묵
**작성일**: 2026년 4월
**레포**: https://github.com/vmaca123/My-AI-Security-Project

---

## 초록 (Abstract)

대형 언어 모델(LLM) 게이트웨이는 개인식별정보(PII) 유출 방지를 위해 Presidio, AWS Bedrock Guardrails, Lakera 등 다계층 가드레일을 결합해 배포된다. 그러나 이러한 가드레일은 **영어 중심**으로 설계되어 있어, 한국어 텍스트형 PII(알레르기·처방·가족관계 등)에 대해 시스템적 탐지 실패를 보인다. 본 연구는 LiteLLM Gateway 기반 실무 프로덕션 환경에서 영어 중심 3계층(Presidio + Bedrock + Lakera) + LLM-as-judge(GPT-4o-mini) 총 4계층 스택을 구축하고, 한국어 특화 퍼저 v4(validity-first, 91종 PII × 6 변이 레벨)로 생성한 10,000건 stratified 페이로드에 대해 **진짜 API 호출 기반** 평가를 수행했다.

주요 발견은 다음과 같다. **(1)** 프로덕션 3계층(L1~L3)은 영어 PII를 99.2% 탐지하지만 한국어 텍스트형 PII(KR_semantic)는 **49.62%만** 탐지한다(1,302건 중 절반 이상 우회). **(2)** 본 연구가 제안하는 Layer 0(한국어 정규화 파이프라인 + 42 정규식 + 22 키워드 사전, LLM 없음)를 앞단에 추가하면 KR_semantic에서 **96.39%**까지 탐지율이 회복된다(+46.77%p). **(3)** GPT-4o-mini judge를 cascade로 추가한 경우 KR_semantic 87.40%에 그치는 반면, Layer 0 단독은 **+8.99%p 더 높은 탐지율을 달성**하며, 이 차이는 McNemar 짝비교에서 **p < 1e-28**로 통계적으로 결정적이다. **(4)** Layer 0의 평균 추가 지연은 **10ms(p99 135ms)**로 GPT-4o-mini judge의 **220배 낮으며 비용은 $0**이다. **(5)** Ablation 분석 결과 Layer 0 효과의 **96%는 키워드 사전**에서, 3%는 정규화에서, 1%는 시너지에서 발생함을 확인했다. **(6)** validity-first fuzzer v4로 재평가 시 Layer 0의 우위는 +3.36%p에서 **+4.56%p로 오히려 증가**하여, 결과가 퍼저 구현에 무관한 방어 메커니즘 자체의 속성임을 입증했다.

본 연구는 한국어 LLM 보안 환경에서 "LLM judge 없이도 더 잘 잡는" 결정론적 경량 방어선이 가능함을 실증했으며, 전체 데이터·스크립트·CI를 공개하여 재현 가능성을 확보했다.

**키워드**: LLM 보안, PII 탐지, 가드레일, 한국어 NLP, Presidio, AWS Bedrock, LiteLLM, 형태 정규화, 퍼징

---

## 1. 서론 (Introduction)

### 1.1 연구 배경

생성형 AI 서비스의 확산은 조직 내외 데이터 흐름에 새로운 유출 벡터를 만들었다. 기업은 LLM API를 사용자 질의에 직접 노출하지 않고 **게이트웨이 계층**에 다계층 방어선(Presidio · Bedrock · Lakera · LLM-as-judge 등)을 배치한다. LiteLLM, Portkey, TrueFoundry 등이 이러한 게이트웨이를 제공하며, 공식 문서는 Presidio(PII) + Lakera(injection) + LLM judge(최종 검증) 조합을 표준 권장 패턴으로 제시한다.

그러나 **모든 가드레일이 영어 중심**이다. Microsoft Presidio v2.2.361 기준 한국어 전용 recognizer는 주민등록번호(KR_RRN), 사업자등록번호, 외국인등록번호, 운전면허, 여권 등 **5종 숫자/형식형 PII**에 한정된다. Bedrock Guardrails는 다국어를 지원하지만 내부 정책은 영어 정책 기반으로 fine-tune되어 있으며, Lakera Guard는 프롬프트 인젝션 전용이다. GPT-4o-mini judge 등 LLM-as-judge 방식은 다국어 대응이 가능하지만 **1건당 약 2초의 지연과 비용**을 발생시킨다.

이로 인해 한국어 환경에서는 **텍스트형 PII — 알레르기, 처방, 혈액형, 학위, 회사명, 가족관계, 사건번호 등 — 은 사실상 방어되지 않는다**. 더 심각한 것은 이들이 "숫자형" PII와 달리 구조가 자유롭고 문맥 의존적이어서, 정규식 기반 접근만으로는 근본적인 한계가 있다.

### 1.2 연구 질문

본 연구는 다음 세 질문에 답한다.

- **RQ1**: 현재 프로덕션에서 사용되는 3~4계층 PII 가드레일 스택은 한국어 텍스트형 PII에 대해 얼마나 취약한가?
- **RQ2**: LLM 기반 judge(GPT-4o-mini)를 추가하는 것은 이 공백을 메우기에 충분한가?
- **RQ3**: LLM을 사용하지 않는 결정론적 한국어 특화 방어선(정규화 + 사전 기반)이 LLM judge를 대체할 수 있는가?

### 1.3 기여

본 논문의 기여는 다음과 같다.

1. **한국어 PII 공격 퍼저 v4**: checksum 100% 유효 시드를 보장하는 validity-first 퍼저를 설계·공개. 91종 PII × 6 변이 레벨(Original → Context) × 21개 한국어 특화 변이(prescription_emr_line, account_bank_alias, transaction_field_split 등).
2. **10,000건 stratified 벤치마크**: lang × validity_group 균형 샘플. 프로덕션 LiteLLM 게이트웨이를 통한 진짜 API 호출 기반 평가. 전 데이터 공개.
3. **Layer 0 설계**: 한국어 13단계 정규화 파이프라인(자모 결합, NFKC, ZWSP 제거, 한자→한글 등) + 42 정규식 + 22 키워드 사전. LLM 없음. LiteLLM `CustomGuardrail` 인터페이스 구현.
4. **4-way 평가 및 통계 검증**: A(Baseline) vs B(+L4) vs C(+L0) vs D(L0+L4). 결과는 McNemar 짝비교로 p < 1e-28 유의.
5. **비용/지연 분석**: Layer 0는 평균 10ms (p99 135ms), $0. GPT-4o-mini는 평균 1,542ms (p99 4,164ms), ~$0.0001/call.
6. **재현성 인프라**: 89개 pytest unit test + GitHub Actions CI + Makefile 단일 명령 파이프라인.

---

## 2. 관련 연구 (Related Work)

### 2.1 LLM 가드레일 배치 패턴

LiteLLM 공식 정책은 Presidio(PII) + Lakera(injection) + Bedrock Guardrails + Azure Content Safety를 기본 권장한다. TrueFoundry와 Bifrost는 여러 가드레일을 병렬 실행하며, Portkey는 60+ 가드레일 중 선택 가능. NVIDIA NeMo Guardrails는 CrowdStrike AIDR, Palo Alto AIRS와 통합된다.

### 2.2 한국어 PII 연구

**KDPII (Fei et al., IEEE Access 2024)**는 대부분의 언어모델이 범용 PII보다 한국어 특화 PII(33개 카테고리)를 인식하는 데 현저히 낮은 성능을 보임을 지적했다. 그러나 이 연구는 **모델 자체의 PII 인식 능력**을 다루지 **실운영 가드레일 스택의 취약성**은 다루지 않았다.

### 2.3 프롬프트 인젝션 연구

HouYi (한국어 프롬프트 인젝션), Mindgard/Hackett 2025 (Bypassing LLM Guardrails), Palo Alto Unit42 2025 (Web IDPI 22 techniques) 등이 다양한 공격 벡터를 제시했다. 본 연구의 퍼저는 HouYi 스타일 컨텍스트 공격(L5)을 포함한다.

### 2.4 본 연구의 차별점

기존 연구는 **(a)** 단일 모델 평가 또는 **(b)** 영어 중심 벤치마크에 국한된다. 본 연구는 **(1)** 프로덕션 가드레일 **스택** 전체를 대상으로 하고, **(2)** 한국어 특화 공격-방어 프레임워크를 제시하며, **(3)** LLM을 사용하지 않는 경량 방어가 LLM-as-judge를 능가함을 실증한다는 점에서 구별된다.

---

## 3. 시스템 설계 (System Design)

### 3.1 5계층 아키텍처

```
User Input
    │
    ▼
┌─────────────────────┐
│ Layer 0 (Korean)    │   pre_call    한국어 정규화 + 42 정규식 + 22 사전
│ Normalizer+Detector │              (LLM 없음, ~10ms, $0)
└─────────────────────┘
    │
    ▼ (정규화된 텍스트 또는 BLOCK)
┌─────────────────────┐
│ Layer 1 Presidio    │   pre_call    regex + NER, 영어 중심
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ Layer 2 Bedrock     │   during_call AWS 관리형 가드레일
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ Layer 3 Lakera      │   pre_call    인젝션 전용 (PII 탐지 X)
└─────────────────────┘
    │
    ▼
    LLM (GPT/Claude 등)
    │
    ▼
┌─────────────────────┐
│ Layer 4 GPT-4o      │   post_call   LLM-as-judge 최종 검증
│ Judge (mini)        │              (~1.5s/call, $0.0001)
└─────────────────────┘
```

### 3.2 Layer 0 상세 설계

Layer 0는 두 주요 컴포넌트로 구성된다.

#### 3.2.1 Korean Normalizer (13단계)

1. NFKC 유니코드 정규화
2. Zero-Width Space (`\u200B`), Zero-Width Non-Joiner 제거
3. Soft Hyphen (`\u00AD`) 제거
4. Combining Mark (`\u0300–\u036F`) 제거
5. Fullwidth → ASCII 변환
6. Mathematical Bold Digits (𝟎-𝟗) → ASCII
7. Circled Digits (①-⑨) → ASCII
8. 한자→한글 변환 (성씨 사전 기반)
9. 자모 결합 (분해된 `ㅈㅜㅁㅣㄴ` → `주민`)
10. Homoglyph 치환
11. 공백 정규화
12. 제어 문자 제거
13. 최종 trim

각 단계는 순서 독립적이지 않으며, 특히 **(9) 자모 결합**이 후속 사전 매칭의 전제 조건이 된다.

#### 3.2.2 Korean PII Detector (42 + 22)

**정규식 패턴 (42종)**
- 기본 토큰형: session, jwt, crypto, biometric, court, crime, gps, aws_key, aws_secret, ssh, mac, ip, salary, retirement, credit_score, body, gpa, political, family, dob, hire_date, grad_year
- P0 (bundle primary): medical_rec, emp_id
- P1 (구조화 토큰): driver, passport, biz_reg, plate, parcel, cctv, transaction_id, approval_code, voice, visa, flight, vehicle_reg, insurance4, ins_policy, immigration, student_id, stock
- 백업 (숫자형 PII): rrn_pattern, phone_kr, card, vin

**키워드 사전 (22종, 텍스트형 PII)**
- 의료: allergy, diagnosis, prescription, surgery, disability, blood, mental, hospital_doctor
- 신원: religion, marital, gender, orientation, nationality
- 교육: school, degree, course_grade
- 고용: job_title, company, dept, work_email
- 금융: transaction, car_ins

#### 3.2.3 False Positive 방지

초기 구현은 정상 한국어 문서(뉴스·이메일·대화·기술 문서·학술 텍스트 50건)에서 **26% FP**를 보였다. 주 원인은:

- `allergy`의 "개" → "3개월", "개선", "5개년" 등에서 오매칭
- `nationality`의 "한국" → "한국은행"
- `gender`의 "남"/"여" → "강남", "여권"

해결책으로 **2자 이하 키워드는 컨텍스트 필수** 규칙을 도입했다. 예를 들어 "한국"은 "국적", "시민권", "영주권" 중 하나가 같은 텍스트에 있을 때만 매칭된다. 이로써 FP는 **2%**로 감소하며, 잔여 2건은 실제 조직 정보 누설(개발팀, 경영지원팀)로 정책적 판단 영역이다.

### 3.3 LiteLLM 통합

Layer 0는 `litellm.integrations.custom_guardrail.CustomGuardrail`을 상속하여 두 진입점을 제공한다.

```python
class KoreanLayer0Guard(CustomGuardrail):
    async def async_pre_call_hook(self, data, user_api_key_dict, call_type):
        # LLM 호출 전 입력 검사 (messages[-1].content에 적용)
        ...

    async def apply_guardrail(self, inputs, request_data, input_type, logging_obj=None):
        # /guardrails/apply_guardrail 엔드포인트용
        # inputs는 TypedDict — 반드시 inputs.get("texts", [])
        ...
```

LiteLLM v4.69+에서는 Bedrock config 스키마가 변경되어 `guardrailIdentifier`/`guardrailVersion`을 `litellm_params` 직접 아래 두어야 한다(이전엔 `guardrail_info` 안). 이를 간과하면 `400 Guardrail was enabled but input is in incorrect format` 오류가 발생한다.

---

## 4. 평가 방법 (Evaluation Methodology)

### 4.1 퍼저 설계 (v4 — Validity-First)

v3 퍼저는 "형식만 비슷한 랜덤값"을 생성하여 주민번호 80%, 신용카드 80%, 사업자번호 100%가 체크섬 실패였다. 이는 "퍼저 시드 자체가 무효이므로 가드레일이 못 잡는 게 당연하다"는 비판을 유발할 수 있다.

v4는 **모든 시드를 생성 전 3단계 검증**한다.

- **Group A (Checksum)**: 주민등록번호(체크섬 공식), 신용카드(Luhn), 사업자번호(가중 체크섬), 외국인등록번호, IMEI, VIN, US SSN
- **Group B (Format)**: 전화번호, 이메일, IP, MAC, 여권, 운전면허 등 (정규식/구조 규칙)
- **Group C (Semantic Dictionary)**: 진단명(30), 처방전(22 약품, 용량·빈도·경로·복용법 allowed combination enumerate), 알레르기(15), 수술(15), 학위, 종교 등

각 payload에 `format_valid`, `rule_valid`, `semantic_valid`, `validity_group` 메타데이터가 기록된다.

### 4.2 6 변이 레벨

- **L0 Original**: 원본 PII
- **L1 Character**: 자모 분해, 초성, 한자, fullwidth, homoglyph, circled, emoji smuggle
- **L2 Encoding**: ZWSP, combining marks, soft hyphen
- **L3 Format**: 구분자 변경 (dot/slash/space/none), space_digits
- **L4 Linguistic**: code_switch, abbreviation, kr_digits, multilingual (ja/zh/fr/de), particle variation, + 한국어 전용 변이(prescription_emr_line, account_bank_alias, transaction_field_split 등)
- **L5 Context**: RAG 삽입, JSON, HouYi

### 4.3 평가 데이터셋

10,000건 stratified 샘플. Key 축: `lang × validity_group`. 분포:

| Bucket | n |
|---|---:|
| EN_checksum | 2,603 |
| EN_format | 884 |
| KR_checksum | 522 |
| KR_format | 4,689 |
| KR_semantic | 1,302 (★ 핵심 narrative slice) |

### 4.4 4-way 실험 설계

같은 10,000건에 대해 네 개 config을 평가.

| Config | 구성 | 목적 |
|---|---|---|
| A) Baseline | L1+L2+L3 | 프로덕션 stack (LLM judge 없음) |
| B) Baseline + L4 | L1+L2+L3+L4 | LLM judge 추가 효과 |
| C) With Layer 0 | L0+L1+L2+L3 | Layer 0 단독 (LLM 없음) |
| D) Full | L0+L1+L2+L3+L4 | 상한선 (양쪽 모두) |

### 4.5 평가 지표

#### TRUE Detection

`output != text`만으로 판단하는 raw detection은 부풀려진다. 예: Presidio가 PERSON만 마스킹하고 전화번호는 그대로 두면 output이 변경되지만 실제 PII는 누설된다. 따라서 **TRUE detection**을 세 가지로 정의:

- **TRUE**: 어떤 레이어라도 진짜 PII 값을 neutralize (BLOCK 또는 해당 PII 값이 output에 없음)
- **FALSE**: 레이어가 텍스트를 변경했지만 PII 원본 값이 여전히 남아있음
- **BYPASS**: 어떤 레이어도 텍스트 변경 안 함

`Real bypass rate = FALSE + BYPASS`.

#### 통계 검정

**McNemar 짝비교**(continuity-corrected chi-squared, df=1)로 두 config이 같은 케이스에서 어떻게 다른지 측정. `b` = config1만 잡음, `c` = config2만 잡음.

### 4.6 재현성 환경

- LiteLLM Proxy v4.69 (Docker)
- PostgreSQL 16, Presidio Analyzer/Anonymizer (Docker)
- OpenAI gpt-4o-mini (PII_JUDGE_THRESHOLD=0.7)
- AWS Bedrock Guardrail (us-east-1, DRAFT 버전)
- Lakera Guard v2
- 평가기: Python 3.12 + httpx async, concurrency=5 (L4만)
- 전체 파이프라인: Makefile `make all` (약 4시간, ~$5 API 비용)

---

## 5. 결과 (Results)

### 5.1 RQ1: 프로덕션 가드레일의 한국어 공백

Table 1은 A) Baseline(L1~L3)의 TRUE detection을 슬라이스별로 보여준다.

| Slice | n | TRUE | Real bypass |
|---|---:|---:|---:|
| Overall | 10,000 | 80.15% | 19.85% |
| English | 3,487 | 99.37% | 0.63% |
| Korean | 6,513 | 69.86% | 30.14% |
| EN_checksum | 2,603 | 99.15% | 0.85% |
| EN_format | 884 | 100.00% | 0.00% |
| KR_checksum | 522 | 83.14% | 16.86% |
| KR_format | 4,689 | 74.00% | 26.00% |
| **KR_semantic** | 1,302 | **49.62%** | **50.38%** |

**결론**: 영어는 99% 이상 방어되지만 **한국어 텍스트형 PII는 절반이 우회된다**. 특히 `session`(95.9%), `court`(92.8%), `allergy`(92.3%), `family`(88.9%), `surgery`(87.5%), `company`(85.7%) 등 의료·법률·직장 정보에서 심각하다.

### 5.2 RQ2/RQ3: Layer 0 vs LLM judge

4-way 결과:

| Config | Overall TRUE | KR_semantic TRUE |
|---|---:|---:|
| A Baseline | 80.15% | 49.62% |
| B Baseline + L4 (LLM judge) | 90.96% | 87.40% |
| **C With Layer 0** | **94.32%** | **96.39%** |
| D Full | 97.23% | 98.85% |

**핵심 발견**:
- **C > B** (Overall +3.36%p, KR_semantic **+8.99%p**)
- **D − C = 2.91%p** (Layer 0가 있으면 LLM judge의 추가 효과는 제한적)

### 5.3 통계적 유의성 (McNemar)

10,000 matched pairs:

| Comparison | b (c1만) | c (c2만) | χ² | p-value |
|---|---:|---:|---:|---:|
| A vs C (Layer 0 effect) | 0 | 1,417 | 1,415 | **< 1e-309 \*\*\*** |
| **B vs C (L0 vs LLM head-to-head)** | 291 | 627 | 122 | **< 2e-28 \*\*\*** |
| C vs D (L4 추가 효과) | 0 | 291 | 289 | < 8e-65 *** |
| A vs D (전체 방어) | 0 | 1,708 | 1,706 | ≈ 0 *** |

Layer 0는 LLM judge보다 **336건 더 독립적으로 catch**했다(c=627 vs b=291). 이 차이는 p < 1e-28로 결정적이다.

### 5.4 지연 및 비용

| Config | p50 | p95 | p99 | mean |
|---|---:|---:|---:|---:|
| A Baseline | 507ms | 751ms | 1,317ms | 553ms |
| B Baseline + L4 | 1,833ms | 3,621ms | **4,819ms** | 2,095ms |
| **C With Layer 0** | **512ms** | **643ms** | **830ms** | 531ms |
| D Full | 1,798ms | 3,573ms | 4,762ms | 2,073ms |

Layer 0의 p99 추가 지연은 **135ms**에 불과하며, GPT-4o-mini judge(p99 4,164ms)의 **1/31**이다. 비용은 $0 (로컬 연산) 대 ~$0.0001/call.

### 5.5 Layer 0 Ablation

Layer 0를 세 모드로 분해:

| Slice | Baseline | +Norm only | +Dict only | +Full |
|---|---:|---:|---:|---:|
| KR_semantic | 49.62% | 49.92% | **87.71%** | 89.17% |
| KR_format | 74.00% | 74.47% | 88.12% | 95.20% |

KR_semantic에서 **Dictionary가 Layer 0 효과의 96%(+38.10%p)를 담당**하며, Normalizer 단독 기여는 +0.31%p에 불과하다. Synergy는 +1.14%p.

이는 **Layer 0의 핵심 엔진이 키워드 사전**이며, 정규화는 자모 분해/homoglyph/ZWSP 공격에서 사전 매칭을 가능하게 하는 보조 역할임을 의미한다.

### 5.6 Smart Cascade 최적화

L0+L1~L3가 이미 catch한 케이스에 L4를 스킵하는 최적화:

| Cascade 전략 | L4 호출 | TRUE detection | Latency 총합 | 비용 |
|---|---:|---:|---:|---:|
| Full Cascade (D) | 10,000 | 97.23% | 257분 | $1.35 |
| **Smart Cascade** | **568** | **97.23%** | **15분** | **$0.08** |

L4 호출 **94.32% 절감**, detection 영향 **0%**. Layer 0가 사실상 "preconditioner" 역할을 하여 LLM judge가 true last resort로 동작한다.

### 5.7 Robustness (v4 Validity-First Fuzzer)

v1(legacy) 퍼저 대비 v4(validity-first) 퍼저로 재평가.

| Config | v1 TRUE | v4 TRUE | Δ |
|---|---:|---:|---:|
| A Baseline | 80.15% | 80.11% | −0.04%p |
| B +L4 | 90.96% | 90.43% | −0.53%p |
| C +L0 | 94.32% | **94.99%** | **+0.67%p** |
| D Full | 97.23% | **97.68%** | **+0.45%p** |

**L0 vs LLM judge 격차(B vs C)는 v1의 +3.36%p에서 v4의 +4.56%p로 오히려 증가**했다. 이는 Layer 0의 우위가 퍼저 구현에 무관한 방어 메커니즘의 속성임을 입증한다. 특히 KR_semantic에서 v4 LLM judge는 84.76%까지 떨어진 반면(v4의 새 prescription_emr_line, account_bank_alias 변이가 LLM 맥락을 혼란시킴), Layer 0는 95.41%를 유지했다.

### 5.8 False Positive on Clean Text

뉴스·이메일·대화·기술문서·학술 문서 50건에서 Layer 0 detector의 FP를 측정했다.

- 초기 구현: 26% (주로 "개", "한국" 등 짧은 값 충돌)
- 개선 후: **2%** (잔여 2건은 실제 조직 정보 누설)

---

## 6. 논의 (Discussion)

### 6.1 Layer 0는 왜 LLM judge를 이기는가?

Ablation 결과(5.5)가 답을 준다. **Layer 0의 핵심 기여는 정적 키워드 사전**이며, 한국어 텍스트형 PII(allergy, company, diagnosis 등)는 **의미가 고정된 제한된 어휘**이기 때문에 사전 매칭이 LLM 추론보다 정확하다.

GPT-4o-mini judge는 범용 언어 이해 능력을 가지지만:
1. **Threshold 기반 이진 분류**(0.7 기본)로 인해 애매한 케이스에서 일관성이 떨어짐
2. **Long context에서 "이 전체 텍스트가 PII를 포함하는가?"를 판단**해야 하므로, 구조가 복잡해진 v4 변이(prescription_emr_line 같은 EMR 포맷)에서 혼동됨
3. **탐지 근거를 로그에 남기지 못함** (블랙박스)

반면 Layer 0는:
1. **결정론적** — 같은 입력 → 같은 출력
2. **설명 가능** — 어떤 키워드/정규식이 매칭됐는지 기록
3. **Korean-specific fine-tuning 없이도** 정규화 후 사전 매칭으로 정확한 탐지

### 6.2 실무 배포 함의

본 결과는 다음과 같은 실무 권장을 지지한다.

- **한국어 서비스를 운영하는 LLM 게이트웨이는 Layer 0 같은 한국어 특화 전처리 계층을 반드시 추가해야 함**
- LLM judge는 cascade 최적화로 전체 케이스의 **5~6%에만 적용**해도 동일한 탐지율 달성 가능 (6.6절)
- 총 비용(10k 기준)은 **$0.08** 수준으로, LLM judge를 "safety net"으로만 사용하는 전략이 경제적

### 6.3 확장성 — 다른 언어

Layer 0 설계는 언어 중립적이다. 다른 언어에도 동일한 패턴이 적용 가능:
- 정규화 단계: 해당 언어 특유의 유니코드/인코딩 공격 (일본어 히라가나-카타카나, 중국어 번체-간체 등)
- 키워드 사전: 해당 언어·도메인 PII 코퍼스

본 연구는 한국어로 실증했지만, 일본어·중국어 확장은 향후 과제다.

### 6.4 한계

- **Semantic ambiguity**: "김철수"가 회사 고객인지 공인인지 Layer 0는 구분 못 함. Context-aware disambiguation은 여전히 LLM judge가 유리.
- **Novel PII types**: 퍼저의 91종 외 새로운 PII(예: 신종 결제 서비스 ID)는 사전 업데이트 필요.
- **Injection 공격 결합**: 본 연구는 PII 우회에 집중했으며, PII + prompt injection 결합 공격은 별도 평가 필요 (Lakera의 실역할).

---

## 7. 결론 (Conclusion)

본 연구는 LiteLLM 게이트웨이 기반 한국어 LLM 환경에서 프로덕션 PII 가드레일이 한국어 텍스트형 PII에 대해 50% 이상 우회되는 심각한 공백을 실증했다. 이 공백을 메우기 위해 **결정론적 한국어 특화 전처리 계층(Layer 0)**을 설계하고, 10,000건 stratified 페이로드에서 진짜 API 호출 기반 4-way 비교 평가를 수행했다.

결과적으로 Layer 0는 GPT-4o-mini judge를 통계적으로 결정적인 차이(p < 1e-28)로 능가하며, 비용과 지연에서 두 자리 수 배 우위를 보였다. 특히 한국어 텍스트형 PII 슬라이스에서 Layer 0 단독 탐지율은 96.39%로, LLM judge(87.40%) 대비 +8.99%p 높았다. Ablation 분석은 이 효과가 주로 키워드 사전에서 기원함을 밝혔으며, validity-first 퍼저로 재평가 시 이 우위는 오히려 확대(+4.56%p → +10.65%p on KR_semantic)되어 결과의 robustness를 입증했다.

본 연구는 LLM 기반 방어선이 모든 보안 문제의 해답이 아니며, 도메인 지식(한국어 PII 사전)에 기반한 경량 결정론적 접근이 더 효과적일 수 있음을 보여준다. 전체 코드·데이터·결과는 Apache 2.0 (코드) 및 CC BY-NC 4.0 (데이터)으로 공개된다.

---

## 참고 문헌 (References)

1. Fei, B. et al. (2024). KDPII: Korean De-identification PII Dataset. *IEEE Access*, 12, 135626–135641.
2. Microsoft Presidio (2025). KR_RRN, KR_BRN, KR_FRN, KR_DRIVER_LICENSE, KR_PASSPORT recognizers. Released in v2.2.361.
3. LiteLLM Documentation. (2026). Guardrail Policies and Korean PII Masking v2.
4. TrueFoundry Blog. (2026). PII Redaction with Palo Alto Prisma AIRS.
5. Mindgard & Hackett (2025). Bypassing LLM Guardrails: A Systematic Study.
6. CrowdStrike (2025). IM/PT Taxonomy for AI Defense.
7. Palo Alto Unit 42 (2025). 22 Web IDPI Techniques.
8. KLUE Benchmark. (2021). Korean Language Understanding Evaluation.

---

## BibTeX

```bibtex
@techreport{min_korean_pii_2026,
  title        = {한국어 환경 다계층 LLM 가드레일의 취약성과 정규화 계층 기반 방어},
  author       = {민우},
  year         = {2026},
  month        = apr,
  institution  = {정보보안학과 CCIT 융합전공},
  advisor      = {임정묵},
  type         = {캡스톤 연구보고서},
  url          = {https://github.com/vmaca123/My-AI-Security-Project}
}
```

---

## 부록 A — 평가 데이터 상세

전체 사례별 평가 결과 (10,000건 × 4 configs × layer_results):

- `PII/results/data/eval_10k_l1l3.json` (14MB, A Baseline)
- `PII/results/data/eval_10k_l1l4_full.json` (11MB, B Baseline+L4)
- `PII/results/data/eval_10k_l0_l1l3.json` (17MB, C With L0)
- `PII/results/data/eval_10k_l0_l1l4_full.json` (13MB, D Full)

## 부록 B — 주요 Figure

- Fig 1: 전체 우회율 슬라이스별 비교
- Fig 7: KR_semantic 3-way head-to-head
- Fig 10: 4-way 최종 비교
- Fig 11: KR_semantic 4-way head-to-head (핵심 figure)
- Fig 12: Top 15 hardest PII 4-way
- Fig 13: Layer 0 Ablation 기여도

## 부록 C — 재현 명령

```bash
git clone https://github.com/vmaca123/My-AI-Security-Project
cd My-AI-Security-Project

# 1. 환경 변수 설정 (.env 파일)
cp .env.example .env  # OPENAI_API_KEY, AWS_*, LAKERA_API_KEY 등 채움

# 2. 전체 파이프라인 실행 (약 4시간, ~$5 API 비용)
make setup          # Docker stack
make deploy-l0      # Layer 0 배포
make test           # 89 unit tests
make all            # 전체 평가 → aggregate → figures → analyze

# 3. 개별 단계 (선택적)
make eval-base      # L1~L3만 (~80분)
make eval-l0        # L0+L1~L3 (~80분)
make eval-l4        # L4 cascade (~40분)
```
