# 정연서한테 보낼 PPT 작성 가이드

> 2026-04-23 기준 — 내일 중간발표 + 콘테스트 최종 발표 양쪽 모두 대응

---

## 1. 핵심 framing 합의 사항 (절대 원칙)

### ❌ 쓰지 말 것
- "한국어 PII **보호 엔진**" — 단독 31%라 과장 표현
- "통합 보호 솔루션" — 영어 PII 못 잡으니 부정확
- "단독으로 모든 PII 방어" — false claim

### ✅ 정확한 표현
- "**한국어 PII 보강 계층(Complementary Layer)**"
- "**다계층 방어의 한국어 특화 missing link**"
- "**LLM 없는 결정론적 한국어 PII 탐지·마스킹 모듈**"
- "**기존 가드레일의 한국어 공백을 메우는 보강선**"

### 영문 (필요 시)
- Korean PII Complementary Layer
- Korean-Specific Defense Layer (for multi-tier guardrail stack)

---

## 2. 절대 빠지면 안 되는 핵심 데이터

### 2.1 4-way 비교 (10,000건 평가)

| Config | 구성 | TRUE | Real bypass | Latency p99 | 비용/10k |
|---|---|---:|---:|---:|---:|
| A) Baseline | L1~L3 (LLM 없음) | 80.15% | 19.85% | 1,317ms | $0 |
| B) Baseline+L4 | L1~L4 (GPT-4o-mini) | 90.96% | 9.04% | 4,819ms | $1.35 |
| **C) +Layer 0** ★ | L0~L3 (LLM 없음) | **94.32%** | 5.68% | **830ms** | **$0.08** |
| D) Full | L0~L4 (둘 다) | 97.23% | 2.77% | 4,762ms | $1.35 |

### 2.2 KR_semantic (한국어 텍스트형 PII, n=1,302) — ★ 핵심 슬라이스

| Config | TRUE | Bypass |
|---|---:|---:|
| A | 49.62% | 50.38% |
| B (LLM judge) | 87.40% | 12.60% |
| **C (Layer 0)** | **96.39%** | **3.61%** |
| D | 98.85% | 1.15% |

→ **C가 B를 +8.99%p 능가** (Layer 0가 GPT-4o-mini judge보다 한국어 텍스트형 PII에서 더 잘 잡음)

### 2.3 통계적 유의성 (McNemar)
- B vs C: b=291, c=627, χ²=122, **p < 2e-28** (결정적)
- 의미: Layer 0가 LLM judge보다 336건 더 독립적으로 catch

### 2.4 Layer 0 단독 성능 (정직하게 명시)

| 슬라이스 | 단독 TRUE |
|---|---:|
| Overall | 30.96% |
| Korean | 47.54% |
| KR_semantic | **80.65%** ← 강점 |
| KR_format | 41.57% |
| KR_checksum | 18.58% (Presidio가 담당) |
| English | 0.00% (의도적, 한국어 전용) |

→ **단독 31%, 조합 94%** — "보강 계층" framing의 정량 근거

---

## 3. 슬라이드 흐름 권장 (15분 발표 기준)

### S1. 표지 + 한 줄 주장
> "기존 가드레일이 한국어 텍스트형 PII에 50% 우회되는 공백을, LLM 없는 결정론적 보강 계층(Layer 0)으로 96%까지 회복시킨다."

### S2. 문제 (RQ1)
- 영어 PII 99% 방어 → 한국어 텍스트형 50% 우회 (49.62%)
- session 95.9%, court 92.8%, allergy 92.3% 우회

### S3. 시스템 아키텍처
- 5계층 그림 (L0~L4)
- Layer 0 위치 강조 (pre_call 최선단)

### S4. Layer 0 설계
- 13단계 정규화 + 42 정규식 + 22 키워드 사전
- LLM 없음, 결정론적, 로컬

### S5. 평가 데이터셋
- v4 fuzzer, 10,000건 stratified
- 91종 PII × 6 변이 레벨

### S6. ★ 핵심 결과 (4-way 비교)
- 위 표 2.1 그대로

### S7. ★ KR_semantic head-to-head (fig11.png)
- Layer 0 vs LLM judge 시각화

### S8. 통계적 유의성
- McNemar p < 1e-28 표

### S9. 비용·지연 비교
- Layer 0 vs L4: 220배 빠름, $0
- Smart Cascade: L4 호출 94% 절감

### S10. Ablation (fig13.png)
- Dict가 96% 기여, Norm 보조

### S11. ★ 정직한 한계 (정연서 절대 빼지 말 것)
- L0 단독: Overall 31%, KR_semantic 80.65%
- "보강 계층"이지 "단독 보호 엔진" 아님

### S12. 최종 목표 (성장 로드맵)
- Phase A (체크섬 추가, 2~3h) → KR_checksum 18% → 85%+
- Phase B (포맷 확장, 1d) → KR_format 42% → 90%+
- Phase C (사전 강화, 1~2d) → KR_semantic 81% → 95%+
- Phase D (NER, 1d) → 단독 한국어 95%+ 보호 엔진 완성

### S13. 의미 (왜 이게 중요한가)
- 폐쇄망(공공·의료·군) 단독 배포 가능
- LLM judge 의존 탈피
- 7가지 deployment 가능 (Python lib/REST/CLI/게이트레일/파이프라인/로그/IDE)

