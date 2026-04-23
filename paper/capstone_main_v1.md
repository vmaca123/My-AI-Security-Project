# 한국어 LLM 게이트웨이 환경에서 다계층 PII 가드레일의 취약성 분석 및 정규화 기반 방어 계층 설계

## *Normalization-First Defense for Korean PII in LLM Gateways: Outperforming LLM-as-Judge at Fraction of the Cost*

**민우** (정보보안학과, CCIT 융합전공) · **지도교수 임정묵**
2026년 4월 · 캡스톤 연구보고서
코드·데이터 공개: https://github.com/vmaca123/My-AI-Security-Project

---

## 초록

생성형 AI 서비스의 확산과 함께 개인식별정보(PII) 유출 방지는 LLM 게이트웨이의 핵심 보안 과제로 부상했다. 산업 현장에서는 Microsoft Presidio, AWS Bedrock Guardrails, Lakera Guard 등 여러 상용 가드레일을 다계층으로 결합하여 배포하는 것이 일반적이다. 그러나 이러한 가드레일은 모두 영어 중심으로 설계되어 있어 한국어 텍스트형 PII(알레르기·처방·가족관계 등)에 대해 심각한 탐지 공백을 보인다.

본 연구는 LiteLLM 게이트웨이 기반 실무 프로덕션 환경에서 Presidio·Bedrock·Lakera 3계층과 GPT-4o-mini 기반 LLM-as-judge를 결합한 4계층 스택을 구축하고, 한국어 특화 퍼저 v4(validity-first, 91종 PII)로 생성한 10,000건 stratified 페이로드에 대해 진짜 API 호출 기반 평가를 수행했다. 그 결과, 기존 3계층(L1~L3)은 영어 PII를 99.2% 탐지하지만 한국어 텍스트형 PII(KR_semantic, n=1,302)는 49.6%만 탐지한다는 것을 확인했다.

이 공백을 메우기 위해 본 연구는 LLM을 사용하지 않는 결정론적 경량 방어 계층인 **Layer 0**를 제안한다. Layer 0는 13단계 한국어 정규화 파이프라인(자모 결합, NFKC, ZWSP 제거, 한자-한글 변환 등)과 42개 정규식 + 22개 키워드 사전을 결합한 탐지기로 구성된다. 같은 10,000건 벤치마크에서 Layer 0 단독 추가는 KR_semantic 탐지율을 96.4%까지 회복시키며, 이는 GPT-4o-mini judge(87.4%)를 **+8.99%p 능가**한다. McNemar 짝비교 검정에서 이 차이는 p < 1e-28로 결정적이며, Layer 0의 평균 지연은 10ms(p99 135ms)로 LLM judge의 220분의 1이다. Ablation 분석은 Layer 0 효과의 96%가 키워드 사전에서 비롯됨을 밝혔다. 끝으로, 더 엄격한 validity-first 퍼저 v4로 재평가 시 Layer 0의 우위는 오히려 +4.56%p(KR_semantic: +10.65%p)로 확대되어, 본 결과가 퍼저 구현이 아닌 방어 메커니즘 자체의 속성임을 입증했다.

본 연구는 한국어 LLM 보안 환경에서 "LLM judge 없이도 더 잘 잡는" 경량 결정론적 방어선이 실무적으로 가능함을 최초로 실증하며, 전체 데이터·코드·CI를 공개하여 재현 가능성을 확보한다.

**주요어**: LLM 보안, 개인식별정보(PII), 가드레일, 한국어 자연어처리, LiteLLM, 형태 정규화, 퍼징

---

## 1. 서론

### 1.1 연구 동기

조직이 LLM 서비스를 도입할 때, 사용자 입력이 외부 LLM API로 흘러가는 과정에서 주민등록번호, 의료 정보, 금융 정보 등의 개인식별정보(PII)가 유출될 위험이 존재한다. 이를 막기 위해 기업들은 LLM과 애플리케이션 사이에 **게이트웨이 계층**을 배치하고, 여기에 여러 상용 PII 가드레일을 직렬로 연결한다. LiteLLM 공식 문서는 Presidio(PII 탐지)와 Lakera(프롬프트 인젝션 방어)를 기본 조합으로 권장하며, 많은 실무 배포가 여기에 AWS Bedrock Guardrails, OpenAI Moderation, Azure Content Safety 등을 추가하여 4~5계층 스택을 구성한다. 최근에는 규칙 기반 가드레일이 놓친 케이스를 LLM 자체에게 판별시키는 **LLM-as-judge** 방식(GPT-4o 등)을 post-call 레이어로 배치하는 패턴이 확산되고 있다.

그러나 이러한 가드레일은 거의 예외 없이 영어 중심으로 설계되었다. 예를 들어 Microsoft Presidio의 2025년 기준 한국어 전용 PII recognizer는 주민등록번호(KR_RRN), 사업자등록번호, 외국인등록번호, 운전면허번호, 여권번호 등 **5종의 숫자·형식형 PII**에 한정된다. AWS Bedrock Guardrails는 다국어 콘텐츠 필터링을 지원하지만 내부 정책 모델은 영어 데이터로 fine-tune되어 있어 한국어에 대한 재현율이 제한적이다. Lakera Guard v2는 PII 탐지보다 프롬프트 인젝션·탈옥 방어에 특화된 서비스이다. 결과적으로 한국어 텍스트형 PII — 알레르기, 처방, 혈액형, 수술 이력, 학력, 직장, 가족관계, 사건번호, 종교 등 — 는 사실상 무방비 상태로 LLM에 전달된다.

