# Evaluation Scripts

LiteLLM Gateway를 통해 4계층(+Layer 0) 가드레일 스택을 진짜 호출해서 평가하고, TRUE detection 기준으로 집계·시각화하는 스크립트 모음.

## 실행 순서

```
1. sample_10k.py              → payloads_10k.json  (stratified 1만건 샘플)
2. guardrail_evaluator.py     → eval_10k_l1l3.json (L1~L3 baseline)
3. cascade_evaluator.py --all → eval_10k_l1l4_full.json (+ L4)
4. guardrail_evaluator.py (L0 포함) → eval_10k_l0_l1l3.json
5. (L4 결과 merge) → eval_10k_l0_l1l4_full.json  (5-layer)
6. run_e_final_4way.py        → run_e_final_summary.json
7. analyze_l0_deep.py         → analyze_l0_deep.json
8. make_figures_final.py      → fig10~12.png
```

## 스크립트별 역할

### Core 평가기

| 파일 | 역할 |
|---|---|
| `guardrail_evaluator.py` | LiteLLM `/guardrails/apply_guardrail` 엔드포인트로 N계층 순차 호출. `--layers`로 대상 가드레일 지정. `--resume`으로 중단 지점부터 재개. 연속 ERROR 30회면 auto-abort. |
| `cascade_evaluator.py` | L1~L3 평가 결과에서 bypass된 케이스(FALSE+BYPASS)에만 L4 cascade 호출. `--all` 플래그로 TRUE 케이스도 강제 평가 (공정 4계층 비교용). `--concurrency N`으로 OpenAI 병렬 호출 제어. |
| `analyze_true_detection.py` | TRUE/FALSE/BYPASS 분류 로직 reference. `cascade_evaluator`와 동일한 `is_pii_in_text()` 사용. |
| `sanity_check_50.py` | 랜덤 50건을 기존 평가 결과와 재실행 비교 — 가드레일 정책 변경 감지용. |

### 집계 스크립트 (TRUE detection 기준)

| 파일 | 역할 |
|---|---|
| `run_b_10k_baseline.py` | L1~L3 1만건 baseline 집계 → `run_b_10k_summary.json` |
| `run_c_l0_compare.py` | L0~L3 vs L1~L3 비교 집계 → `run_c_l0_summary.json` |
| `run_d_4way_compare.py` | Cascade 결과까지 포함한 3-way 집계 → `run_d_4way_summary.json` |
| `run_e_final_4way.py` | **최종 4-way** (A/B/C/D) 집계, full L4 on 전 10k → `run_e_final_summary.json` |
| `analyze_l0_deep.py` | L0 solo catches / 남은 bypass / EN false positive 분석 → `analyze_l0_deep.json` |

### 시각화

| 파일 | 역할 |
|---|---|
| `make_figures.py` | fig1~5 (초기 Layer 0 효과) |
| `make_figures_4way.py` | fig6~9 (3-way 중간 버전) |
| `make_figures_final.py` | **fig10~12** (최종 4-way) |

## TRUE detection 정의

Raw `output != text` 기준은 **부풀려진 detection** — Presidio가 PERSON만 마스킹하고 진짜 PII(전화번호)는 그대로 둔 경우도 "detected"로 카운트됨.

따라서 `classify()` 함수로 3단계 분류:

- **TRUE**: 어떤 레이어라도 PII 값을 실제 neutralize (BLOCK 또는 진짜 PII 값을 마스킹)
- **FALSE**: 텍스트를 변경했지만 PII 원본 값이 여전히 텍스트에 남아있음 (주변만 잡음)
- **BYPASS**: 모든 레이어가 텍스트 변경 안 함

**Real bypass rate = FALSE + BYPASS** (진짜 뚫린 케이스 비율)

## 핵심 수치 (10k stratified, 4-way)

| Config | TRUE | Real bypass |
|---|---:|---:|
| A) Baseline (L1~L3) | 80.15% | 19.85% |
| B) Baseline + L4 | 90.96% | 9.04% |
| C) With L0 (L0~L3, no LLM) | **94.32%** | **5.68%** |
| D) Full (L0~L4) | **97.23%** | **2.77%** |

- **C beats B by +3.36%p** (Layer 0 > GPT-4o judge in overall)
- **C beats B by +8.99%p on KR_semantic** (한국어 텍스트형 PII)

자세한 결과는 [../results/summaries/RESULTS_10k_summary.md](../results/summaries/RESULTS_10k_summary.md) 참조.
