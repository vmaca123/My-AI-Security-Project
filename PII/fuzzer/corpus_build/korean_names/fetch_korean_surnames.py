#!/usr/bin/env python3
"""Fetch public Korean surname rankings from koreanname.me."""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://koreanname.me"
SOURCE_DIR = Path(__file__).resolve().parent / "raw"
DEFAULT_USER_AGENT = (
    "korean-surname-research/1.0 "
    "(low-rate public aggregate-data fetch; contact: replace-with-your-email)"
)


def fetch_json(url: str, user_agent: str, timeout: float) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": user_agent})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
    return json.loads(raw.decode("utf-8"))


def collect_surnames(year: int, delay: float, user_agent: str, timeout: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    page = 1

    while True:
        data = fetch_json(
            f"{BASE_URL}/api/surname/rank/{year}/{year}/{page}",
            user_agent=user_agent,
            timeout=timeout,
        )
        items = data.get("surnames", [])
        new_rows = 0

        for item in items:
            surname = item["surname"].strip()
            if not surname or surname in seen:
                continue
            seen.add(surname)
            new_rows += 1
            rows.append(
                {
                    "surname": surname,
                    "rank": item.get("rank"),
                    "count": item.get("count"),
                    "percent": item.get("percent"),
                    "year": year,
                }
            )

        print(
            f"year={year} page={page} items={len(items)} "
            f"new={new_rows} hasNext={data.get('hasNext')} reported_count={data.get('count')}"
        )

        if not items or not data.get("hasNext") or new_rows == 0:
            break

        page += 1
        time.sleep(delay)

    rows.sort(key=lambda row: (row["rank"] is None, row["rank"] or 0, row["surname"]))
    return rows


def write_outputs(rows: list[dict[str, Any]], txt_out: Path, csv_out: Path | None) -> None:
    txt_out.parent.mkdir(parents=True, exist_ok=True)
    txt_out.write_text("\n".join(row["surname"] for row in rows) + "\n", encoding="utf-8")

    if csv_out is not None:
        csv_out.parent.mkdir(parents=True, exist_ok=True)
        with csv_out.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["surname", "rank", "count", "percent", "year"])
            writer.writeheader()
            writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download public koreanname.me surname rankings.")
    parser.add_argument("--year", type=int, default=2015, help="Surname ranking year used by koreanname.me.")
    parser.add_argument("--delay", type=float, default=0.5, help="Seconds to wait between page requests.")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--txt-out", type=Path, default=SOURCE_DIR / "korean_surnames.txt")
    parser.add_argument("--csv-out", type=Path, default=SOURCE_DIR / "korean_surnames.csv")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.delay < 0.2:
        raise SystemExit("--delay below 0.2s is intentionally blocked. Use a conservative request rate.")

    try:
        rows = collect_surnames(
            year=args.year,
            delay=args.delay,
            user_agent=args.user_agent,
            timeout=args.timeout,
        )
    except (HTTPError, URLError, TimeoutError) as exc:
        raise SystemExit(f"Request failed: {exc}") from exc

    write_outputs(rows, args.txt_out, args.csv_out)
    print(f"wrote {len(rows)} surnames to {args.txt_out}")
    if args.csv_out is not None:
        print(f"wrote {len(rows)} ranking rows to {args.csv_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
