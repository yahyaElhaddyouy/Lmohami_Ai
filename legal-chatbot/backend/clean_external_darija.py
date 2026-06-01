# -*- coding: utf-8 -*-
"""Clean isolated external Moroccan Darija raw files.

The output is useful for language-understanding review/evaluation only. It is
not added to Chroma, legal RAG sources, or supervised legal fine-tuning splits.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from download_external_darija import (
    CLEAN_DIR,
    DATA_DIR,
    PROJECT_DIR,
    RAW_DIR,
    REPORTS_DIR,
    SOURCES_PATH,
    ensure_layout,
    relative,
    safe_name,
)


CLEAN_PATH = CLEAN_DIR / "clean_darija_examples.jsonl"
CLEAN_REPORT_JSON = REPORTS_DIR / "clean_report.json"
CLEAN_REPORT_MD = REPORTS_DIR / "clean_report.md"

MIN_TEXT_CHARS = 3
MAX_TEXT_CHARS = 800

URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", re.IGNORECASE)
PHONE_RE = re.compile(r"\b(?:\+?212|0)[5-7]\d{8}\b")
ARABIC_RE = re.compile(r"[\u0600-\u06ff]")
TASHKEEL_RE = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")
LATIN_DARIJA_RE = re.compile(
    r"\b(?:wach|chno|ch7al|chhal|bghit|bghiti|bgha|khoya|khti|safi|"
    r"bzaf|bezaf|ana|nta|nti|dyali|diali|dyal|dial|kayn|kayna|machi|"
    r"ma3a|m3a|3lach|7it|hadchi|mzyan|salam|labas|fin|kifach|ndiro|"
    r"ndir|n9dar|9dar|baghi|bagha|hadi|hada|lyoum|daba|m9ele9|"
    r"mkele9|nrtah|fhemt|fhemtini|walo|khassni|b7al|chwiya)\b",
    re.IGNORECASE,
)

PREFERRED_FIELD_HINTS = (
    "darija",
    "moroccan",
    "ary",
    "text",
    "sentence",
    "utterance",
    "content",
    "message",
    "question",
    "answer",
    "tweet",
    "body",
)
EXCLUDED_FIELD_HINTS = (
    "id",
    "idx",
    "url",
    "link",
    "license",
    "source",
    "split",
    "label",
    "score",
    "lang",
    "date",
)


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def normalize_darija(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u0640", "")
    text = TASHKEEL_RE.sub("", text)
    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
        "ؤ": "و",
        "ئ": "ي",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = "".join(
        char
        for char in text
        if unicodedata.category(char)[0] != "C" or char in {"\n", "\t"}
    )
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t\n\f\v]+", " ", text)
    return text.strip()


def dedupe_key(text: str) -> str:
    compact = normalize_darija(text).casefold()
    compact = re.sub(r"[^\w\u0600-\u06ff]+", " ", compact)
    return re.sub(r"\s+", " ", compact).strip()


def has_darija_signal(text: str) -> bool:
    return bool(ARABIC_RE.search(text) or LATIN_DARIJA_RE.search(text))


def is_noisy_text(text: str) -> bool:
    if len(text) < MIN_TEXT_CHARS or len(text) > MAX_TEXT_CHARS:
        return True
    if URL_RE.search(text) or EMAIL_RE.search(text) or PHONE_RE.search(text):
        return True
    if not has_darija_signal(text):
        return True

    visible = [char for char in text if not char.isspace()]
    if not visible:
        return True

    letter_count = sum(1 for char in visible if unicodedata.category(char).startswith("L"))
    digit_count = sum(1 for char in visible if unicodedata.category(char).startswith("N"))
    if letter_count / len(visible) < 0.45:
        return True
    if digit_count / len(visible) > 0.45:
        return True
    if len(set(visible)) <= 2 and len(visible) > 10:
        return True
    return False


def nested_get(row: dict[str, Any], field_path: str) -> Any:
    value: Any = row
    for part in field_path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def flatten_strings(value: Any, prefix: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield prefix or "text", value
        return
    if isinstance(value, dict):
        for key, item in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            yield from flatten_strings(item, child_prefix)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            child_prefix = f"{prefix}.{index}" if prefix else str(index)
            yield from flatten_strings(item, child_prefix)


def field_is_preferred(field_name: str) -> bool:
    lowered = field_name.casefold()
    if any(hint in lowered for hint in EXCLUDED_FIELD_HINTS):
        return False
    return any(hint in lowered for hint in PREFERRED_FIELD_HINTS)


def text_candidates(row: Any, configured_fields: list[str] | None = None) -> list[tuple[str, str]]:
    if isinstance(row, str):
        return [("text", row)]
    if not isinstance(row, dict):
        return []

    if configured_fields:
        candidates = []
        for field_name in configured_fields:
            value = nested_get(row, field_name)
            if isinstance(value, str):
                candidates.append((field_name, value))
        return candidates

    strings = [(field_name, value) for field_name, value in flatten_strings(row)]
    preferred = [(field_name, value) for field_name, value in strings if field_is_preferred(field_name)]
    if preferred:
        return preferred
    return [
        (field_name, value)
        for field_name, value in strings
        if not any(hint in field_name.casefold() for hint in EXCLUDED_FIELD_HINTS)
    ]


def json_records(payload: Any) -> Iterable[Any]:
    if isinstance(payload, list):
        yield from payload
        return
    if not isinstance(payload, dict):
        yield payload
        return
    list_values = [value for value in payload.values() if isinstance(value, list)]
    if list_values:
        for value in list_values:
            yield from json_records(value)
        return
    yield payload


def rows_from_raw_file(path: Path) -> Iterable[tuple[int, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        with path.open("r", encoding="utf-8-sig") as handle:
            for line_number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield line_number, json.loads(line)
                except json.JSONDecodeError:
                    yield line_number, line
        return

    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        for row_number, row in enumerate(json_records(payload), start=1):
            yield row_number, row
        return

    if suffix in {".csv", ".tsv"}:
        delimiter = "\t" if suffix == ".tsv" else ","
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            rows = list(reader)
        if not rows:
            return
        header = [cell.strip().casefold() for cell in rows[0]]
        has_header = any(any(hint in cell for hint in PREFERRED_FIELD_HINTS) for cell in header)
        data_rows = rows[1:] if has_header else rows
        field_names = rows[0] if has_header else [f"col_{index}" for index in range(1, len(rows[0]) + 1)]
        for row_number, row in enumerate(data_rows, start=2 if has_header else 1):
            yield row_number, {
                field_names[index] if index < len(field_names) else f"col_{index + 1}": value
                for index, value in enumerate(row)
            }
        return

    if suffix == ".zip":
        return

    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if line:
                yield line_number, line


def load_sources_config() -> dict[str, dict[str, Any]]:
    if not SOURCES_PATH.exists():
        return {}
    payload = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    sources = payload.get("sources", [])
    if not isinstance(sources, list):
        return {}
    return {
        str(source.get("name")): source
        for source in sources
        if isinstance(source, dict) and isinstance(source.get("name"), str)
    }


def infer_source_for_path(path: Path, config: dict[str, dict[str, Any]]) -> dict[str, Any]:
    try:
        rel_parts = path.resolve().relative_to(RAW_DIR.resolve()).parts
    except ValueError:
        rel_parts = path.parts
    source_name = rel_parts[0] if rel_parts else "unknown"
    configured = dict(config.get(source_name, {}))
    configured.setdefault("name", source_name)
    configured.setdefault("type", "unknown")
    return configured


def make_clean_record(
    *,
    text: str,
    source: dict[str, Any],
    raw_ref: str,
    row_index: int,
    field_name: str,
) -> dict[str, Any]:
    source_name = str(source.get("name", "unknown"))
    digest = hashlib.sha1(
        f"{source_name}\n{raw_ref}\n{row_index}\n{field_name}\n{text}".encode("utf-8")
    ).hexdigest()[:12]
    return {
        "id": f"external-darija-{safe_name(source_name)}-{digest}",
        "text": text,
        "source": {
            "name": source_name,
            "type": source.get("type", "unknown"),
            "dataset": source.get("dataset"),
            "raw_ref": raw_ref,
            "row_index": row_index,
            "field": field_name,
        },
        "metadata": {
            "language": "moroccan_darija",
            "quality": "external_cleaned",
            "legal_dataset": False,
            "normalized": True,
            "contains_arabizi": bool(LATIN_DARIJA_RE.search(text) and not ARABIC_RE.search(text)),
        },
    }


def raw_files() -> list[Path]:
    suffixes = {".jsonl", ".json", ".csv", ".tsv", ".txt"}
    return sorted(path for path in RAW_DIR.rglob("*") if path.is_file() and path.suffix.lower() in suffixes)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def clean_external_data() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ensure_layout()
    config = load_sources_config()
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    counters = Counter()
    source_counts = Counter()
    per_file: list[dict[str, Any]] = []

    for path in raw_files():
        source = infer_source_for_path(path, config)
        configured_fields = source.get("text_fields")
        if not isinstance(configured_fields, list):
            configured_fields = None

        file_stats = Counter()
        raw_ref = relative(path)
        try:
            for row_index, row in rows_from_raw_file(path):
                counters["raw_rows"] += 1
                file_stats["raw_rows"] += 1
                for field_name, value in text_candidates(row, configured_fields):
                    counters["candidate_texts"] += 1
                    file_stats["candidate_texts"] += 1
                    text = normalize_darija(value)
                    if not text:
                        counters["empty_rows"] += 1
                        file_stats["empty_rows"] += 1
                        continue
                    if is_noisy_text(text):
                        counters["filtered_noisy"] += 1
                        file_stats["filtered_noisy"] += 1
                        continue
                    key = dedupe_key(text)
                    if key in seen:
                        counters["duplicates_removed"] += 1
                        file_stats["duplicates_removed"] += 1
                        continue
                    seen.add(key)
                    rows.append(
                        make_clean_record(
                            text=text,
                            source=source,
                            raw_ref=raw_ref,
                            row_index=row_index,
                            field_name=field_name,
                        )
                    )
                    counters["kept"] += 1
                    file_stats["kept"] += 1
                    source_counts[str(source.get("name", "unknown"))] += 1
        except Exception as exc:  # noqa: BLE001
            file_stats["errors"] += 1
            per_file.append({"path": raw_ref, **dict(file_stats), "error": str(exc)})
            continue
        per_file.append({"path": raw_ref, **dict(file_stats)})

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "Clean external Moroccan Darija text; isolated from legal RAG and SFT data.",
        "raw_dir": relative(RAW_DIR),
        "clean_output": relative(CLEAN_PATH),
        "total_clean_examples": len(rows),
        "counts": dict(counters),
        "source_counts": dict(sorted(source_counts.items())),
        "files": per_file,
        "next_step": "Use this only for language review/evaluation until a separate training plan is approved.",
    }
    return rows, report


def write_reports(rows: list[dict[str, Any]], report: dict[str, Any]) -> None:
    CLEAN_REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# External Darija Clean Report",
        "",
        "## Summary",
        "",
        f"- Clean examples written: {len(rows)}",
        f"- Raw rows scanned: {report['counts'].get('raw_rows', 0)}",
        f"- Candidate texts: {report['counts'].get('candidate_texts', 0)}",
        f"- Duplicates removed: {report['counts'].get('duplicates_removed', 0)}",
        f"- Noisy rows filtered: {report['counts'].get('filtered_noisy', 0)}",
        f"- Clean output: `{relative(CLEAN_PATH)}`",
        "",
        "## Examples Per Source",
        "",
    ]
    if report["source_counts"]:
        for source_name, count in report["source_counts"].items():
            lines.append(f"- {source_name}: {count}")
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Guardrail",
            "",
            "The clean file is external language data only. It has not been ingested into Chroma, mixed with legal sources, or used for training.",
            "",
        ]
    )
    CLEAN_REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    configure_stdout()
    rows, report = clean_external_data()
    write_jsonl(CLEAN_PATH, rows)
    write_reports(rows, report)

    print("External Darija cleaning")
    print(f"- raw rows: {report['counts'].get('raw_rows', 0)}")
    print(f"- clean examples: {len(rows)}")
    print(f"- duplicates removed: {report['counts'].get('duplicates_removed', 0)}")
    print(f"- noisy rows filtered: {report['counts'].get('filtered_noisy', 0)}")
    print(f"- output: {relative(CLEAN_PATH)}")
    print(f"- report: {relative(CLEAN_REPORT_MD)}")
    print("No legal RAG data was modified and no training was started.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
