# Evaluation Results

1만건 stratified 샘플에 대한 5계층(L0~L4) 가드레일 평가 결과.

## 디렉토리 구조

```
results/
├── summaries/   — TRUE detection 집계 JSON + 최종 메모 MD
├── figures/     — 논문/발표용 PNG (300dpi)
└── data/        — Raw 평가 결과 (case-level layer_results)
```

## summaries/

| 파일 | 내용 |
|---|---|
| `RESULTS_10k_summary.md` | 전체 결과 종합 (헤드라인 + 표 + 해석) |
| `run_b_10k_summary.json` | L1~L3 baseline 집계 |
| `run_c_l0_summary.json` | L0~L3 vs L1~L3 3-way 비교 |
| `run_d_4way_summary.json` | Cascade 기반 3-way |
| `run_e_final_summary.json` | **최종 4-way** (A/B/C/D, 전 10k에 L4 on) |
| `analyze_l0_deep.json` | L0 solo catches 1,444건 + 남은 bypass 602건 + FP 분석 |

## figures/

| 파일 | 설명 |
|---|---|
| `fig1_overall_bypass.png` | Baseline vs L0 bypass (슬라이스별) |
| `fig2_lang_x_validity.png` | Lang × Validity TRUE rate |
| `fig3_hardest_pii.png` | Top 20 hardest PII before/after L0 |
| `fig4_mutation_level.png` | 변이 레벨별 회복 |
| `fig5_l0_solo_pii.png` | L0 단독 차단 PII 분포 |
| **`fig10_4way_bypass.png`** | **4-way 슬라이스별 bypass** (최종) |
| **`fig11_kr_semantic_4way.png`** | **KR_semantic 4-way head-to-head** (핵심 figure) |
| **`fig12_hardest_pii_4way.png`** | **Top 15 hardest PII 4-way** (최종) |

## data/

Case-level 원본 평가 결과. 각 케이스마다 `layer_results` 배열에 레이어별 action/output/latency 포함.

| 파일 | 크기 | 설명 |
|---|---:|---|
| `payloads_10k.json` | 3.4MB | Fuzzer 출력에서 stratified 샘플링한 1만건 |
| `eval_10k_l1l3.json` | 14MB | A) Baseline (L1~L3) |
| `eval_10k_l1l4_full.json` | 11MB | B) Baseline + L4 (전 10k L4 풀 호출) |
| `eval_10k_l0_l1l3.json` | 17MB | C) With L0 (L0~L3) |
| `eval_10k_l0_l1l4_full.json` | 13MB | D) Full (L0~L4) |

## Reproduce

```bash
# 환경 준비
docker compose -f ../config/docker-compose.yml up -d
# evaluation/ 스크립트 순차 실행 (상세 순서는 evaluation/README.md)
cd ../evaluation
python sample_10k.py                    # → payloads_10k.json
python guardrail_evaluator.py \
  --input payloads_10k.json \
  --output eval_10k_l1l3.json \
  --layers "Presidio PII,Bedrock Guardrail,Lakera"
python cascade_evaluator.py \
  --input eval_10k_l1l3.json \
  --output eval_10k_l1l4_full.json \
  --all --concurrency 5 --sleep 0.3
# ... (L0 포함도 동일 패턴)
python run_e_final_4way.py              # → run_e_final_summary.json
python make_figures_final.py            # → fig10~12.png
```
