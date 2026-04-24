"""
Phase 4: compare OPF results with existing A/B/C/D summary.

Inputs:
  - Existing summary: run_e_final_summary.json
  - OPF result file from phase4_opf_eval.py

Output:
  - One JSON comparison artifact.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _get_opf_overall(opf_doc: dict[str, Any]) -> dict[str, Any]:
    summary = opf_doc.get("summary", {})
    overall = summary.get("overall", {})
    required = {"n", "TRUE", "FALSE", "BYPASS", "true_rate", "real_bypass_rate"}
    if not required.issubset(overall.keys()):
        missing = sorted(required.difference(overall.keys()))
        raise ValueError(f"OPF overall is missing required keys: {missing}")
    return overall


def _safe_slice(summary: dict[str, Any], key: str) -> dict[str, Any]:
    value = summary.get(key)
    return value if isinstance(value, dict) else {}


def build_comparison(
    baseline: dict[str, Any],
    opf: dict[str, Any],
    *,
    baseline_file: str,
    opf_file: str,
) -> dict[str, Any]:
    baseline_overall = baseline.get("overall", {})
    opf_summary = opf.get("summary", {})
    opf_overall = _get_opf_overall(opf)

    merged_overall = {
        "A_Baseline": baseline_overall.get("A_Baseline", {}),
        "B_Baseline_L4": baseline_overall.get("B_Baseline_L4", {}),
        "C_With_L0": baseline_overall.get("C_With_L0", {}),
        "D_Full": baseline_overall.get("D_Full", {}),
        "E_OPF_Solo": opf_overall,
    }

    def true_rate(config: str) -> float:
        return float(merged_overall.get(config, {}).get("true_rate", 0.0))

    def bypass_rate(config: str) -> float:
        return float(merged_overall.get(config, {}).get("real_bypass_rate", 0.0))

    return {
        "run": "phase4_opf_compare",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_files": {
            "baseline_summary": baseline_file,
            "opf_result": opf_file,
        },
        "overall": merged_overall,
        "head_to_head": {
            "E_minus_B_true_rate_pp": round(true_rate("E_OPF_Solo") - true_rate("B_Baseline_L4"), 2),
            "E_minus_C_true_rate_pp": round(true_rate("E_OPF_Solo") - true_rate("C_With_L0"), 2),
            "E_minus_D_true_rate_pp": round(true_rate("E_OPF_Solo") - true_rate("D_Full"), 2),
            "E_minus_B_bypass_pp": round(
                bypass_rate("E_OPF_Solo") - bypass_rate("B_Baseline_L4"), 2
            ),
            "E_minus_C_bypass_pp": round(
                bypass_rate("E_OPF_Solo") - bypass_rate("C_With_L0"), 2
            ),
            "E_minus_D_bypass_pp": round(
                bypass_rate("E_OPF_Solo") - bypass_rate("D_Full"), 2
            ),
        },
        "opf_slices": {
            "by_lang": _safe_slice(opf_summary, "by_lang"),
            "by_validity": _safe_slice(opf_summary, "by_validity"),
            "by_lang_x_validity": _safe_slice(opf_summary, "by_lang_x_validity"),
            "by_mutation_level": _safe_slice(opf_summary, "by_mutation_level"),
            "hardest_pii": opf_summary.get("hardest_pii", []),
            "latency": opf_summary.get("latency", {}),
            "errors": opf_summary.get("errors", {}),
        },
    }


def print_table(comparison: dict[str, Any]) -> None:
    overall = comparison["overall"]
    ordered = [
        ("A_Baseline", "L1+L2+L3"),
        ("B_Baseline_L4", "L1+L2+L3+L4"),
        ("C_With_L0", "L0+L1+L2+L3"),
        ("D_Full", "L0+L1+L2+L3+L4"),
        ("E_OPF_Solo", "OPF"),
    ]
    print("=" * 88)
    print("  Phase 4 OPF Compare")
    print("=" * 88)
    print(f"{'Config':16s} {'Stack':30s} {'TRUE':>10s} {'real_bypass':>14s}")
    print("-" * 88)
    for key, desc in ordered:
        row = overall.get(key, {})
        print(
            f"{key:16s} {desc:30s} "
            f"{float(row.get('true_rate', 0.0)):>9.2f}% "
            f"{float(row.get('real_bypass_rate', 0.0)):>13.2f}%"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare OPF result with run_e summary.")
    parser.add_argument(
        "--baseline",
        default=str(
            Path(__file__).resolve().parents[1] / "summaries" / "run_e_final_summary.json"
        ),
        help="Path to baseline 4-way summary json",
    )
    parser.add_argument("--opf", required=True, help="Path to OPF result json")
    parser.add_argument("--output", required=True, help="Path to comparison output json")
    parser.add_argument("--quiet", action="store_true", help="Do not print summary table")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    baseline_path = Path(args.baseline).expanduser().resolve()
    opf_path = Path(args.opf).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    baseline = _read_json(baseline_path)
    opf = _read_json(opf_path)

    comparison = build_comparison(
        baseline,
        opf,
        baseline_file=str(baseline_path),
        opf_file=str(opf_path),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(comparison, f, ensure_ascii=False, indent=2)

    if not args.quiet:
        print_table(comparison)
    print(f"\nSaved: {output_path}")


if __name__ == "__main__":
    main()

