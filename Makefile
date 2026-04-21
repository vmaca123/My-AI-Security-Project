# Korean PII Guardrail — Single-command reproduction
#
# Usage:
#   make help        — show this help
#   make setup       — start Docker stack (LiteLLM + Presidio + Postgres)
#   make deploy-l0   — copy Layer 0 modules + config into LiteLLM container
#   make test        — run Layer 0 pytest suite
#   make sample      — generate stratified 10k payload from fuzzer
#   make eval-base   — L1~L3 baseline evaluation (~80 min)
#   make eval-l0     — L0+L1~L3 evaluation (~80 min)
#   make eval-l4     — L4 cascade on baseline, all 10k (~40 min)
#   make eval-full   — L0+L1~L4 merge (no extra calls, joins existing L4)
#   make aggregate   — run 4-way summary (run_e_final_4way)
#   make figures     — generate fig10~12 PNGs
#   make analyze     — run ablation + smart-skip + mcnemar + latency
#   make all         — full pipeline (sample → eval all → aggregate → figures → analyze)
#   make down        — stop Docker stack

SHELL := /bin/bash
.DEFAULT_GOAL := help

EVAL_DIR := PII/evaluation
DATA_DIR := PII/results/data
FIG_DIR  := PII/results/figures
SUM_DIR  := PII/results/summaries
PHASE1_DIR := PII/results/phase1
PHASE3_DIR := PII/results/phase3

help:  ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-14s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup:  ## Start Docker stack
	docker compose -f PII/config/docker-compose.yml up -d
	docker start presidio-analyzer presidio-anonymizer 2>/dev/null || true
	@echo "Waiting for LiteLLM to be alive..."
	@until curl -sf http://localhost:4000/health/liveness >/dev/null 2>&1; do sleep 2; done
	@echo "Gateway alive."

deploy-l0:  ## Copy Layer 0 modules + config into LiteLLM container
	docker cp PII/layer_0/korean_normalizer.py litellm-litellm-1:/app/korean_normalizer.py
	docker cp PII/layer_0/korean_pii_detector.py litellm-litellm-1:/app/korean_pii_detector.py
	docker cp PII/layer_0/korean_layer0_guardrail.py litellm-litellm-1:/app/korean_layer0_guardrail.py
	docker cp PII/layer_4/custom_guardrail.py litellm-litellm-1:/app/custom_guardrail.py
	docker cp PII/config/config.yaml litellm-litellm-1:/app/config.yaml
	docker compose -f PII/config/docker-compose.yml restart litellm
	@sleep 15 && curl -s http://localhost:4000/health/liveness

test:  ## Run Layer 0 pytest suite
	cd PII/layer_0 && pytest tests/ -v

sample:  ## Generate stratified 10k payload via fuzzer
	cd PII/fuzzer && python korean_pii_fuzzer_v4.py --count 3 --output ../../fuzzer_out_v4.json
	cd $(EVAL_DIR) && python sample_10k.py

eval-base:  ## L1~L3 baseline (~80 min)
	cd $(EVAL_DIR) && python guardrail_evaluator.py \
	  --input payloads_10k.json \
	  --output eval_10k_l1l3.json \
	  --layers "Presidio PII,Bedrock Guardrail,Lakera"

eval-l0:  ## L0+L1~L3 (~80 min)
	cd $(EVAL_DIR) && python guardrail_evaluator.py \
	  --input payloads_10k.json \
	  --output eval_10k_l0_l1l3.json \
	  --layers "korean-layer0,Presidio PII,Bedrock Guardrail,Lakera"

eval-l4:  ## L4 cascade on full 10k (~40 min)
	cd $(EVAL_DIR) && python cascade_evaluator.py \
	  --input eval_10k_l1l3.json \
	  --output eval_10k_l1l4_full.json \
	  --all --concurrency 5 --sleep 0.3

eval-full:  ## Merge L0 + L4 into 5-layer dataset (local, no API calls)
	cd $(EVAL_DIR) && python -c "\
	import json; \
	l0 = json.load(open('eval_10k_l0_l1l3.json')); \
	l4 = json.load(open('eval_10k_l1l4_full.json')); \
	L4 = 'gpt4o-pii-judge'; \
	l4_map = {r['id']: [lr for lr in r['layer_results'] if lr['layer']==L4][0] for r in l4['results'] if any(lr['layer']==L4 for lr in r['layer_results'])}; \
	[r['layer_results'].append(l4_map[r['id']]) for r in l0['results'] if r['id'] in l4_map and not any(lr['layer']==L4 for lr in r['layer_results'])]; \
	json.dump(l0, open('eval_10k_l0_l1l4_full.json','w'), ensure_ascii=False)"

aggregate:  ## Run 4-way summary
	cd $(EVAL_DIR) && python run_e_final_4way.py

figures:  ## Generate final PNGs
	cd $(EVAL_DIR) && python make_figures_final.py

analyze:  ## Run Phase 1 + Phase 3 analyses
	cd $(EVAL_DIR) && python ../../../phase3_ablation.py 2>/dev/null || cd $(PHASE3_DIR) && python phase3_ablation.py
	cd $(PHASE3_DIR) && python phase3_l4_smart_skip.py
	cd $(PHASE1_DIR) && python phase1_latency_precise.py
	cd $(PHASE1_DIR) && python phase1_mcnemar.py
	cd $(PHASE1_DIR) && python phase1_fp_test.py

all: setup deploy-l0 test sample eval-base eval-l0 eval-l4 eval-full aggregate figures analyze  ## Full pipeline (4+ hours, ~$5 in API costs)
	@echo "Pipeline complete. See $(SUM_DIR) and $(FIG_DIR)."

down:  ## Stop Docker stack
	docker compose -f PII/config/docker-compose.yml down

.PHONY: help setup deploy-l0 test sample eval-base eval-l0 eval-l4 eval-full aggregate figures analyze all down
