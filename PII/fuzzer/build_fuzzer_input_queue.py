import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List


def _load_records(path: Path) -> List[Dict[str, object]]:
    if path.suffix.lower() == ".jsonl":
        records: List[Dict[str, object]] = []
        with path.open("r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                if isinstance(data, dict):
                    records.append(data)
        return records

    with path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)

    if isinstance(data, dict) and isinstance(data.get("payloads"), list):
        return [item for item in data["payloads"] if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    raise ValueError(f"Unsupported manifest format: {path}")


def _iter_queue_records(
    records: Iterable[Dict[str, object]],
    id_field: str,
    text_field: str,
    strict: bool,
) -> Iterable[Dict[str, str]]:
    for row in records:
        rid = str(row.get(id_field, "")).strip()
        text = str(row.get(text_field, "")).strip()
        if not rid or not text:
            if strict:
                raise ValueError(
                    f"Missing required fields: id_field='{id_field}', text_field='{text_field}', row={row}"
                )
            continue
        yield {"id": rid, "text": text}


def _split_part_path(output: Path, index: int) -> Path:
    if index <= 1:
        return output
    return output.with_name(f"{output.stem}_part{index:03d}{output.suffix}")


def _cleanup_split_parts(output: Path) -> None:
    for part_path in output.parent.glob(f"{output.stem}_part*{output.suffix}"):
        if part_path.is_file():
            part_path.unlink()


def _write_jsonl_split(records: List[Dict[str, str]], output: Path, max_bytes: int) -> List[Path]:
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


def _write_output(records: List[Dict[str, str]], output: Path, max_file_mb: float) -> List[Path]:
    output.parent.mkdir(parents=True, exist_ok=True)
    _cleanup_split_parts(output)

    if output.suffix.lower() == ".json":
        with output.open("w", encoding="utf-8") as fp:
            json.dump(records, fp, ensure_ascii=False, indent=2)
        return [output]

    max_bytes = int(max_file_mb * 1024 * 1024) if max_file_mb > 0 else 0
    if max_bytes <= 0:
        with output.open("w", encoding="utf-8") as fp:
            for row in records:
                fp.write(json.dumps(row, ensure_ascii=False) + "\n")
        return [output]

    return _write_jsonl_split(records, output=output, max_bytes=max_bytes)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build queue input file from fuzzer payload manifest. Queue records contain only id + text."
    )
    parser.add_argument("--manifest", required=True, help="Fuzzer payload file (.json or .jsonl)")
    parser.add_argument(
        "--output",
        default="PII/fuzzer/data/input_queue.jsonl",
        help="Output queue file (.jsonl recommended, .json supported)",
    )
    parser.add_argument("--id-field", default="id", help="ID field in manifest records")
    parser.add_argument("--text-field", default="mutated", help="Input text field in manifest records")
    parser.add_argument("--limit", type=int, default=0, help="Max records (<=0 means all)")
    parser.add_argument(
        "--max-file-mb",
        type=float,
        default=45.0,
        help="Max size per output file in MiB for JSONL output (<=0 disables split)",
    )
    parser.add_argument("--strict", action="store_true", help="Fail on missing required fields")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest)
    output_path = Path(args.output)

    manifest_records = _load_records(manifest_path)
    queue_records = list(
        _iter_queue_records(
            records=manifest_records,
            id_field=args.id_field,
            text_field=args.text_field,
            strict=args.strict,
        )
    )

    if args.limit > 0:
        queue_records = queue_records[: args.limit]

    output_files = _write_output(queue_records, output_path, max_file_mb=args.max_file_mb)

    print(f"manifest records: {len(manifest_records):,}")
    print(f"queue records: {len(queue_records):,}")
    if len(output_files) == 1:
        print(f"saved queue -> {output_files[0]}")
    else:
        print(f"saved queue -> {len(output_files)} files (max {args.max_file_mb} MiB each)")
        for path in output_files:
            print(f"  - {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
