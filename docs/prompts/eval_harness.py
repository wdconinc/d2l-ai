#!/usr/bin/env python3
"""Prompt regression harness for docs/prompts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROMPTS_ROOT = ROOT / "docs" / "prompts"
CATALOG_PATH = PROMPTS_ROOT / "catalog.json"


class FixtureProvider:
    """Deterministic provider that returns fixture outputs from case files."""

    def generate(self, case: dict[str, Any]) -> Any:
        return case["fixture_output"]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalized(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def check_metadata(entry: dict[str, Any]) -> list[str]:
    required = ["owner", "workflow", "model_assumptions", "safety_notes"]
    return [field for field in required if not entry.get(field)]


def run_fixture_regression() -> int:
    catalog = load_json(CATALOG_PATH)
    provider = FixtureProvider()

    failures: list[str] = []
    total = 0

    for prompt in catalog["prompts"]:
        missing_fields = check_metadata(prompt)
        if missing_fields:
            failures.append(
                f"{prompt['id']} missing metadata fields: {', '.join(missing_fields)}"
            )

        prompt_file = ROOT / prompt["prompt_file"]
        if not prompt_file.exists():
            failures.append(f"Missing prompt file: {prompt_file}")

        golden_dir = ROOT / prompt["golden_dir"]
        case_files = sorted(golden_dir.glob("*.json"))
        if len(case_files) < 3:
            failures.append(f"{prompt['id']} requires at least 3 golden cases (found {len(case_files)})")

        for case_file in case_files:
            total += 1
            case = load_json(case_file)

            if case["prompt_id"] != prompt["id"]:
                failures.append(f"{case_file} prompt_id mismatch")
            if case["version"] != prompt["version"]:
                failures.append(f"{case_file} version mismatch")

            first = provider.generate(case)
            second = provider.generate(case)
            if normalized(first) != normalized(second):
                failures.append(f"{case_file} fixture provider is non-deterministic")

            if normalized(first) != normalized(case["expected_output"]):
                failures.append(f"{case_file} output mismatch")

    if failures:
        print("Prompt regression checks failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"Prompt regression checks passed ({total} golden cases).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run prompt regression checks")
    parser.add_argument(
        "--provider",
        choices=["fixture"],
        default="fixture",
        help="Provider backend to use. Currently only deterministic fixture provider is supported.",
    )
    _ = parser.parse_args()

    return run_fixture_regression()


if __name__ == "__main__":
    sys.exit(main())
