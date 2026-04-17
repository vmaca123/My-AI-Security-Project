import argparse
import sys
from pathlib import Path

FUZZER_DIR = Path(__file__).resolve().parents[2]
SOURCE_DIR = Path(__file__).resolve().parent / "raw"

if str(FUZZER_DIR) not in sys.path:
    sys.path.insert(0, str(FUZZER_DIR))

from address_corpus import (
    build_balanced_address_sample,
    build_expanded_address_mutation_records,
    build_tagged_address_records,
    load_tagged_address_records,
    summarize_address_records,
    write_jsonl,
    write_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build tagged Korean address corpus and mutation-expanded payload seeds."
    )
    parser.add_argument("--raw-dir", default=SOURCE_DIR, help="Directory that contains raw address zip files")
    parser.add_argument(
        "--input-tagged",
        default="",
        help="Optional tagged address JSONL input. If set, skip raw ZIP parsing and reuse this tagged corpus.",
    )
    parser.add_argument(
        "--output",
        default="PII/fuzzer/data/tagged_korean_addresses.jsonl",
        help="JSONL output path for full tagged address corpus",
    )
    parser.add_argument(
        "--summary-out",
        default="PII/fuzzer/data/address_tag_summary.json",
        help="JSON output path for address summary stats",
    )
    parser.add_argument(
        "--balanced-out",
        default="PII/fuzzer/data/balanced_address_samples.jsonl",
        help="JSONL output path for balanced address sample",
    )
    parser.add_argument(
        "--expanded-out",
        default="PII/fuzzer/data/expanded_address_mutation_samples.jsonl",
        help="JSONL output path for mutation-expanded address samples",
    )
    parser.add_argument(
        "--sample-per-tier",
        type=int,
        default=500,
        help="Per-tier sample size for balanced output (<=0 disables)",
    )
    parser.add_argument(
        "--max-base-records",
        type=int,
        default=50000,
        help="Maximum number of base tagged address records to keep",
    )
    parser.add_argument(
        "--expanded-per-record",
        type=int,
        default=12,
        help="Max number of expanded mutation entries per base record (<=0 means all)",
    )
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.input_tagged:
        base_records = load_tagged_address_records(args.input_tagged)
        if args.max_base_records > 0:
            base_records = base_records[: args.max_base_records]
        print(f"loaded tagged address corpus: {len(base_records):,} records <- {args.input_tagged}")
    else:
        base_records = build_tagged_address_records(
            raw_dir=str(Path(args.raw_dir)),
            seed=args.seed,
            max_records=args.max_base_records,
        )
    write_jsonl(base_records, args.output)

    summary = summarize_address_records(base_records)
    write_summary(summary, args.summary_out)

    print(f"built tagged address corpus: {len(base_records):,} records -> {args.output}")
    print(f"summary saved -> {args.summary_out}")

    if args.sample_per_tier > 0:
        balanced = build_balanced_address_sample(
            base_records,
            per_tier=args.sample_per_tier,
            seed=args.seed,
        )
        write_jsonl(balanced, args.balanced_out)
        print(
            f"balanced sample saved: {len(balanced):,} records "
            f"({args.sample_per_tier} per tier cap) -> {args.balanced_out}"
        )

    expanded = build_expanded_address_mutation_records(
        base_records,
        per_record=args.expanded_per_record,
        seed=args.seed,
    )
    write_jsonl(expanded, args.expanded_out)
    print(
        f"expanded mutation samples saved: {len(expanded):,} records "
        f"(per-record cap: {args.expanded_per_record}) -> {args.expanded_out}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
