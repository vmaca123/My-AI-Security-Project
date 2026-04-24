"""
Analyze Korean OPF misses from phase4_opf_10k.json.

Output:
{
  "overview": {...},
  "by_validity": {...},
  "by_mutation_level": {...},
  "top_mutations": {...},
  "false_label_counts": {...},
  "by_type": [...]
}
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def load_results(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        doc = json.load(f)
    return list(doc["results"])


def classify_rows(rows: list[dict[str, Any]], *, lang: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    target = [row for row in rows if row.get("lang") == lang]
    miss = [row for row in target if row.get("classification") != "TRUE"]
    return target, miss


def summarize_classes(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(row.get("classification", "") for row in rows)
    return {
        "TRUE": counts.get("TRUE", 0),
        "FALSE": counts.get("FALSE", 0),
        "BYPASS": counts.get("BYPASS", 0),
    }


def mutation_table(rows: list[dict[str, Any]], limit: int = 30) -> list[dict[str, Any]]:
    counts = Counter(row.get("mutation_name", "") for row in rows)
    return [{"mutation_name": key, "count": value} for key, value in counts.most_common(limit)]


def validity_table(rows: list[dict[str, Any]]) -> dict[str, Any]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(row.get("validity_group", ""))].append(row)

    out: dict[str, Any] = {}
    for validity, grouped in sorted(buckets.items(), key=lambda kv: kv[0]):
        counts = summarize_classes(grouped)
        total = len(grouped)
        miss = counts["FALSE"] + counts["BYPASS"]
        out[validity] = {
            "n": total,
            **counts,
            "miss_rate": round(100 * miss / total, 2) if total else 0.0,
        }
    return out


def mutation_level_table(rows: list[dict[str, Any]]) -> dict[str, Any]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(row.get("mutation_level", ""))].append(row)

    out: dict[str, Any] = {}
    for level, grouped in sorted(buckets.items(), key=lambda kv: kv[0]):
        counts = summarize_classes(grouped)
        total = len(grouped)
        miss = counts["FALSE"] + counts["BYPASS"]
        out[level] = {
            "n": total,
            **counts,
            "miss_rate": round(100 * miss / total, 2) if total else 0.0,
        }
    return out


def false_label_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    labels = Counter()
    for row in rows:
        if row.get("classification") != "FALSE":
            continue
        for span in row.get("detected_spans", []):
            labels[span.get("label", "")] += 1
    return dict(labels.most_common())


def by_type_table(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(row.get("pii_type", ""))].append(row)

    out: list[dict[str, Any]] = []
    for pii_type, grouped in buckets.items():
        counts = summarize_classes(grouped)
        total = len(grouped)
        miss = counts["FALSE"] + counts["BYPASS"]
        out.append(
            {
                "pii_type": pii_type,
                "n": total,
                **counts,
                "miss": miss,
                "true_rate": round(100 * counts["TRUE"] / total, 2) if total else 0.0,
                "miss_rate": round(100 * miss / total, 2) if total else 0.0,
            }
        )
    out.sort(key=lambda row: (-row["miss_rate"], -row["miss"], row["pii_type"]))
    return out


def example_rows(rows: list[dict[str, Any]], wanted: list[str]) -> list[dict[str, Any]]:
    chosen = []
    seen = set()
    for row in rows:
        pii_type = row.get("pii_type")
        if pii_type in wanted and pii_type not in seen:
            chosen.append(
                {
                    "pii_type": pii_type,
                    "classification": row.get("classification"),
                    "mutation_name": row.get("mutation_name"),
                    "mutated": row.get("mutated"),
                    "redacted_text": row.get("redacted_text"),
                    "detected_spans": row.get("detected_spans", [])[:3],
                }
            )
            seen.add(pii_type)
    return chosen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Korean OPF misses.")
    parser.add_argument("--input", required=True, help="phase4_opf_10k.json path")
    parser.add_argument("--output", required=True, help="summary json output path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    rows = load_results(input_path)
    kr_rows, kr_miss = classify_rows(rows, lang="KR")

    by_type = by_type_table(kr_rows)
    false_rows = [row for row in kr_miss if row.get("classification") == "FALSE"]
    bypass_rows = [row for row in kr_miss if row.get("classification") == "BYPASS"]

    summary = {
        "source_file": str(input_path),
        "overview": {
            "kr_total": len(kr_rows),
            "kr_miss": len(kr_miss),
            "kr_miss_rate": round(100 * len(kr_miss) / len(kr_rows), 2) if kr_rows else 0.0,
            "miss_classes": summarize_classes(kr_miss),
            "unique_kr_types": len(by_type),
        },
        "by_validity": validity_table(kr_miss),
        "by_mutation_level": mutation_level_table(kr_miss),
        "top_mutations": {
            "overall": mutation_table(kr_miss, 40),
            "false_only": mutation_table(false_rows, 30),
            "bypass_only": mutation_table(bypass_rows, 30),
        },
        "false_label_counts": false_label_counts(kr_miss),
        "top_types_by_miss_count": by_type[:40],
        "all_types": by_type,
        "examples": example_rows(
            kr_miss,
            [
                "marital",
                "school",
                "mental",
                "orientation",
                "allergy",
                "disability",
                "job_title",
                "prescription",
                "blood",
                "degree",
                "surgery",
                "religion",
                "diagnosis",
                "family",
                "ssh",
                "dob",
                "aws_key",
            ],
        ),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()

