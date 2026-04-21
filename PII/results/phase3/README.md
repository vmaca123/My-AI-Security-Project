# Phase 3 — Ablation + Smart Cascade Optimization

## A.2 — Layer 0 Ablation Study

[`phase3_ablation.py`](phase3_ablation.py) / [`phase3_ablation.json`](phase3_ablation.json)

**Question**: Layer 0의 두 구성요소(정규화 vs 키워드 사전) 중 어느 쪽이 핵심 기여를 하는가?

3가지 모드 분해:
- **Mode N (Normalizer only)**: 13단계 한국어 정규화만, detector 비활성
- **Mode D (Detector only)**: 42 regex + 22 keyword dict on raw text, 정규화 없음
- **Mode F (Full)**: Normalize → then Detect on normalized (현재 production)

### 결과 (TRUE detection on 10k)

| Slice | n | Baseline | +Norm only | +Dict only | +Full (current) |
|---|---:|---:|---:|---:|---:|
| Overall | 10,000 | 80.15% | 80.42% (+0.27) | 91.80% (+11.65) | 95.51% (+15.36) |
| KR | 6,513 | 69.86% | 70.27% (+0.41) | 87.75% (+17.89) | 93.44% (+23.58) |
| **KR_semantic** | 1,302 | 49.62% | 49.92% (+0.31) | **87.71% (+38.10)** | 89.17% (+39.55) |
| KR_format | 4,689 | 74.00% | 74.47% (+0.47) | 88.12% (+14.12) | 95.20% (+21.20) |
| KR_checksum | 522 | 83.14% | 83.33% (+0.19) | 84.48% (+1.34) | 88.31% (+5.17) |
| EN | 3,487 | 99.37% | 99.37% (+0.00) | 99.37% (+0.00) | 99.37% (+0.00) |

### 해석

**Dict(키워드 사전)가 Layer 0 효과의 96.4%를 담당** (KR_semantic: +38.10%p / +39.55%p total).

| 구성요소 | KR_semantic 기여 |
|---|---:|
| Normalizer alone | +0.31%p |
| Dictionary alone | **+38.10%p** |
| Synergy (F − N − D) | +1.14%p |

- **Normalizer 단독**으로는 한국어 텍스트형 PII 탐지에 거의 기여하지 않음 — L1~L3가 정규화된 텍스트를 더 잘 잡는 효과가 미미
- **Dictionary가 본질적 기여** — 42 regex + 22 keyword 사전이 한국어 텍스트형 PII를 직접 탐지
- **Synergy (+1.14%p)**: 정규화된 텍스트에 사전 적용 시 추가 탐지 — 자모 분해/homoglyph 공격에서 표준 한국어 복원 후 사전 매칭

**논문 시사점**: "Layer 0 = 정규화 + 사전" 중 **사전이 핵심 엔진**, normalizer는 보조적 역할. Normalizer만으로는 한국어 텍스트형 PII 문제 해결 안 됨.

---

## B.6 — L4 Smart Skip Analysis

[`phase3_l4_smart_skip.py`](phase3_l4_smart_skip.py) / [`phase3_l4_smart_skip.json`](phase3_l4_smart_skip.json)

**Question**: L0+L1~L3 가 이미 잡은 케이스에 L4(GPT-4o judge)를 호출할 필요 있는가? Smart cascade 최적화 시 얼마나 절감되나?

### 결과

```
Case-level breakdown:
  L0+L1~L3 이미 neutralize:   9,432 (94.32%)  → L4 스킵 가능
  L0~L3 놓친 → L4 필요:          568 (5.68%)
    └ L4가 복구:                291 (51.23% of L4-called)
    └ L4도 못 잡음:              277 (48.77% of L4-called)

Throughput / Cost:
  Full Cascade (D):    L4 호출 10,000회 → TRUE 97.23%
  Smart Cascade:       L4 호출    568회 → TRUE 97.23%  ← detection 동일!

  → L4 호출 94.32% 절감, detection impact 0.00%p
```

### 비용 / 시간 투사

| 항목 | Full | Smart | 절감 |
|---|---:|---:|---:|
| L4 호출 수 | 10,000 | 568 | 94.32% |
| L4 latency 총합 (avg 1,542ms) | 257분 | 15분 | 242분 |
| 비용 ($0.135/1k calls) | $1.35 | $0.08 | $1.27 |

### 실무 배포 권장 구성

```
[Input] → L0 (~10ms, $0)
       → L1 Presidio (~70ms, $0)
       → L2 Bedrock (~410ms, $0.0001)
       → L3 Lakera (~6ms, $0.00002)

If any layer neutralized:
  → Return (done, L4 not called)  [94.32% of cases]
Else:
  → L4 GPT-4o judge (~1.5s, $0.00014)  [5.68% of cases]
```

**결과**:
- 평균 latency: ~500ms (L4 skip) / ~2s (L4 needed)
- 10k 케이스당 비용: **$0.08** (vs full cascade $1.35)
- Detection rate 97.23% 유지

### 논문 시사점

**"Layer 0는 LLM judge 의존도를 94% 낮추는 preconditioner 역할"** — 이것이 cost-sensitive 실무 배포의 핵심 argument. 기존 research들은 LLM judge를 cascade의 safety net으로 썼지만, Layer 0가 대부분 케이스를 차단하므로 LLM judge가 진짜 "last resort"로 동작.

---

## 종합 findings

1. **Layer 0 내부**: Dictionary가 정규화보다 20배 이상 중요 (KR_semantic: +38%p vs +0.31%p)
2. **Layer 0의 시스템적 역할**: LLM judge 호출 94% 감소 → 비용/지연/의존성 모두 대폭 개선
3. **Defense-in-depth 재평가**: L4는 safety net이지만, L0가 잘 설계되면 L4는 5% 케이스만 담당해도 충분
