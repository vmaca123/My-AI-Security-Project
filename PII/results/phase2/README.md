# Phase 2 — v4 Fuzzer Full Robustness Study

**Complete 4-way re-evaluation** using the team's validity-first `korean_pii_fuzzer_v4` (91 PII types, checksum 100% valid, prescription/account/transaction dedicated generators with Korean-specific L4/L5 mutations).

## Files

| File | Purpose |
|---|---|
| `phase2_v4_baseline.py` / `.json` | L1~L3 baseline comparison (orig vs v4) |
| `phase2_v4_compare.py` / `.json` | A + C comparison (Layer 0 effect across fuzzer versions) |
| `phase2_v4_final_4way.py` / `.json` | **Full 4-way (A/B/C/D)** on v4 payloads |

## Full 4-way Results (v4 vs v1 original)

| Config | 구성 | v1 TRUE | v4 TRUE | Δ |
|---|---|---:|---:|---:|
| A Baseline | L1+L2+L3 | 80.15% | 80.11% | −0.04%p |
| B Baseline+L4 | L1+L2+L3+L4 | 90.96% | 90.43% | −0.53%p |
| **C With Layer 0** | L0+L1+L2+L3 | 94.32% | **94.99%** | **+0.67%p** |
| **D Full** | L0+L1+L2+L3+L4 | 97.23% | **97.68%** | **+0.45%p** |

### Layer 0 효과는 v4에서 더 강함

| Comparison | v1 | v4 | Δ effect |
|---|---:|---:|---:|
| Layer 0 effect (C − A) | +14.17%p | **+14.88%p** | +0.71 |
| LLM judge effect (B − A) | +10.81%p | +10.32%p | −0.49 |
| **L0 vs LLM head-to-head (C − B)** | **+3.36%p** | **+4.56%p** | **+1.20** |

**Layer 0의 LLM judge 대비 우위가 validity-first 퍼저에서 1.20%p 더 커짐.**

### KR_semantic (핵심 slice)

| Config | v1 (n=1,302) | v4 (n=1,483) | Δ |
|---|---:|---:|---:|
| A Baseline | 49.62% | 49.90% | +0.28 |
| B +LLM judge | 87.40% | **84.76%** | −2.64 |
| **C +Layer 0** | 96.39% | 95.41% | −0.98 |
| **D Full** | 98.85% | 97.64% | −1.21 |

**v4에서 LLM judge의 KR_semantic 탐지가 약해지는 반면(84.76%), Layer 0는 95%+ 유지**. → Layer 0 > LLM judge 격차 v4에서 **+10.65%p**.

## 왜 v4에서 Layer 0 우위가 커지는가?

v4의 새 변이들:
- **prescription_korean**: EMR 라인(`Rx) 메트포르민 500mg PO bid pc x 30D`), pharmacy 라벨, 한국어 sig
- **account_korean**: bank alias, label 변형(입금/환불/정산), 콜센터 문맥
- **transaction_korean**: CSV row, type abbrev (카승/체크승인), 문맥 6종

이 변이들은 **표면적으로 구조가 복잡해지지만 핵심 키워드(약품명, 은행명, 거래구분)는 유지**됨. Layer 0의 keyword dictionary는 키워드를 직접 보므로 영향이 적고, LLM judge는 긴 구조에서 혼란스러워함.

## 논문 주장 (robustness section)

> "We validated the robustness of our main conclusions by re-evaluating
> with a stricter validity-first fuzzer (v4) generating 91 PII types with
> checksum validation + 3 dedicated semantic generators (prescription,
> account, transaction) adding 21 Korean-specific L4/L5 mutations. Under
> this harder evaluation, the Layer 0 vs GPT-4o-mini judge advantage
> actually *widens*: from +3.36%p (v1) to +4.56%p (v4) overall, and from
> +8.99%p to +10.65%p on the KR_semantic slice. This strongly suggests
> our finding is a property of the defense mechanism, not the fuzzer."

## 데이터 파일

- `../../../eval_10k_v4_l1l3.json` (~14MB, 로컬 평가 결과 / repo에는 요약만)
- `../../../eval_10k_v4_l0_l1l3.json`
- `../../../eval_10k_v4_l1l4_full.json`
- `../../../eval_10k_v4_l0_l1l4_full.json`
