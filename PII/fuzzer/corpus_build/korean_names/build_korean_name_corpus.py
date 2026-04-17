import argparse
import sys
from pathlib import Path

FUZZER_DIR = Path(__file__).resolve().parents[2]
SOURCE_DIR = Path(__file__).resolve().parent / "raw"

if str(FUZZER_DIR) not in sys.path:
    sys.path.insert(0, str(FUZZER_DIR))

from name_corpus import (
    build_balanced_sample,
    build_tagged_name_records,
    load_given_names,
    load_surname_rows,
    summarize_records,
    write_jsonl,
    write_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build tagged Korean name corpus for stratified fuzzing."
    )
    parser.add_argument("--names-txt", default=SOURCE_DIR / "korean_names.txt")
    parser.add_argument("--surnames-csv", default=SOURCE_DIR / "korean_surnames.csv")
    parser.add_argument(
        "--output",
        default="PII/fuzzer/data/tagged_korean_names.jsonl",
        help="JSONL output path for full tagged corpus",
    )
    parser.add_argument(
        "--summary-out",
        default="PII/fuzzer/data/name_tag_summary.json",
        help="JSON output path for summary stats",
    )
    parser.add_argument(
        "--balanced-out",
        default="PII/fuzzer/data/balanced_name_samples.jsonl",
        help="JSONL output path for balanced sample",
    )
    parser.add_argument(
        "--sample-per-tier",
        type=int,
        default=500,
        help="Per-tier sample size for balanced output (<=0 disables)",
    )
    parser.add_argument(
        "--surname-mode",
        choices=["weighted", "uniform"],
        default="weighted",
        help="weighted uses surname count distribution from CSV",
    )
    parser.add_argument("--max-records", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    names_txt = Path(args.names_txt)
    surnames_csv = Path(args.surnames_csv)

    given_names = load_given_names(str(names_txt))
    surname_rows = load_surname_rows(str(surnames_csv))

    records = build_tagged_name_records(
        given_names=given_names,
        surname_rows=surname_rows,
        seed=args.seed,
        max_records=args.max_records,
        surname_mode=args.surname_mode,
    )

    write_jsonl(records, args.output)
    summary = summarize_records(records)
    write_summary(summary, args.summary_out)

    print(f"built tagged corpus: {len(records):,} records -> {args.output}")
    print(f"summary saved -> {args.summary_out}")

    if args.sample_per_tier > 0:
        balanced = build_balanced_sample(records, per_tier=args.sample_per_tier, seed=args.seed)
        write_jsonl(balanced, args.balanced_out)
        print(
            f"balanced sample saved: {len(balanced):,} records "
            f"({args.sample_per_tier} per tier cap) -> {args.balanced_out}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
