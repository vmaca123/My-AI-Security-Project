"""Stratified sample 10,000 payloads from payloads_full.json.

Preserves lang x validity_group proportions and enforces corpus policy
for evaluation datasets.
"""

import json
import random
from collections import Counter, defaultdict

SEED = 20260419
TARGET = 10000
random.seed(SEED)


def fail(message):
    raise SystemExit(f"[ERROR] {message}")


with open("payloads_full.json", "r", encoding="utf-8") as f:
    src = json.load(f)

all_payloads = src.get("payloads", [])
source_meta = src.get("metadata", {})
source_stats = src.get("stats", {})

name_source = str(source_meta.get("name_corpus_source", ""))
address_source = str(source_meta.get("address_corpus_source", ""))
name_corpus = int(source_meta.get("name_corpus", 0) or 0)
address_corpus = int(source_meta.get("address_corpus", 0) or 0)
by_address_tier = source_stats.get("by_address_tier", {}) if isinstance(source_stats, dict) else {}

if name_source == "legacy_embedded":
    fail("name_corpus_source is legacy_embedded. evaluation requires tagged corpus.")
if address_source == "legacy_generator":
    fail("address_corpus_source is legacy_generator. evaluation requires tagged corpus.")
if name_corpus <= 0:
    fail("name_corpus must be > 0 for evaluation.")
if address_corpus <= 0:
    fail("address_corpus must be > 0 for evaluation.")
if not isinstance(by_address_tier, dict) or not by_address_tier:
    fail("stats.by_address_tier is empty. evaluation requires address tier coverage.")

N = len(all_payloads)
print(f"source: {N} payloads, target: {TARGET}")

# Stratify by lang + validity_group (3 levels coarse enough)
buckets = defaultdict(list)
for payload in all_payloads:
    key = (payload.get("lang", "?"), payload.get("validity_group", "?"))
    buckets[key].append(payload)

print("source distribution:")
for key, values in sorted(buckets.items()):
    print(f"  {key}: {len(values)}")

# Allocate proportionally
allocated = {}
remaining = TARGET
keys = list(buckets.keys())
for idx, key in enumerate(keys):
    if idx == len(keys) - 1:
        allocated[key] = remaining
    else:
        sample_size = round(TARGET * len(buckets[key]) / N)
        allocated[key] = min(sample_size, len(buckets[key]))
        remaining -= allocated[key]

print("\nallocated:")
for key, sample_size in sorted(allocated.items()):
    print(f"  {key}: {sample_size}")

sampled = []
for key, sample_size in allocated.items():
    random.shuffle(buckets[key])
    sampled.extend(buckets[key][:sample_size])

random.shuffle(sampled)
print(f"\nfinal: {len(sampled)}")

# Verify distribution
print("\nresulting distribution:")
print("  lang:", dict(Counter(payload["lang"] for payload in sampled)))
print("  validity_group:", dict(Counter(payload["validity_group"] for payload in sampled)))
print("  mutation_level:", dict(Counter(payload["mutation_level"] for payload in sampled)))

output_meta = dict(source_meta) if isinstance(source_meta, dict) else {}
output_meta.update(
    {
        "source": output_meta.get("source", "payloads_full.json"),
        "stratified": "lang x validity_group",
        "seed": SEED,
        "count": len(sampled),
        "sampled_from_total": N,
    }
)

with open("payloads_10k.json", "w", encoding="utf-8") as f:
    json.dump({"metadata": output_meta, "payloads": sampled}, f, ensure_ascii=False)

print("\nsaved: payloads_10k.json")
