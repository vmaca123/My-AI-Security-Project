#!/usr/bin/env python3
"""Fetch public Korean birth-name rankings from koreanname.me.

This script uses koreanname.me's public ranking endpoint, not the government
source site. Keep the delay enabled and check the site's current terms before
bulk use.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://koreanname.me"
DEFAULT_USER_AGENT = (
    "korean-name-research/1.0 "
    "(low-rate public aggregate-data fetch; contact: replace-with-your-email)"
)


def fetch_json(url: str, user_agent: str, timeout: float) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": user_agent})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
    return json.loads(raw.decode("utf-8"))


def fetch_total_count(start_year: int, end_year: int, user_agent: str, timeout: float) -> int | None:
    data = fetch_json(
        f"{BASE_URL}/api/rank/{start_year}/{end_year}/1",
        user_agent=user_agent,
        timeout=timeout,
    )
    total_count = data.get("totalCount")
    return int(total_count) if total_count is not None else None


def iter_rank_pages(
    start_year: int,
    end_year: int,
    delay: float,
    user_agent: str,
    timeout: float,
    max_pages: int | None,
    strategy: str,
):
    page = 1
    requests_sent = 0
    while True:
        url = f"{BASE_URL}/api/rank/{start_year}/{end_year}/{page}"
        data = fetch_json(url, user_agent=user_agent, timeout=timeout)
        requests_sent += 1
        yield page, data

        if not data.get("male") and not data.get("female"):
            break
        if not data.get("maleHasNext") and not data.get("femaleHasNext"):
            break
        if max_pages is not None and requests_sent >= max_pages:
            break

        page = page + 1 if strategy == "sequential" else page * 2
        time.sleep(delay)


def iter_length_pages(
    name_length: int,
    delay: float,
    user_agent: str,
    timeout: float,
    max_pages: int | None,
    strategy: str,
):
    page = 1
    requests_sent = 0
    while True:
        url = f"{BASE_URL}/api/length/{name_length}/{page}"
        data = fetch_json(url, user_agent=user_agent, timeout=timeout)
        requests_sent += 1
        yield page, data

        if not data.get("lengthList"):
            break
        if not data.get("hasNext"):
            break
        if max_pages is not None and requests_sent >= max_pages:
            break

        page = page + 1 if strategy == "sequential" else page * 2
        time.sleep(delay)


def collect_names(
    start_year: int,
    end_year: int,
    delay: float,
    user_agent: str,
    timeout: float,
    max_pages: int | None,
    strategy: str,
) -> tuple[set[str], list[dict[str, Any]]]:
    names: set[str] = set()
    rows: list[dict[str, Any]] = []
    row_keys: set[tuple[str, str]] = set()

    for page, data in iter_rank_pages(start_year, end_year, delay, user_agent, timeout, max_pages, strategy):
        print(
            f"page={page} male={len(data.get('male', []))} "
            f"female={len(data.get('female', []))} total={data.get('totalCount')}"
        )
        new_rows = 0
        for gender, key in (("male", "male"), ("female", "female")):
            for item in data.get(key, []):
                name = item["name"].strip()
                if not name:
                    continue
                names.add(name)
                row_key = (gender, name)
                if row_key in row_keys:
                    continue
                row_keys.add(row_key)
                new_rows += 1
                rows.append(
                    {
                        "name": name,
                        "gender": gender,
                        "rank": item.get("rank"),
                        "count": item.get("count"),
                        "start_year": start_year,
                        "end_year": end_year,
                    }
                )
        if new_rows == 0:
            break

    return names, rows


def collect_names_by_length(
    max_name_length: int,
    stop_after_empty_lengths: int,
    delay: float,
    user_agent: str,
    timeout: float,
    max_pages: int | None,
    strategy: str,
) -> tuple[set[str], list[dict[str, Any]]]:
    names: set[str] = set()
    rows: list[dict[str, Any]] = []
    empty_lengths = 0

    for name_length in range(1, max_name_length + 1):
        length_items = 0
        length_new_rows = 0
        for page, data in iter_length_pages(name_length, delay, user_agent, timeout, max_pages, strategy):
            items = data.get("lengthList", [])
            length_items += len(items)
            new_rows = 0
            for item in items:
                name = item["name"].strip()
                if not name or name in names:
                    continue
                names.add(name)
                new_rows += 1
                length_new_rows += 1
                rows.append(
                    {
                        "name": name,
                        "gender": "",
                        "rank": item.get("rank"),
                        "count": item.get("count"),
                        "name_length": name_length,
                        "start_year": 2008,
                        "end_year": date.today().year,
                    }
                )

            print(
                f"length={name_length} page={page} items={len(items)} "
                f"new={new_rows} hasNext={data.get('hasNext')}"
            )

            if not items or new_rows == 0:
                break

        if length_items == 0:
            empty_lengths += 1
            if empty_lengths >= stop_after_empty_lengths:
                print(f"stopping after {empty_lengths} consecutive empty name lengths")
                break
        else:
            empty_lengths = 0

    return names, rows


def write_outputs(names: set[str], rows: list[dict[str, Any]], names_path: Path, csv_path: Path | None) -> None:
    names_path.parent.mkdir(parents=True, exist_ok=True)
    names_path.write_text("\n".join(sorted(names)) + "\n", encoding="utf-8")

    if csv_path is not None:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["name", "gender", "rank", "count", "name_length", "start_year", "end_year"],
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download public koreanname.me ranking names with conservative rate limiting."
    )
    parser.add_argument("--start-year", type=int, default=2008)
    parser.add_argument("--end-year", type=int, default=date.today().year)
    parser.add_argument(
        "--source",
        choices=["length", "rank"],
        default="length",
        help="length is fastest and exact for all-site unique names; rank supports year ranges.",
    )
    parser.add_argument(
        "--strategy",
        choices=["exponential", "sequential"],
        default="exponential",
        help="exponential uses pages 1,2,4,8... to avoid overlapping API ranges.",
    )
    parser.add_argument("--delay", type=float, default=0.5, help="Seconds to wait between page requests.")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--max-pages", type=int, default=None, help="Optional request-count safety cap for testing.")
    parser.add_argument("--max-name-length", type=int, default=40)
    parser.add_argument("--stop-after-empty-lengths", type=int, default=3)
    parser.add_argument("--names-out", type=Path, default=Path("korean_names.txt"))
    parser.add_argument("--csv-out", type=Path, default=None, help="Optional metadata CSV output path.")
    parser.add_argument("--no-verify-total", dest="verify_total", action="store_false")
    parser.add_argument("--strict-total", action="store_true", help="Exit non-zero if verification count differs.")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.set_defaults(verify_total=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.start_year < 2008:
        raise SystemExit("koreanname.me states that data exists only for births from 2008 onward.")
    if args.end_year < args.start_year:
        raise SystemExit("--end-year must be greater than or equal to --start-year.")
    if args.delay < 0.2:
        raise SystemExit("--delay below 0.2s is intentionally blocked. Use a conservative request rate.")
    if args.max_name_length <= 0:
        raise SystemExit("--max-name-length must be positive.")
    if args.stop_after_empty_lengths <= 0:
        raise SystemExit("--stop-after-empty-lengths must be positive.")
    if args.source == "length" and (args.start_year != 2008 or args.end_year != date.today().year):
        raise SystemExit(
            "--source length enumerates koreanname.me's all-site unique names and cannot apply year filters. "
            "Use --source rank for a custom year range."
        )

    try:
        if args.source == "length":
            names, rows = collect_names_by_length(
                max_name_length=args.max_name_length,
                stop_after_empty_lengths=args.stop_after_empty_lengths,
                delay=args.delay,
                user_agent=args.user_agent,
                timeout=args.timeout,
                max_pages=args.max_pages,
                strategy=args.strategy,
            )
        else:
            names, rows = collect_names(
                start_year=args.start_year,
                end_year=args.end_year,
                delay=args.delay,
                user_agent=args.user_agent,
                timeout=args.timeout,
                max_pages=args.max_pages,
                strategy=args.strategy,
            )
    except (HTTPError, URLError, TimeoutError) as exc:
        raise SystemExit(f"Request failed: {exc}") from exc

    write_outputs(names, rows, args.names_out, args.csv_out)
    print(f"wrote {len(names)} unique names to {args.names_out}")
    if args.csv_out:
        print(f"wrote {len(rows)} ranking rows to {args.csv_out}")
    if args.verify_total:
        total_count = fetch_total_count(args.start_year, args.end_year, args.user_agent, args.timeout)
        if total_count is not None and total_count != len(names):
            message = f"verification mismatch: site totalCount={total_count}, collected={len(names)}"
            if args.strict_total:
                raise SystemExit(message)
            print(f"WARNING: {message}")
        elif total_count is not None:
            print(f"verified totalCount={total_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
