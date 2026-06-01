"""Validate the isolated external Moroccan Darija import output."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from clean_external_darija import CLEAN_PATH, CLEAN_REPORT_JSON, CLEAN_REPORT_MD, dedupe_key, is_noisy_text
from download_external_darija import CLEAN_DIR, DATA_DIR, RAW_DIR, REPORTS_DIR, SOURCES_PATH


def read_json(path: Path) -> tuple[Any | None, list[str]]:
    if not path.exists():
        return None, [f"{path}: file does not exist"]
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except json.JSONDecodeError as exc:
        return None, [f"{path}: invalid JSON: {exc}"]


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    if not path.exists():
        return rows, [f"{path}: file does not exist"]

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{path.name}:{line_number}: invalid JSONL: {exc}")
                continue
            if not isinstance(row, dict):
                errors.append(f"{path.name}:{line_number}: row must be a JSON object")
                continue
            row["_line"] = line_number
            rows.append(row)
    return rows, errors


def configured_source_names(payload: Any) -> tuple[set[str], list[str]]:
    errors: list[str] = []
    names: set[str] = set()
    if not isinstance(payload, dict):
        return names, ["sources.json must be a JSON object"]
    sources = payload.get("sources")
    if not isinstance(sources, list):
        return names, ["sources.json must contain a sources list"]

    for index, source in enumerate(sources, start=1):
        if not isinstance(source, dict):
            errors.append(f"sources[{index}] must be an object")
            continue
        name = source.get("name")
        source_type = source.get("type")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"sources[{index}] missing name")
        else:
            names.add(name)
        if source_type not in {"github_raw", "huggingface", "local_files"}:
            errors.append(f"sources[{index}] unsupported type: {source_type}")
        if source_type == "github_raw" and not isinstance(source.get("urls", []), list):
            errors.append(f"sources[{index}].urls must be a list")
        if source_type == "huggingface" and not isinstance(source.get("dataset"), str):
            errors.append(f"sources[{index}].dataset must be a string")
        if source_type == "local_files" and not isinstance(source.get("paths", []), list):
            errors.append(f"sources[{index}].paths must be a list")
    return names, errors


def validate_row(row: dict[str, Any], configured_sources: set[str]) -> list[str]:
    errors: list[str] = []
    label = f"{CLEAN_PATH.name}:{row.get('_line', '?')}"

    for field_name in ("id", "text", "source", "metadata"):
        if field_name not in row:
            errors.append(f"{label}: missing {field_name}")

    if not isinstance(row.get("id"), str) or not row.get("id", "").strip():
        errors.append(f"{label}: id must be a non-empty string")

    text = row.get("text")
    if not isinstance(text, str) or not text.strip():
        errors.append(f"{label}: text must be non-empty")
    elif is_noisy_text(text):
        errors.append(f"{label}: text still looks noisy after cleaning")

    source = row.get("source")
    if not isinstance(source, dict):
        errors.append(f"{label}: source must be an object")
        source = {}
    source_name = source.get("name")
    source_type = source.get("type")
    if not isinstance(source_name, str) or not source_name.strip():
        errors.append(f"{label}: source.name must be a non-empty string")
    elif source_name not in configured_sources:
        errors.append(f"{label}: source.name is not configured in sources.json: {source_name}")
    if source_type not in {"github_raw", "huggingface", "local_files", "unknown"}:
        errors.append(f"{label}: unsupported source.type: {source_type}")
    for field_name in ("raw_ref", "row_index", "field"):
        if field_name not in source:
            errors.append(f"{label}: source.{field_name} is required")

    metadata = row.get("metadata")
    if not isinstance(metadata, dict):
        errors.append(f"{label}: metadata must be an object")
        metadata = {}
    if metadata.get("language") != "moroccan_darija":
        errors.append(f"{label}: metadata.language must be moroccan_darija")
    if metadata.get("quality") != "external_cleaned":
        errors.append(f"{label}: metadata.quality must be external_cleaned")
    if metadata.get("legal_dataset") is not False:
        errors.append(f"{label}: metadata.legal_dataset must be false")

    return errors


def validate() -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not DATA_DIR.exists():
        errors.append(f"{DATA_DIR}: directory does not exist")
    if not RAW_DIR.exists():
        errors.append(f"{RAW_DIR}: raw directory does not exist")
    if not CLEAN_DIR.exists():
        errors.append(f"{CLEAN_DIR}: clean directory does not exist")
    if not REPORTS_DIR.exists():
        errors.append(f"{REPORTS_DIR}: reports directory does not exist")

    sources_payload, source_errors = read_json(SOURCES_PATH)
    errors.extend(source_errors)
    configured_sources, config_errors = configured_source_names(sources_payload)
    errors.extend(config_errors)

    rows, row_read_errors = read_jsonl(CLEAN_PATH)
    errors.extend(row_read_errors)
    for row in rows:
        errors.extend(validate_row(row, configured_sources))

    ids = Counter(str(row.get("id", "")) for row in rows)
    duplicate_ids = [value for value, count in ids.items() if value and count > 1]
    for duplicate_id in duplicate_ids:
        errors.append(f"duplicate id: {duplicate_id}")

    normalized = Counter(dedupe_key(str(row.get("text", ""))) for row in rows if row.get("text"))
    duplicates = {text: count for text, count in normalized.items() if text and count > 1}
    for text, count in duplicates.items():
        errors.append(f"duplicate normalized text appears {count} times: {text[:120]}")

    if not CLEAN_REPORT_JSON.exists():
        warnings.append("clean_report.json was not found")
    if not CLEAN_REPORT_MD.exists():
        warnings.append("clean_report.md was not found")
    if not rows:
        warnings.append(
            "No clean examples were imported. Add DODa raw URLs or install the optional Hugging Face dependency if needed."
        )
    if RAW_DIR.exists() and not any(RAW_DIR.iterdir()):
        warnings.append("raw directory is empty because no external source produced raw files")

    source_counts = Counter(
        str(row.get("source", {}).get("name"))
        for row in rows
        if isinstance(row.get("source"), dict)
    )

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "rows": rows,
        "source_counts": dict(sorted(source_counts.items())),
        "duplicates": duplicates,
    }


def main() -> int:
    result = validate()
    print("External Darija validation")
    print(f"- examples: {len(result['rows'])}")
    print(f"- duplicate normalized texts: {len(result['duplicates'])}")
    print("- examples per source:")
    if result["source_counts"]:
        for source_name, count in result["source_counts"].items():
            print(f"  - {source_name}: {count}")
    else:
        print("  - none")

    if result["warnings"]:
        print(f"WARN: {len(result['warnings'])} warning(s)")
        for warning in result["warnings"]:
            print(f"  - {warning}")

    if result["errors"]:
        print(f"FAIL: {len(result['errors'])} validation error(s)")
        for error in result["errors"][:200]:
            print(f"  - {error}")
        if len(result["errors"]) > 200:
            print(f"  - ... {len(result['errors']) - 200} more")
        return 1

    print("PASS: external Darija import is structurally valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