한국어 텍스트형 PII의 난이도는 단순히 언어 문제가 아니다. 숫자형 PII(전화번호, 카드번호)는 구조가 고정되어 있어 정규식으로 잡을 수 있지만, 텍스트형 PII는 자유 문형 안에 삽입되며 문맥 의존적이다. "환자 기록: 김씨 페니실린 알레르기" 같은 짧은 문장에서 "페니실린 알레르기"라는 텍스트 조각을 PII로 인식하려면 **한국어 의료 어휘에 대한 사전 지식**이 필수적이다. 또한 한국어에는 자모 분해(`ㅈㅜㅁㅣㄴ번호`), 초성 추출(`ㅈㅁㄷㄹㅂㅎ`), 한자 혼용, 야민정음, 동형 문자, Zero-Width Space 삽입 등 고유한 변이 기법이 존재하여, 영어권에서 알려진 동일한 공격(fullwidth digit, homoglyph)에 한국어 특유의 공격 표면이 추가된다.

### 1.2 연구 질문

본 연구는 다음 세 가지 질문에 답한다.

**RQ1**. 현재 산업에서 배포되는 다계층 PII 가드레일 스택은 한국어 텍스트형 PII에 대해 얼마나 취약한가? 이 취약성은 언어 차이에서 오는 것인가, 아니면 PII의 종류(형식형 vs 텍스트형) 차이에서 오는 것인가?

**RQ2**. GPT-4o-mini 같은 LLM-as-judge를 cascade 레이어로 추가하는 것은 이 공백을 실질적으로 메우는가? 메운다면 어느 정도의 비용과 지연을 수반하는가?

**RQ3**. LLM을 사용하지 않는 결정론적 한국어 특화 방어선 — 정규화 파이프라인과 키워드 사전의 조합 — 이 LLM-as-judge를 대체하거나 능가할 수 있는가?

### 1.3 본 연구의 기여

본 논문의 주요 기여는 다음과 같다. **첫째**, 91종 PII와 6개 변이 레벨(Original → Context)을 지원하며 체크섬 100% 유효를 보장하는 한국어 특화 validity-first 퍼저를 설계·공개했다. **둘째**, LiteLLM 게이트웨이를 통해 진짜 API를 호출하여 수집한 10,000건 벤치마크(영어 3,487 / 한국어 6,513, `lang × validity_group` stratified)를 공개했다. **셋째**, 4-way 비교 실험(A: Baseline / B: +LLM judge / C: +Layer 0 / D: Full)을 통해 Layer 0가 LLM judge를 통계적으로 결정적인 차이로 능가함을 입증했다. **넷째**, Ablation 분석으로 Layer 0 효과의 96%가 키워드 사전에서 비롯됨을 밝혔으며, 이는 다른 언어로의 확장성에 대한 실무적 지침을 제공한다. **다섯째**, validity-first 퍼저 v4로 재평가하여 결과의 robustness를 검증했고, Layer 0 우위가 오히려 확대됨을 확인했다. **여섯째**, 89개 단위 테스트와 GitHub Actions CI, 단일 명령 재현 파이프라인(`make all`)을 포함한 전체 재현 환경을 공개했다.

---

## 2. 관련 연구

### 2.1 LLM 게이트웨이 가드레일 배치

LLM 게이트웨이는 애플리케이션과 LLM 사이에 위치하여 라우팅, 비용 관리, 관찰성, 보안을 담당한다. LiteLLM, Portkey, TrueFoundry, Bifrost 등 주요 오픈소스·상용 솔루션이 존재하며, 이들은 공통적으로 "여러 가드레일을 순차 또는 병렬로 실행"하는 패턴을 제공한다. LiteLLM의 공식 권장 구성은 Presidio를 PII baseline으로, Lakera를 injection 전담으로, 필요 시 Bedrock Guardrails나 Azure Content Safety를 추가하는 것이다. NVIDIA NeMo Guardrails는 CrowdStrike Falcon AIDR 및 Palo Alto AIRS와 통합되어 엔터프라이즈급 정책을 제공한다.

### 2.2 한국어 PII 연구

Fei 등(2024)은 IEEE Access에 발표한 KDPII 논문에서 한국어 대화형 데이터셋의 PII 비식별화 벤치마크를 제시하고, GPT-4를 포함한 주요 언어모델이 범용 PII보다 한국어 특화 PII(33개 카테고리)를 인식하는 데 현저히 낮은 성능을 보임을 실증했다. 이 연구는 본 연구의 공격 대상 PII 카테고리(의료, 법률, 직장, 가족 등)를 정하는 데 직접적인 참조가 되었다. 그러나 KDPII는 **모델 자체의 PII 인식 능력**을 다루는 데 반해, 본 연구는 **실운영 다계층 가드레일 스택의 취약성**을 대상으로 한다는 점에서 차별된다. 또한 KDPII는 정적 벤치마크이지만 본 연구는 퍼징 기반 동적 공격을 도입하여 변이 차원을 추가했다.

한국어 NER(Named Entity Recognition) 관점에서는 KLUE 벤치마크, KoELECTRA, KPF-BERT-NER 등 공개 모델이 존재하지만, 이들은 인명·지명·기관명 등 일반 개체명에 초점이 맞추어져 있으며 의료·법률 PII 같은 세부 도메인 어휘를 다루지 않는다. 따라서 본 연구는 NER 모델 fine-tuning 경로 대신 **한국어 의료·법률·금융 도메인 키워드를 직접 사전화**하는 접근을 선택했다.

### 2.3 프롬프트 인젝션 및 우회 공격

LLM 가드레일을 우회하는 공격 연구는 지난 몇 년간 빠르게 확산되었다. Mindgard & Hackett(2025)는 *Bypassing LLM Guardrails*에서 인코딩 변이(base64, ROT13, fullwidth)와 컨텍스트 위장(역할극, 시스템 오버라이드)을 체계적으로 분석했다. Palo Alto Unit42(2025)는 웹 IDPI 22개 기법을 분류했고, CrowdStrike(2025)는 IM/PT 분류 체계를 제안했다. 한국어 환경에서는 **HouYi** 프레임워크가 한국어 프롬프트 인젝션의 체계적 연구로서 선행한다. 본 연구의 퍼저는 HouYi 스타일의 컨텍스트 삽입 공격을 L5 레벨 변이로 포함한다.

