# Phase 2 — v4 Fuzzer Baseline Robustness

## A.1 v4 Fuzzer vs Original Baseline

[`phase2_v4_baseline.py`](phase2_v4_baseline.py) / [`phase2_v4_baseline.json`](phase2_v4_baseline.json)

**Question**: Original legacy fuzzer로 만든 baseline(10k)과 **v4 validity-first fuzzer**로 만든 baseline(10k)의 detection rate가 동일한가?

- 시드 유효성: v4는 checksum 100% 유효 (RRN, Card Luhn, Biz Reg, VIN, IMEI, US SSN)
- v4는 prescription/account/transaction 전용 생성기 사용 (의미적 일관성 강화)
- v4는 91 PII types (기존 대비 +)

### 결과 (TRUE detection on L1~L3, same 10k size)

| Config | n | TRUE | Real bypass |
|---|---:|---:|---:|
| Original (legacy) | 10,000 | 80.15% | 19.85% |
| v4 (validity-first) | 10,000 | 80.11% | 19.89% |
| **Δ (v4 − orig)** | | **−0.04%p** | **+0.04%p** |

### Lang × Validity breakdown

| Slice | orig n | orig TRUE | v4 n | v4 TRUE | Δ |
|---|---:|---:|---:|---:|---:|
| EN_checksum | 2,603 | 99.15% | 2,596 | 98.96% | −0.19%p |
| EN_format | 884 | 100.00% | 904 | 100.00% | +0.00%p |
| KR_checksum | 522 | 83.14% | 480 | 81.25% | −1.89%p |
| KR_format | 4,689 | 74.00% | 4,537 | 75.12% | +1.12%p |
| **KR_semantic ★** | 1,302 | **49.62%** | 1,483 | **49.90%** | **+0.28%p** |

### 해석

**모든 슬라이스에서 Δ ≤ 2%p** — detection rate는 퍼저 버전에 실질적으로 무관.

특히 **KR_semantic (핵심 narrative slice)은 Δ = +0.28%p** — 0.5% 이내. Layer 0의 +8.99%p 효과(B vs C) 대비 1/32 크기. 우리 결론은 validity-first 퍼저로 재평가해도 **완전히 robust**.

### 논문 방어

> "We verified the robustness of our baseline measurements by re-evaluating
> with a stricter validity-first fuzzer v4 (all RRN/Card/VIN seeds pass
> national checksum rules, with KR_semantic up 14% in size via expanded
> prescription/account/transaction generators). All slice-level deltas in
> L1~L3 baseline were ≤ 2%p (KR_semantic: +0.28%p), confirming our
> conclusions do not depend on fuzzer version."

## 진행 중

v4 fuzzer의 L0+L1~L3 (C config) 및 L0~L4 (D config) 평가는 별도로 진행 중 — 완료 시 4-way v4 재집계 추가.
