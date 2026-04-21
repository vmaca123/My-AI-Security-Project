#!/usr/bin/env bash
# Full evaluation pipeline runner.
# Prereq: Docker stack running + Layer 0 deployed + OpenAI/AWS/Lakera keys in env.
# Estimated time: ~4 hours. Estimated cost: ~$5 (gpt-4o-mini judge).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVAL="$ROOT/PII/evaluation"
DATA="$ROOT/PII/results/data"

echo "[1/9] Gateway health check"
curl -sf http://localhost:4000/health/liveness >/dev/null || {
  echo "Gateway not alive. Run 'make setup && make deploy-l0'."; exit 1;
}

echo "[2/9] Generate fuzzer payloads (10k+ synthetic PII)"
cd "$ROOT/PII/fuzzer"
python korean_pii_fuzzer_v4.py --count 3 --output "$EVAL/fuzzer_out_v4.json"

echo "[3/9] Stratified 10k sampling"
cd "$EVAL" && python sample_10k.py

echo "[4/9] L1~L3 baseline evaluation (Presidio + Bedrock + Lakera, ~80 min)"
python guardrail_evaluator.py \
  --input payloads_10k.json \
  --output eval_10k_l1l3.json \
  --layers "Presidio PII,Bedrock Guardrail,Lakera"

echo "[5/9] L0+L1~L3 evaluation (+Korean normalizer, ~80 min)"
python guardrail_evaluator.py \
  --input payloads_10k.json \
  --output eval_10k_l0_l1l3.json \
  --layers "korean-layer0,Presidio PII,Bedrock Guardrail,Lakera"

echo "[6/9] L4 cascade on full 10k (GPT-4o-mini judge, ~40 min)"
python cascade_evaluator.py \
  --input eval_10k_l1l3.json \
  --output eval_10k_l1l4_full.json \
  --all --concurrency 5 --sleep 0.3

echo "[7/9] Merge L4 into L0 dataset for 5-layer view"
python -c "
import json
l0 = json.load(open('eval_10k_l0_l1l3.json', encoding='utf-8'))
l4 = json.load(open('eval_10k_l1l4_full.json', encoding='utf-8'))
L4 = 'gpt4o-pii-judge'
l4_map = {}
for r in l4['results']:
    for lr in r['layer_results']:
        if lr['layer'] == L4:
            l4_map[r['id']] = lr
            break
for r in l0['results']:
    if r['id'] in l4_map and not any(lr['layer']==L4 for lr in r['layer_results']):
        r['layer_results'].append(l4_map[r['id']])
json.dump(l0, open('eval_10k_l0_l1l4_full.json','w', encoding='utf-8'), ensure_ascii=False)
print('merged into eval_10k_l0_l1l4_full.json')
"

echo "[8/9] Aggregate 4-way + figures"
python run_e_final_4way.py
python make_figures_final.py

echo "[9/9] Done. Results:"
echo "  - $EVAL/run_e_final_summary.json"
echo "  - figures fig10~12.png in same dir"
echo "  - raw case-level data in eval_10k_*.json"