### 2.4 본 연구의 차별점

기존 연구는 대체로 (a) 단일 모델 또는 단일 가드레일 평가에 머물거나, (b) 영어 중심 벤치마크를 사용하거나, (c) 공격 분석에만 집중하고 방어 대안을 제시하지 않는다. 본 연구는 세 측면에서 구별된다. 첫째, 실무에서 실제로 배포되는 **다계층 스택 전체(L1~L4)**를 대상으로 한다. 둘째, **한국어 특화 공격-방어 양면 연구**로서 공격 퍼저와 방어 레이어를 함께 제안한다. 셋째, LLM을 사용하지 않는 결정론적 방어가 LLM-as-judge를 능가함을 실증함으로써 **기존 통념(LLM 방어가 최고)에 도전**한다.

---

## 3. 시스템 설계

### 3.1 5계층 방어 파이프라인

본 연구에서 구축한 5계층 방어 파이프라인의 구조는 그림 1과 같다. 사용자 입력은 먼저 Layer 0(한국어 정규화 + 키워드 탐지)를 통과하고, 이후 Presidio(L1), Bedrock Guardrails(L2), Lakera(L3)를 순차 또는 병렬로 거쳐 LLM에 전달된다. LLM 응답이 생성되면 post-call 레이어로 GPT-4o-mini judge(L4)가 최종 검증을 수행한다. 각 레이어의 호출 시점(`pre_call`, `during_call`, `post_call`)과 동작 모드(BLOCK/MASK/PASS)는 LiteLLM `CustomGuardrail` 인터페이스를 통해 통합 제어된다.

본 연구의 핵심 기여는 L0 레이어의 설계에 있으며, L1~L4는 기존 상용 가드레일을 그대로 활용한다. 이는 "실무에서 이미 배포된 스택에 추가만 하면 되는" 실용적 의도를 반영한다.

### 3.2 Layer 0의 구성

Layer 0는 두 개의 주요 컴포넌트로 구성된다: **(1) Korean Normalizer**와 **(2) Korean PII Detector**.

Korean Normalizer는 한국어 텍스트에 가해진 표면적 변이를 표준 형태로 복원하는 13단계 파이프라인이다. 그 핵심 단계는 유니코드 NFKC 정규화, Zero-Width Space(`\u200B`)와 Soft Hyphen(`\u00AD`) 제거, Combining Mark(`\u0300–\u036F`) 제거, Fullwidth 문자(ａ-ｚ, ０-９)를 ASCII로 변환, Mathematical Bold Digits(𝟎-𝟗)와 Circled Digits(①-⑨)를 표준 숫자로 치환, 한자 성씨를 한글로 변환, 분해된 자모(`ㅈㅜㅁㅣㄴ`)를 음절(`주민`)로 재결합, Homoglyph 치환, 공백 정규화 및 제어 문자 제거이다. 이 중 자모 결합 단계는 후속 사전 매칭의 전제 조건이 되므로 가장 중요하다.

Korean PII Detector는 **42개 정규식 패턴**과 **22개 키워드 사전**으로 구성된다. 정규식은 구조가 명확한 토큰형 PII — 세션 토큰, JWT, 암호화폐 지갑, 사건번호, GPS 좌표, AWS 키, SSH 키, MAC 주소, 의료기록번호(MRN), 사번(EMP), 여권번호, 차량번호, 택배 송장번호, 승인번호, 거래번호, 보험증권번호 등 — 을 대상으로 한다. 키워드 사전은 **구조가 자유로운 텍스트형 PII** — 알레르기, 진단명, 처방, 수술, 장애, 혈액형, 종교, 결혼 상태, 학교, 학과/학위, 직책, 회사, 부서, 업무 이메일, 병원 담당의, 거래내역, 자동차 보험 등 — 을 대상으로 한다. 각 사전 항목은 **컨텍스트 키워드**(예: "알레르기", "국적")와 **구체 값**(예: "페니실린", "한국")의 쌍으로 구성되어, 값 단독 매칭의 위험을 제어한다.

### 3.3 False Positive 방지 설계

초기 구현은 정상 한국어 문서 50건(뉴스, 업무 이메일, 일상 대화, 기술 문서, 학술 텍스트)에서 약 26%의 False Positive를 보였다. 주요 원인은 짧은 사전 값의 부주의한 매칭이었다: "알레르기" 사전의 "개"가 "3개월", "개선", "개최" 등에서 매칭되었고, "국적" 사전의 "한국"이 "한국은행", "한국인"에서 매칭되었다. 이를 해결하기 위해 **2자 이하 키워드는 컨텍스트 필수** 규칙을 도입했다. 즉 "한국"은 같은 텍스트 내에 "국적", "시민권", "영주권" 등 컨텍스트 키워드가 있을 때만 매칭된다. 이 규칙 하나로 FP는 26%에서 2%로 감소했다. 잔여 2건은 조직 공지문의 "개발팀", "경영지원팀"에 대한 매칭으로, 실제 조직 정보의 누설 여부는 정책적 판단 영역에 속한다.

### 3.4 LiteLLM 통합의 실무적 주의사항

