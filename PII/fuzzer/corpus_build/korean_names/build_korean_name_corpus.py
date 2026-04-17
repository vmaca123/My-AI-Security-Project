import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List

FUZZER_DIR = Path(__file__).resolve().parents[2]
SOURCE_DIR = Path(__file__).resolve().parent / "raw"

if str(FUZZER_DIR) not in sys.path:
    sys.path.insert(0, str(FUZZER_DIR))

from name_corpus import (
    build_expanded_name_mutation_records,
    build_balanced_sample,
    build_tagged_name_records,
    load_given_names,
    load_surname_rows,
    summarize_records,
    write_jsonl,
    write_summary,
)


def _split_part_path(output_path: Path, index: int) -> Path:
    if index <= 1:
        return output_path
    return output_path.with_name(f"{output_path.stem}_part{index:03d}{output_path.suffix}")


def _cleanup_split_parts(output_path: Path) -> None:
    for part_path in output_path.parent.glob(f"{output_path.stem}_part*{output_path.suffix}"):
        if part_path.is_file():
            part_path.unlink()


def write_jsonl_with_split(records: Iterable[Dict[str, object]], output_path: str, max_bytes: int = 0) -> List[Path]:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    _cleanup_split_parts(output)

    if max_bytes <= 0:
        write_jsonl(records, str(output))
        return [output]

    written_files: List[Path] = []
    part_index = 1
    current_path = _split_part_path(output, part_index)
    current_size = 0
    current_fp = current_path.open("w", encoding="utf-8")
    written_files.append(current_path)

    try:
        for row in records:
            line = json.dumps(row, ensure_ascii=False) + "\n"
            line_size = len(line.encode("utf-8"))
            if current_size > 0 and current_size + line_size > max_bytes:
                current_fp.close()
                part_index += 1
                current_path = _split_part_path(output, part_index)
                current_fp = current_path.open("w", encoding="utf-8")
                written_files.append(current_path)
                current_size = 0
            current_fp.write(line)
            current_size += line_size
    finally:
        current_fp.close()

    return written_files


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
        "--expanded-out",
        default="PII/fuzzer/data/expanded_name_mutation_samples.jsonl",
        help="JSONL output path for mutation-expanded name samples",
    )
    parser.add_argument(
        "--name-seed-out",
        default="PII/fuzzer/seeds/name/name_input_queue_202604_v1.jsonl",
        help="JSONL output path for versioned name seed queue (id + text)",
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
    parser.add_argument(
        "--expanded-per-record",
        type=int,
        default=12,
        help="Max number of expanded mutation entries per base record (<=0 means all)",
    )
    parser.add_argument(
        "--name-seed-max-file-mb",
        type=float,
        default=45.0,
        help="Max size per name seed output file in MiB (<=0 disables split)",
    )
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

    expanded = build_expanded_name_mutation_records(
        records,
        per_record=args.expanded_per_record,
        seed=args.seed,
    )
    write_jsonl(expanded, args.expanded_out)
    print(
        f"expanded mutation samples saved: {len(expanded):,} records "
        f"(per-record cap: {args.expanded_per_record}) -> {args.expanded_out}"
    )

    seed_queue = []
    for row in expanded:
        seed_queue.append(
            {
                "id": row.get("id", ""),
                "text": row.get("mutated_name", ""),
                "name_id": row.get("name_id", ""),
                "name_tier": row.get("name_tier", ""),
                "name_tags": row.get("name_tags", []),
                "original_name": row.get("original_name", ""),
                "mutated_name": row.get("mutated_name", ""),
                "mutation_name": row.get("mutation_name", ""),
                "mutation_tags": row.get("mutation_tags", []),
                "expected_action": row.get("expected_action", "mask"),
                "synthetic": True,
            }
        )
    seed_max_bytes = int(args.name_seed_max_file_mb * 1024 * 1024) if args.name_seed_max_file_mb > 0 else 0
    seed_files = write_jsonl_with_split(seed_queue, args.name_seed_out, max_bytes=seed_max_bytes)
    if len(seed_files) == 1:
        print(f"name seed queue saved: {len(seed_queue):,} records -> {seed_files[0]}")
    else:
        print(
            f"name seed queue saved: {len(seed_queue):,} records "
            f"-> {len(seed_files)} files (max {args.name_seed_max_file_mb} MiB each)"
        )
        for path in seed_files:
            print(f"  - {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
