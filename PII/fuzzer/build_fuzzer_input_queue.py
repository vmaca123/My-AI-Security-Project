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


def _write_output(records: List[Dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() == ".json":
        with output.open("w", encoding="utf-8") as fp:
            json.dump(records, fp, ensure_ascii=False, indent=2)
        return

    with output.open("w", encoding="utf-8") as fp:
        for row in records:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")


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

    _write_output(queue_records, output_path)

    print(f"manifest records: {len(manifest_records):,}")
    print(f"queue records: {len(queue_records):,}")
    print(f"saved queue -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