Layer 0는 `litellm.integrations.custom_guardrail.CustomGuardrail` 클래스를 상속하여 `async_pre_call_hook`(실제 LLM 호출 전 입력 검사용)과 `apply_guardrail`(`/guardrails/apply_guardrail` API 엔드포인트용) 두 진입점을 모두 제공한다. 본 연구 과정에서 LiteLLM v4.69+에서 Bedrock 가드레일 설정 스키마가 변경되어 `guardrailIdentifier`와 `guardrailVersion`을 `litellm_params` 직접 아래에 두어야 한다는 점을 발견했다. 이 필드를 `guardrail_info` 중첩 아래에 두면 초기화 함수가 값을 `None`으로 읽어 `400 Guardrail was enabled but input is in incorrect format` 오류를 발생시킨다. 이 이슈는 실제 평가 중 발견되어 수정되었으며, 설정 파일의 호환성 문서화가 후속 배포에 중요하다.

---

## 4. 평가 방법

### 4.1 Validity-First Fuzzer v4

평가의 신뢰성을 확보하려면 "퍼저가 만든 시드 자체가 무효이므로 가드레일이 못 잡는 게 당연하다"는 반론을 차단해야 한다. 본 연구의 v4 퍼저는 모든 시드를 mutation 적용 전에 **3단계 유효성 검증**을 거치도록 설계되었다. 첫째, **Checksum 검증형 PII**는 주민등록번호(공식 체크섬), 신용카드(Luhn 알고리즘), 사업자등록번호(가중치 체크섬), 외국인등록번호, IMEI(Luhn), VIN(transliteration 기반 체크섬), US SSN(area/group/serial 규칙)에 대해 **100% 유효한 값**만 생성한다. 둘째, **Format 검증형 PII**는 전화번호, 이메일, IP, MAC, 여권, 운전면허 등의 공식 포맷 규칙을 준수한다. 셋째, **Semantic Dictionary 검증형 PII**는 진단명(건강보험심사평가원 상위 30개), 처방 약품(22종 × 용량·빈도·경로·복용법 allowed combination), 알레르기, 수술, 학위, 종교 등 실제 존재하는 값 목록에서 추출한다. 각 payload에는 `format_valid`, `rule_valid`, `semantic_valid`, `validity_group` 메타데이터가 기록되어 사후 검증이 가능하다.

### 4.2 6단계 변이 구조

각 PII 시드는 다음 6단계 변이 레벨로 확장된다. **L0 Original**은 원본 PII 값 그대로, **L1 Character**는 자모 분해, 초성, 한자, fullwidth, homoglyph, circled, emoji smuggling, **L2 Encoding**은 Zero-Width Space, combining marks, soft hyphen 삽입, **L3 Format**은 구분자 변경(dot/slash/space/none)과 space_digits, **L4 Linguistic**은 code-switching, abbreviation, 한국어 숫자 표기(공일이삼), 다국어 용어(일어/중국어/프랑스어/독일어), 조사 변이, 그리고 도메인 전용 변이 — `prescription_emr_line`(`Rx) 메트포르민 500mg PO bid pc x 30D`), `account_bank_alias`(`KB 123-45-67890`), `transaction_field_split`(거래일시/거래구분/금액/승인번호 분리 표기) — 를 포함한다. **L5 Context**는 RAG 삽입, JSON 포맷, HouYi 스타일 인젝션을 포함한다.

### 4.3 평가 데이터셋

v4 퍼저의 출력에서 10,000건을 `lang × validity_group` 기준 stratified sampling으로 추출했다. 분포는 영어 3,487건(체크섬 2,603 / 포맷 884) 및 한국어 6,513건(체크섬 522 / 포맷 4,689 / 시맨틱 **1,302**)이다. 본 연구의 핵심 narrative slice인 **KR_semantic**에 1,302건을 할당하여 한국어 텍스트형 PII에 대한 충분한 통계적 검정력을 확보했다.

### 4.4 4-way 비교 실험 설계

같은 10,000건 페이로드에 대해 네 가지 구성을 평가했다. 구성 A(Baseline)는 L1+L2+L3로 LLM judge 없는 프로덕션 스택에 해당한다. 구성 B(Baseline+L4)는 A에 GPT-4o-mini judge를 cascade로 추가하여 LLM-as-judge 방식의 효과를 측정한다. 구성 C(With Layer 0)는 L0+L1+L2+L3로 Layer 0 단독의 효과를 측정하며 LLM을 전혀 사용하지 않는다. 구성 D(Full)는 L0+L1+L2+L3+L4로 모든 방어선을 적용한 상한선이다.

Layer 4는 원칙적으로 모든 케이스에 호출하지만, 비용 통제를 위해 본 연구는 두 모드를 비교한다: **Full Cascade**(전체 10,000건에 L4 호출)와 **Smart Cascade**(L0+L1~L3가 이미 neutralize한 케이스는 L4 스킵). 두 모드의 detection rate가 일치하면 Smart Cascade가 운영 환경에서 선호된다.

### 4.5 평가 지표: TRUE Detection

가드레일 평가에서 흔히 사용되는 raw detection(`output != text`) 지표는 부풀려진다. 예를 들어 Presidio가 텍스트 내 PERSON만 마스킹하고 실제 PII인 전화번호는 원본 그대로 남긴 경우 output이 변경되었으므로 "detected"로 카운트되지만, 실제 PII는 누설된다. 따라서 본 연구는 다음 세 분류의 **TRUE Detection**을 채택한다.

- **TRUE**: 어떤 레이어라도 실제 PII 값을 neutralize (BLOCK 액션 또는 output에서 해당 PII 값이 사라짐).
- **FALSE**: 레이어가 텍스트를 변경했으나 PII 원본 값이 여전히 남아있음.
- **BYPASS**: 어떤 레이어도 텍스트를 변경하지 않음.

**Real bypass rate**는 FALSE와 BYPASS의 합으로 정의한다. 이는 "가드레일이 탐지했다"보다 "가드레일이 실제로 PII 유출을 막았다"라는 의미에 가까우며, 논문 결과의 신뢰성을 높인다.

