# Layer 0 Unit Tests

Pytest-based test suite for the Korean PII Normalizer + Detector.

## Running

```bash
cd PII/layer_0
pip install pytest
pytest tests/ -v
```

Or from repo root:

```bash
pytest PII/layer_0/tests/ -v
```

## Coverage

| Test file | Cases | Coverage |
|---|---:|---|
| `test_detector.py` | 50+ | All 42 regex + 22 keyword dict types, FP guards, API shape |
| `test_normalizer.py` | 10+ | ZWSP/soft-hyphen strip, fullwidth, homoglyph, jamo, determinism, latency |

## CI

`.github/workflows/layer_0_tests.yml` runs the suite on every push to `main`
and every PR. See workflow file for Python version matrix.

## Regression guard

If any test fails, do NOT merge. Common failure modes:

1. **FP regression**: a detector pattern is too greedy → triggers on clean text
2. **Short-keyword without context**: 2-char keywords must require context
3. **Normalizer non-determinism**: randomness introduced (should never happen)
4. **Latency regression**: normalization exceeds 500ms on typical input