### S14. Q&A 슬라이드 (대비)
- 결론 + 레포 주소 + 발표자 contact

---

## 4. Q&A 대비 답변 카드

### Q1. "단독으로 못 쓰면 의미 있나?"
A. "현재는 보강 계층입니다. **다계층 방어가 실무 표준이므로 보강 자체로도 가치**가 있고, 후속 로드맵(Phase A~D)으로 단독 95%+ 가능합니다. 콘테스트 후 Phase A부터 진행 예정입니다."

### Q2. "왜 GPT-4o judge보다 좋다는 게 의미 있나?"
A. "비용 220배 차이($1.35 vs $0.08), 폐쇄망 사용 가능, 결정론적(재현 가능). 통계적으로 p<1e-28로 결정적 차이입니다."

### Q3. "Presidio도 한국어 지원하지 않나?"
A. "RRN 등 5종 숫자형만 지원. 텍스트형(알레르기·처방·회사 등)은 49.62%. Layer 0가 그 공백을 메웁니다."

### Q4. "Bedrock 빼고 Azure AI Language로 가면 어땠나?"
A. "둘 다 cloud API라 본질적 한계 동일. Azure가 한국어 NER fine-tuned 가능성 있어 후속 비교 가치 있음. 현재 검증된 게 Bedrock이라 그대로 사용. Discussion에 future work로 언급됨."

### Q5. "왜 영어는 안 다루나?"
A. "Presidio가 영어 PII 99% 방어. **분업 설계** — Presidio가 영어/숫자형 담당, Layer 0가 한국어/텍스트형 담당. 바퀴 재발명 안 함."

### Q6. "LLM judge가 하는 일을 왜 사전이 더 잘 잡지?"
A. "한국어 텍스트형 PII는 의미가 고정된 제한된 어휘(allergy/diagnosis/company 등). LLM 추론보다 사전 매칭이 정확. Ablation에서 Dict가 96% 기여 입증."

### Q7. "콘테스트 끝나고 어떻게 발전?"
A. "(1) Phase A~D로 단독 보호 엔진화 (2) Azure AI Language와 5-way 비교 (3) Output fuzzer 평가 (4) Injection 결합 공격 (5) 다국어 확장 (일본어/중국어)"

---

## 5. 자주 헷갈리는 표현 (절대 주의!)

| 잘못된 표현 | 정확한 표현 |
|---|---|
| "L0가 LLM 대체" | "L0가 한국어 텍스트형 PII에서 LLM judge 능가" |
| "단독으로 96% 탐지" | "L0+L1~L3 조합 시 KR_semantic 96.39%" |
| "Layer 0가 모든 PII 보호" | "Layer 0가 한국어 PII 공백 보강" |
| "LLM 필요 없음" | "Layer 0는 LLM 없이 동작 / Smart Cascade로 LLM 호출 94% 절감" |
| "보호 엔진" (현재 시점) | "보강 계층" — "보호 엔진"은 최종 목표 |

---

## 6. 첨부 자료 (PPT에 embed 권장)

- `PII/results/figures/fig11_kr_semantic_4way.png` — ★ 핵심 figure
- `PII/results/figures/fig10_4way_bypass.png` — 슬라이스별 비교
- `PII/results/figures/fig13_ablation.png` — Ablation
- `PII/results/figures/fig12_hardest_pii_4way.png` — Top 15 hardest PII

---

## 7. 발표 끝 멘트 권장

> "본 연구는 LLM 게이트웨이의 한국어 보안 사각지대를 정량 입증하고, LLM 없는 결정론적 보강 계층(Layer 0)이 GPT-4o-mini judge보다 더 효과적임을 통계적으로 결정적인 차이(p<1e-28)로 확립했습니다.
>
> **현재의 L0는 다계층 방어의 보강 모듈이지만**, Phase A~D 로드맵으로 단독 한국어 PII 보호 엔진으로 성장시키는 것이 최종 목표입니다. 이는 폐쇄망 환경, 외부 API 의존 불가 시나리오, LLM 게이트웨이 외 다양한 deployment에서 사용 가능한 진짜 단독 보호 엔진을 의미합니다.
>
> 전체 코드, 데이터, 89개 단위 테스트, GitHub Actions CI, 단일 명령 재현 환경(`make all`)을 공개합니다. 감사합니다."

---

## 📎 참고 파일 위치

| 파일 | 용도 |
|---|---|
| `paper/결과요약_for_PPT.docx` | PPT 작성 시 표·문구 copy/paste |
| `paper/캡스톤논문_전체_v1.docx` | 전체 논문 (24p) |
| `paper/capstone_main_v1.md` | 본문 markdown (수정 시 사용) |
| `PII/results/figures/` | 모든 figure (300dpi PNG) |
| `PII/results/phase*/` | 각 phase별 분석 결과 |
| `PII/results/phase1/phase1_l0_standalone.json` | ★ L0 단독 성능 (보강 계층 framing 근거) |
| `CHANGELOG.md` | 프로젝트 history 누적 기록 |

---

질문 있으면 민우한테. 이 가이드는 PPT 작성 전에 **반드시 한 번 읽기**.