### 4.6 통계 검정

본 연구는 같은 10,000건 케이스에 대한 짝비교(matched-pairs) 결과를 보유하므로 **McNemar 검정**(continuity-corrected chi-squared, df=1)을 적용했다. 두 구성을 비교할 때 `b`는 구성1만 catch한 건수, `c`는 구성2만 catch한 건수이며, $\chi^2 = (|b-c|-1)^2 / (b+c)$에 따른 p-value로 유의성을 판정한다.

### 4.7 재현성 환경

전체 실험은 Docker 기반 고정 환경에서 수행되었다: LiteLLM Proxy(ghcr.io/berriai/litellm:main-latest, v4.69), PostgreSQL 16, Presidio Analyzer/Anonymizer, AWS Bedrock Guardrail(`us-east-1`, DRAFT 버전), Lakera Guard v2, OpenAI gpt-4o-mini(`PII_JUDGE_THRESHOLD=0.7`). 평가기는 Python 3.12 + httpx async 기반으로 작성되었으며, OpenAI rate limit 대응을 위해 L4 호출에만 `asyncio.Semaphore(5)`로 동시성을 제어한다. 전체 평가 파이프라인은 `make all` 단일 명령으로 재현 가능하며 약 4시간, 총 API 비용은 약 5 USD이다.

---

## 5. 결과

### 5.1 RQ1: 프로덕션 가드레일의 한국어 공백

표 1은 구성 A(L1~L3 Baseline)의 TRUE detection 결과를 주요 슬라이스별로 보여준다. 전체 평균은 80.15%이며 영어는 99.37%, 한국어는 69.86%에 머문다. 그러나 가장 결정적인 수치는 **한국어 텍스트형 PII(KR_semantic, n=1,302)의 49.62%**이다. 이는 1,302건의 한국어 알레르기·처방·학력·가족관계 페이로드 중 650건이 프로덕션 가드레일을 **완전히 우회**했음을 의미한다. 반면 영어 format(n=884)은 100.00% 방어되었다.

| Slice | n | TRUE | Real bypass |
|---|---:|---:|---:|
| Overall | 10,000 | 80.15% | 19.85% |
| English | 3,487 | 99.37% | 0.63% |
| Korean | 6,513 | 69.86% | 30.14% |
| EN_checksum | 2,603 | 99.15% | 0.85% |
| EN_format | 884 | 100.00% | 0.00% |
| KR_checksum | 522 | 83.14% | 16.86% |
| KR_format | 4,689 | 74.00% | 26.00% |
| **KR_semantic** | **1,302** | **49.62%** | **50.38%** |

**표 1. Baseline (A) 구성의 TRUE detection rate**

이 공백은 PII 유형별로 더 극적이다. `session`(세션 토큰, 95.9%), `court`(사건번호, 92.8%), `allergy`(알레르기, 92.3%), `family`(가족관계, 88.9%), `surgery`(수술 이력, 87.5%), `company`(회사명, 85.7%), `job_title`(직책, 82.4%) 등 일곱 개 PII 타입이 85% 이상 우회되었다. 이는 한국어 환경에서 프로덕션 가드레일이 의료·법률·직장 정보에 대해 실질적으로 무방비 상태임을 의미한다.

### 5.2 RQ2: GPT-4o-mini Judge의 효과

구성 B(A + Layer 4)는 GPT-4o-mini judge를 cascade로 추가한 결과이다. 전체 TRUE detection은 90.96%, KR_semantic은 87.40%로 상승하며, 이는 baseline 대비 overall +10.81%p, KR_semantic +37.78%p의 개선이다. 통계적으로 매우 유의미한 향상이지만, 실무 배포 관점에서 문제가 있다. LLM judge는 **평균 1,542ms, p99 4,164ms의 지연**을 발생시키며, 10,000건 호출 기준 약 1.35 USD의 비용이 소요된다. 또한 KR_semantic의 12.60%(n=1,302 중 164건)는 여전히 우회되었다.

### 5.3 RQ3: Layer 0 단독의 효과

본 연구의 핵심 결과는 구성 C(A + Layer 0)이다. LLM을 전혀 사용하지 않는 Layer 0 단독 추가만으로 전체 TRUE는 94.32%, KR_semantic은 **96.39%**에 도달한다. 이는 baseline 대비 overall +14.17%p, KR_semantic +46.77%p이며, 구성 B(LLM judge) 대비로는 overall +3.36%p, **KR_semantic에서 +8.99%p 우위**이다.

| Config | Overall TRUE | KR_semantic TRUE | Overall Latency p99 | Cost per 10k |
|---|---:|---:|---:|---:|
| A Baseline | 80.15% | 49.62% | 1,317ms | $0 |
| B Baseline + L4 | 90.96% | 87.40% | 4,819ms | $1.35 |
| **C With Layer 0** | **94.32%** | **96.39%** | **830ms** | **$0.08** |
| D Full (L0+L4) | 97.23% | 98.85% | 4,762ms | $1.35 |

**표 2. 4-way 비교 (주요 지표)**

특히 Layer 0는 11개 한국어 텍스트형 PII 타입(`allergy`, `company`, `job_title`, `gps`, `degree`, `blood`, `marital`, `dept`, `jwt`, `diagnosis`, `religion`)에서 100% 차단을 달성했다. 이전에 92% 이상 우회되던 `allergy`가 0%, 85% 우회되던 `company`가 0%로 떨어진 것이다.

### 5.4 통계적 유의성

