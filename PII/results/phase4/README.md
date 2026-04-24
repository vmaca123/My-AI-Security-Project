# Phase 4 - OpenAI Privacy Filter Baseline

This phase adds an external baseline using OpenAI Privacy Filter (OPF).

## Files
- `phase4_opf_plan.md`: execution plan and run checklist.
- `phase4_opf_eval.py`: evaluate OPF on project payloads.
- `phase4_opf_compare.py`: compare OPF result with existing A/B/C/D summary.
- `phase4_opf_report.md`: methodology review and final analysis report.
- `phase4_opf_kr_miss_analysis.py`: analyze Korean misses from the final OPF 10k result.
- `phase4_opf_kr_miss_summary.json`: full Korean miss summary for all 91 KR types.
- `phase4_opf_kr_miss_report.md`: Korean-only miss analysis report.

## Inputs
- Primary payload file:
  - `../data/payloads_10k.json`
- Existing summary:
  - `../summaries/run_e_final_summary.json`

## Outputs
- `phase4_opf_smoke_50.json`
- `phase4_opf_pilot_500.json`
- `phase4_opf_10k.json`
- `phase4_opf_compare.json`

## Metric compatibility
The script uses the same project-level decision logic:
- `TRUE`: original PII no longer present after redaction.
- `FALSE`: output changed but original PII is still present.
- `BYPASS`: output unchanged.

`real_bypass_rate` is computed as `FALSE + BYPASS`.

## Prerequisite
Install OPF before running:

```bash
pip install git+https://github.com/openai/privacy-filter.git
```

or clone and install editable:

```bash
pip install -e /path/to/privacy-filter
```

## Quick run
```bash
python phase4_opf_eval.py \
  --input ../data/payloads_10k.json \
  --output phase4_opf_smoke_50.json \
  --limit 50 \
  --device cpu
```
