# Corpus Build Pipelines

This folder keeps data acquisition and corpus-build steps separate from the
runtime fuzzer modules.

## Subfolders
- `korean_names/`: Korean name source collection and tagged-corpus build pipeline.
- `korean_addresses/`: Korean public-address DB intake and future address-corpus build pipeline.

Runtime fuzzer code remains in `PII/fuzzer/` so imports used by the input and
output fuzzers stay stable.