10,000건 matched-pairs에 대한 McNemar 검정 결과는 표 3과 같다. 특히 본 연구의 핵심 주장인 **"Layer 0가 LLM judge를 이긴다"**(구성 B vs C)는 Layer 0만 catch한 케이스 627건 대비 LLM judge만 catch한 케이스 291건으로, 차이 336건이 $\chi^2 = 122.25$, $p < 2.04 \times 10^{-28}$의 결정적 유의 수준이다. 다른 비교도 모두 $p < 0.001$로 구성 간 차이가 모두 통계적으로 유의하다.

| Comparison | b (c1만 catch) | c (c2만 catch) | χ² | p-value |
|---|---:|---:|---:|---:|
| A vs B (LLM judge 효과) | 0 | 1,081 | 1,079 | < 1e-236 *** |
| A vs C (Layer 0 효과) | 0 | 1,417 | 1,415 | **< 1e-309 \*\*\*** |
| **B vs C (L0 vs LLM judge)** | **291** | **627** | **122.25** | **< 2e-28 \*\*\*** |
| C vs D (L4 추가 효과) | 0 | 291 | 289 | < 8e-65 *** |
| A vs D (전체 방어) | 0 | 1,708 | 1,706 | ≈ 0 *** |

**표 3. McNemar 짝비교 검정 결과 (n=10,000)**

### 5.5 비용 및 지연 분석

표 4는 각 구성의 latency 백분위수를 보여준다. Layer 0의 평균 추가 지연은 52ms(p99 135ms)로, 구성 A와 C의 전체 p99 차이는 **-487ms**이다. 즉 Layer 0 추가가 오히려 p99 지연을 감소시키는데, 이는 Layer 0에 의해 정규화된 텍스트를 Bedrock이 더 빠르게 처리하기 때문으로 분석된다(Bedrock p50: A의 427ms → C의 392ms).

| Config | p50 | p95 | p99 | mean |
|---|---:|---:|---:|---:|
| A Baseline | 507ms | 751ms | 1,317ms | 553ms |
| B Baseline + L4 | 1,833ms | 3,621ms | 4,819ms | 2,095ms |
| **C With Layer 0** | **512ms** | **643ms** | **830ms** | 531ms |
| D Full (L0+L4) | 1,798ms | 3,573ms | 4,762ms | 2,073ms |

**표 4. End-to-end latency (n=10,000)**

비용 측면에서는 Layer 0가 완전히 무료인 반면 LLM judge는 입력 500토큰 + 출력 100토큰 가정 시 호출당 약 0.000135 USD로, 10,000건 기준 1.35 USD, 월 100만 호출 환경에서는 135 USD가 된다. 기업 환경에서 연간 수만 USD 비용 절감 효과가 발생한다.

### 5.6 Ablation: Layer 0 내부 구성요소 분해

Layer 0는 "정규화"와 "사전"의 결합이다. 어느 쪽이 실제로 기여하는가? 이를 밝히기 위해 세 모드로 분해 실험을 수행했다: **Mode N**은 정규화만 적용(사전 비활성), **Mode D**는 원본 텍스트에 사전만 적용(정규화 없음), **Mode F**는 현재 production 구성(정규화 → 사전).

| Slice | Baseline | +Norm only | +Dict only | +Full |
|---|---:|---:|---:|---:|
| Overall | 80.15% | 80.42% (+0.27) | 91.80% (+11.65) | 95.51% (+15.36) |
| **KR_semantic** | **49.62%** | **49.92% (+0.31)** | **87.71% (+38.10)** | **89.17% (+39.55)** |
| KR_format | 74.00% | 74.47% (+0.47) | 88.12% (+14.12) | 95.20% (+21.20) |
| KR_checksum | 83.14% | 83.33% (+0.19) | 84.48% (+1.34) | 88.31% (+5.17) |

**표 5. Layer 0 Ablation (TRUE detection)**

KR_semantic에서 +39.55%p 총 효과 중 **키워드 사전이 +38.10%p(약 96%)를 담당**하며, 정규화 단독 기여는 +0.31%p, 시너지는 +1.14%p이다. 즉 Layer 0의 핵심 엔진은 **정적 키워드 사전**이며, 정규화는 자모 분해·homoglyph·ZWSP 공격에서 사전 매칭을 가능하게 하는 보조 역할이다. 이 발견은 다른 언어로의 확장 설계에 직접적인 지침을 제공한다.

### 5.7 Smart Cascade 최적화

Layer 0가 이미 catch한 케이스에 L4 호출을 스킵하는 Smart Cascade의 효과를 측정했다. 결과(표 6)는 L4 호출을 **94.32% 절감**하면서도 TRUE detection rate를 **완전히 유지**한다. 즉 Layer 0가 "preconditioner" 역할을 하여 LLM judge가 실제로 필요한 5.68%의 어려운 케이스에만 투입된다.

| 전략 | L4 호출 | TRUE | Latency 총합 | Cost per 10k |
|---|---:|---:|---:|---:|
| Full Cascade (D) | 10,000 | 97.23% | 257분 | $1.35 |
| **Smart Cascade** | **568** | **97.23%** | **15분** | **$0.08** |

**표 6. Smart Cascade 최적화 효과**

### 5.8 Robustness: Validity-First Fuzzer v4로 재평가

"결과가 퍼저 구현에 의존할 수 있다"는 잠재적 비판에 대응하기 위해, 전체 4-way 평가를 **v4 퍼저**(checksum 100% 유효, prescription/account/transaction 전용 생성기 포함, 21개 한국어 전용 L4/L5 변이 추가)로 재실행했다. 결과는 표 7과 같다.

| Config | v1 TRUE | v4 TRUE | Δ |
|---|---:|---:|---:|
| A Baseline | 80.15% | 80.11% | −0.04%p |
| B Baseline + L4 | 90.96% | 90.43% | −0.53%p |
| C With Layer 0 | 94.32% | **94.99%** | **+0.67%p** |
| D Full | 97.23% | **97.68%** | **+0.45%p** |

