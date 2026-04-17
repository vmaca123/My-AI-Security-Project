# Korean Name Corpus Build

This folder contains the Korean-name acquisition and corpus-build pipeline.

## Files
- `fetch_koreanname_names.py`: downloads public given-name data from koreanname.me.
- `fetch_korean_surnames.py`: downloads public surname ranking data from koreanname.me.
- `raw/korean_names.txt`: collected given-name source data.
- `raw/korean_surnames.csv`: collected surname source data with rank/count metadata.
- `raw/korean_surnames.txt`: collected surname source data as plain text.
- `build_korean_name_corpus.py`: builds tagged/balanced/expanded name corpora and versioned name seed queue.

## Build
Run from the repository root:

```powershell
python PII/fuzzer/corpus_build/korean_names/build_korean_name_corpus.py
```

The generated fuzzer-ready files are written under `PII/fuzzer/data/` by default.

Default outputs:

- `PII/fuzzer/data/tagged_korean_names.jsonl`
- `PII/fuzzer/data/name_tag_summary.json`
- `PII/fuzzer/data/balanced_name_samples.jsonl`
- `PII/fuzzer/data/expanded_name_mutation_samples.jsonl`
- `PII/fuzzer/seeds/name/name_input_queue_202604_v1.jsonl`