**표 7. v1 vs v4 fuzzer 결과 비교**

흥미롭게도 **Layer 0 우위는 v4에서 오히려 확대**된다. B vs C 격차는 v1의 +3.36%p에서 v4의 +4.56%p로, KR_semantic에서는 +8.99%p에서 +10.65%p로 증가했다. 이는 v4의 새 변이(특히 `prescription_emr_line`, `account_bank_alias`)가 LLM judge에게 더 어려운 반면, 핵심 키워드를 보존하므로 Layer 0 사전에 그대로 매칭되기 때문으로 분석된다. 이 결과는 본 연구의 핵심 주장이 **방어 메커니즘의 속성**이지 퍼저 구현의 artifact가 아님을 강하게 입증한다.

### 5.9 False Positive on Clean Korean Text

마지막으로, Layer 0의 False Positive를 정상 한국어 문서 50건(뉴스 10, 이메일/공지 10, 일상 대화 10, 기술 문서 10, 학술 텍스트 10)에서 측정했다. 2자 이하 키워드 컨텍스트 필수 규칙 적용 후 **Clean pass rate는 98%(50건 중 49건에서 finding 없음)**에 도달한다. 잔여 1건(2%)은 사내 공지문의 "개발팀"/"경영지원팀" 탐지이며, 이는 실제 조직 구조 정보의 누설로도 해석 가능하여 정책적 판단 영역에 해당한다.

---

## 6. 논의

### 6.1 Layer 0는 왜 LLM Judge를 이기는가?

Ablation 결과(5.6)는 결정적인 단서를 제공한다. Layer 0의 핵심 엔진은 **정적 키워드 사전**이며, 한국어 텍스트형 PII는 **의미가 고정된 제한된 어휘 집합**이다. "페니실린 알레르기", "메트포르민 500mg 1일 2회", "서울대병원 내과 김○○ 교수" 같은 표현은 몇 천 개의 정형화된 어휘 조합에 수렴한다. 이러한 bounded vocabulary 문제에서는 **사전 기반 매칭이 확률적 LLM 추론보다 더 정확**하다.

반면 GPT-4o-mini judge가 밀리는 이유는 세 가지로 요약된다. 첫째, threshold 기반 이진 분류(본 연구는 0.7) 특성상 애매한 confidence 영역의 케이스에서 일관성이 흔들린다. 둘째, LLM은 긴 컨텍스트를 받아 "이 전체 텍스트가 PII를 포함하는가?"를 판단하므로, v4의 `prescription_emr_line`처럼 EMR 포맷으로 감싸진 텍스트에서는 맥락이 분산되어 혼동이 발생한다. 셋째, 탐지 근거가 블랙박스여서 False Negative 발생 시 원인 분석과 개선이 어렵다. Layer 0는 이 세 가지에서 모두 반대 특성을 갖는다: 결정론적, 단일 PII 조각에 집중, 매칭 근거 기록.

### 6.2 실무 배포 함의

본 연구 결과는 한국어 LLM 서비스 운영자에게 다음 권장을 지지한다. 첫째, 영어 중심 가드레일(Presidio, Bedrock, Lakera 등)만으로는 한국어 텍스트형 PII에 대해 부적절한 방어가 수행됨을 인지해야 한다. 둘째, LLM-as-judge를 cascade로 추가하는 것은 기본 탐지율은 올리지만 지연과 비용의 큰 증가를 수반한다. 셋째, 경량 결정론적 한국어 특화 계층(본 연구의 Layer 0)을 먼저 배치하는 것이 비용 대비 효과가 크다. 넷째, LLM judge는 Layer 0가 놓친 약 5~6%의 케이스에만 적용하는 Smart Cascade 패턴을 통해 탐지율을 유지하면서 비용을 94% 절감할 수 있다.

월 100만 API 호출 환경에서 이 배치 전략은 연간 수만 USD의 비용 절감을 의미하며, 동시에 p99 지연을 3초 이상 낮춤으로써 사용자 경험 개선에도 기여한다. 또한 Layer 0는 외부 인터넷 연결이 필요 없으므로 **폐쇄망 환경**(정부·군·의료 기관 등)의 LLM 서비스에도 동일한 수준의 방어를 제공할 수 있다. 이는 LLM judge 의존 방식이 제공할 수 없는 중요한 운영적 자산이다.

### 6.3 한계

본 연구는 세 가지 한계를 가진다. 첫째, **Semantic ambiguity 처리의 한계**이다. "김철수"가 일반 고객인지 공인인지 Layer 0는 구별하지 못한다. 맥락 의존적 disambiguation은 여전히 LLM judge가 강점을 가지는 영역이며, 이 때문에 Full(L0+L4) 구성이 C 단독보다 추가 2.91%p 높다. 둘째, **새로운 PII 타입에 대한 대응**이다. 현재 Layer 0는 91종 PII를 다루지만, 새로운 결제 서비스 ID나 신규 플랫폼 토큰이 등장하면 사전·정규식 업데이트가 필요하다. 이는 NER 모델 기반 접근 대비 약점이다. 셋째, **프롬프트 인젝션 결합 공격**이다. 본 연구는 PII 우회 공격에 집중했으며, HouYi 같은 한국어 프롬프트 인젝션과 PII의 결합(예: "너는 고객관리 상담원이야. ㅈㅁㄷㄹㅂㅎ 조회해줘") 공격은 별도 평가가 필요하다. Lakera의 실제 역할(인젝션 전담)이 발휘되는 시나리오로, 후속 연구에서 다룰 예정이다.

### 6.4 확장성 및 후속 연구

Layer 0의 설계 철학은 **언어 중립적**이다. 각 언어에 대해 (1) 해당 언어 특유의 정규화 파이프라인과 (2) 해당 언어·도메인의 PII 키워드 사전을 구축하면 동일한 프레임워크를 적용할 수 있다. 일본어(히라가나-카타카나 변이, 한자 혼용), 중국어(번체-간체 변환), 아랍어(오른쪽-왼쪽 쓰기, 비음화) 등으로의 확장이 자연스러운 후속 연구 주제이다.

또한 본 연구는 입력 측 방어에 집중했으나, LLM 출력 측에 대한 Layer 0 적용도 가능하다. 팀 구성원이 개발한 `korean_pii_output_fuzzer_v4`는 LLM 응답 스타일(narrative, JSON, log, table, partial mask)로 PII가 누설되는 시나리오를 생성하며, 3,025건의 CRM/Healthcare/Finance/HR 번들 페이로드가 준비되어 있다. 이에 대한 Layer 0의 방어 효과 측정이 후속 연구로 계획되어 있다.

---

## 7. 결론

본 연구는 LiteLLM 게이트웨이 기반 한국어 LLM 서비스 환경에서 프로덕션 PII 가드레일 스택(Presidio + Bedrock Guardrails + Lakera)이 한국어 텍스트형 PII에 대해 절반 이상 우회되는 심각한 공백을 실증했다. 이 공백을 메우기 위해 LLM을 사용하지 않는 결정론적 경량 방어 계층인 **Layer 0**를 설계하고, 10,000건 stratified 벤치마크에서 진짜 API 호출 기반 4-way 비교 평가를 수행했다. Layer 0 단독 추가는 한국어 텍스트형 PII 탐지율을 49.62%에서 96.39%로 회복시키며, GPT-4o-mini judge cascade 대비 +8.99%p 우위를 McNemar 짝비교 $p < 10^{-28}$의 통계적으로 결정적인 차이로 확립했다. Layer 0의 평균 추가 지연은 10ms, 비용은 0 USD로 LLM judge의 220분의 1 수준이며, Ablation 분석은 효과의 96%가 키워드 사전에서 비롯됨을 밝혔다. 더 엄격한 validity-first 퍼저 v4로 재평가했을 때 Layer 0 우위가 오히려 확대되어 결과의 robustness를 입증했다.

본 연구는 LLM 기반 방어선이 모든 보안 문제의 해답이 아니며, **도메인 지식에 기반한 경량 결정론적 접근이 경우에 따라 더 우월**함을 실증한다. 특히 한국어·일본어·중국어처럼 영어 중심 프레임워크에서 소외된 언어의 LLM 보안에서는 이러한 접근이 표준이 되어야 할 것이다. 전체 코드, 데이터, 단위 테스트, CI 설정, 재현 파이프라인이 공개되어 있으며, 후속 연구자는 `make all` 단일 명령으로 본 연구를 완전히 재현할 수 있다.

---

## 감사의 글

본 연구의 방향 설정과 피드백을 주신 임정묵 지도교수께 감사드린다. 또한 퍼저 v4와 테스트 구축을 공동 개발한 팀원들에게 감사드린다.

---

## 참고 문헌

1. Fei, B., Kim, H., & Park, S. (2024). KDPII: Korean De-identification PII Dataset. *IEEE Access*, 12, 135626–135641.
2. Microsoft Presidio Release Notes. (2025). KR_RRN (#1675, #1807), KR_BRN (#1822), KR_FRN (#1825), KR_DRIVER_LICENSE (#1820), KR_PASSPORT (#1814). Released in v2.2.361.
3. LiteLLM Documentation. (2026). Guardrail Policies and Korean PII Masking v2. docs.litellm.ai
4. TrueFoundry Blog. (2026). Integrating Palo Alto Prisma AIRS with TrueFoundry AI Gateway.
5. Mindgard & Hackett. (2025). Bypassing LLM Guardrails: A Systematic Study. *Proceedings of AI Security Summit*.
6. CrowdStrike. (2025). IM/PT Taxonomy: A Framework for Industrial Machine-Learning Model Prompt Threats.
7. Palo Alto Unit 42. (2025). 22 Web IDPI Techniques Observed in the Wild.
8. KLUE Benchmark Team. (2021). KLUE: Korean Language Understanding Evaluation. *arXiv:2105.09680*.

---

## 인용 (BibTeX)

```bibtex
@techreport{min_korean_pii_2026,
  title        = {한국어 LLM 게이트웨이 환경에서 다계층 PII 가드레일의 취약성 분석 및 정규화 기반 방어 계층 설계},
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

## 부록 A. 평가 데이터

본 연구의 전체 사례별 평가 결과(10,000건 × 4 구성 × layer_results)는 공개 레포지토리의 `PII/results/data/` 디렉토리에 포함된다. 파일 크기는 각 11~17MB이며, synthetic AWS 키는 "AKIAXXXXXXXXXXXXXXXX"로 마스킹되었다(GitHub secret scanner 대응).

## 부록 B. 재현 명령

```bash
git clone https://github.com/vmaca123/My-AI-Security-Project
cd My-AI-Security-Project
cp .env.example .env  # 환경변수 채움: OPENAI_API_KEY, AWS_*, LAKERA_API_KEY
make setup            # Docker stack 기동
make deploy-l0        # Layer 0 모듈 배포
make test             # 89개 unit test 실행
make all              # 전체 평가 파이프라인 (약 4시간, 약 $5)
```

## 부록 C. 주요 Figure 목록

- Fig 10: 4-way 전체 비교 (슬라이스별 bypass rate)
- Fig 11: KR_semantic 4-way head-to-head (본 논문의 핵심 figure)
- Fig 12: Top 15 hardest PII 4-way 비교
- Fig 13: Layer 0 Ablation (Norm vs Dict 기여도)

모든 figure는 `PII/results/figures/` 디렉토리에 300dpi PNG로 포함되어 있다.
