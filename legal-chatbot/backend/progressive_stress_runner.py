# -*- coding: utf-8 -*-
"""Run gated 50 -> 200 -> 500 stress phases with narrowly scoped safe fixes.

The runner never changes legal rules, article interpretation, compensation
amounts, deadlines, penalties, or legal conclusions. It can apply only exact,
predeclared routing/configuration fixes after matching failures are observed.
Every attempt, baseline command, gate decision, and source edit is recorded.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
RUNS_DIR = BASE_DIR / "stress_runs"
PROGRESSIVE_REPORT_PATH = RUNS_DIR / "PROGRESSIVE_STRESS_REPORT.md"
BLOCKED_REPORT_PATH = RUNS_DIR / "BLOCKED_REPORT.md"
MANUAL_REVIEW_PATH = RUNS_DIR / "manual_review_required.md"
FIX_LOG_PATH = RUNS_DIR / "fixes_applied.jsonl"

PHASES = (50, 200, 500)
CRITICAL_FAILURES = {
    "hallucination_error",
    "legal_guarantee_error",
    "exception_error",
}
UNSAFE_LEGAL_FAILURES = {
    "hallucination_error",
}


@dataclass(frozen=True)
class SafeFix:
    name: str
    description: str
    failure_types: tuple[str, ...]
    detector: Callable[[list[dict[str, Any]]], bool]
    apply: Callable[[], list[str]]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path}:{line_number}") from exc
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def run_command(
    name: str,
    command: list[str],
    output_dir: Path,
    timeout_seconds: int | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = output_dir / f"{name}.out.log"
    stderr_path = output_dir / f"{name}.err.log"
    started = time.perf_counter()
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    try:
        completed = subprocess.run(
            command,
            cwd=BASE_DIR,
            env=merged_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
        return_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        return_code = 124
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        stderr += f"\nTimed out after {timeout_seconds} seconds.\n"
        timed_out = True

    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    elapsed_seconds = time.perf_counter() - started
    return {
        "name": name,
        "command": command,
        "return_code": return_code,
        "timed_out": timed_out,
        "elapsed_seconds": round(elapsed_seconds, 2),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "stdout": stdout,
        "stderr": stderr,
    }


def metric_from_text(text: str, labels: tuple[str, ...]) -> float | None:
    for label in labels:
        match = re.search(
            rf"{re.escape(label)}[^\n]*?"
            rf"(?:\((\d+(?:\.\d+)?)%\)|(\d+(?:\.\d+)?)%)",
            text,
            re.IGNORECASE,
        )
        if match:
            value = match.group(1) or match.group(2)
            return float(value) / 100
    return None


def parse_stress_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    passed = sum(bool(row.get("passed")) for row in results)
    failures_by_type: Counter[str] = Counter()
    latencies: list[float] = []
    for row in results:
        failures_by_type.update(row.get("failure_types") or [])
        latencies.append(float(row.get("latency_ms") or 0))

    sorted_latencies = sorted(latencies)
    median = 0.0
    if sorted_latencies:
        middle = len(sorted_latencies) // 2
        if len(sorted_latencies) % 2:
            median = sorted_latencies[middle]
        else:
            median = (
                sorted_latencies[middle - 1] + sorted_latencies[middle]
            ) / 2

    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": passed / total if total else 0.0,
        "failures_by_type": dict(failures_by_type),
        "average_latency_ms": (
            sum(latencies) / len(latencies) if latencies else 0.0
        ),
        "median_latency_ms": median,
        "max_latency_ms": max(latencies) if latencies else 0.0,
        "critical_hallucinations": failures_by_type["hallucination_error"],
        "legal_guarantees": failures_by_type["legal_guarantee_error"],
        "exceptions": failures_by_type["exception_error"],
    }


def api_contract_check(output_dir: Path) -> dict[str, Any]:
    script = (
        "from fastapi.testclient import TestClient\n"
        "import main\n"
        "client = TestClient(main.app, raise_server_exceptions=False)\n"
        "response = client.post('/chat', json={'question': 'سلام'})\n"
        "body = response.json()\n"
        "ok = response.status_code == 200 and isinstance(body.get('answer'), str) "
        "and isinstance(body.get('sources'), list)\n"
        "print(f'API_CONTRACT={int(ok)} STATUS={response.status_code} "
        "KEYS={sorted(body.keys())}')\n"
        "raise SystemExit(0 if ok else 1)\n"
    )
    return run_command(
        "api_contract",
        [sys.executable, "-c", script],
        output_dir,
        timeout_seconds=60,
    )


def run_baselines(output_dir: Path) -> dict[str, Any]:
    baseline_dir = output_dir / "baselines"
    commands = (
        (
            "conversation_classifier",
            [sys.executable, "evaluate_conversation_classifier.py"],
            300,
        ),
        (
            "darija_comprehension",
            [sys.executable, "evaluate_darija_comprehension.py"],
            7_200,
        ),
        (
            "darija_intent",
            [sys.executable, "evaluate_darija_intent.py"],
            300,
        ),
        (
            "trust",
            [
                sys.executable,
                "evaluate_trust.py",
                "--report",
                str(output_dir / "trust_report.json"),
            ],
            7_200,
        ),
        (
            "darija_intent_priority",
            [sys.executable, "test_darija_intent_priority.py"],
            300,
        ),
    )
    command_results = {
        name: run_command(name, command, baseline_dir, timeout_seconds)
        for name, command, timeout_seconds in commands
    }
    command_results["api_contract"] = api_contract_check(baseline_dir)

    classifier_text = command_results["conversation_classifier"]["stdout"]
    comprehension_text = command_results["darija_comprehension"]["stdout"]
    intent_text = command_results["darija_intent"]["stdout"]
    trust_text = command_results["trust"]["stdout"]

    classifier_score = metric_from_text(classifier_text, ("Accuracy:",))
    comprehension_score = metric_from_text(
        comprehension_text,
        ("Darija comprehension score:", "Pass rate:", "Accuracy:"),
    )
    intent_score = metric_from_text(intent_text, ("Accuracy:",))
    trust_score = metric_from_text(trust_text, ("Trust score:",))

    summary = {
        "conversation_classifier_score": classifier_score,
        "darija_comprehension_score": comprehension_score,
        "intent_score": intent_score,
        "trust_score": trust_score,
        "priority_test_passed": (
            command_results["darija_intent_priority"]["return_code"] == 0
        ),
        "api_contract_passed": (
            command_results["api_contract"]["return_code"] == 0
        ),
        "all_commands_passed": all(
            result["return_code"] == 0 for result in command_results.values()
        ),
        "commands": {
            name: {
                key: value
                for key, value in result.items()
                if key not in {"stdout", "stderr"}
            }
            for name, result in command_results.items()
        },
    }
    write_json(output_dir / "baseline_summary.json", summary)
    return summary


def verified_rules_fix_needed(results: list[dict[str, Any]]) -> bool:
    failure_counts = Counter(
        failure
        for row in results
        for failure in (row.get("failure_types") or [])
    )
    rag_text = (BASE_DIR / "rag.py").read_text(encoding="utf-8")
    default_is_false = (
        'os.getenv("USE_VERIFIED_RULES_FIRST", "false")' in rag_text
    )
    return default_is_false and (
        failure_counts["latency_error"] >= 3
        or failure_counts["citation_error"] >= 1
    )


def apply_verified_rules_fix() -> list[str]:
    path = BASE_DIR / "rag.py"
    content = path.read_bytes()
    old = b'os.getenv("USE_VERIFIED_RULES_FIRST", "false")'
    new = b'os.getenv("USE_VERIFIED_RULES_FIRST", "true")'
    if old not in content:
        return []
    path.write_bytes(content.replace(old, new, 1))
    return [str(path)]


def vague_dismissal_fix_needed(results: list[dict[str, Any]]) -> bool:
    phrases = ("سير ترتاح", "حتى نعيطو ليك", "بقا فداركم")
    return any(
        "conversation_routing_error" in (row.get("failure_types") or [])
        and row.get("topic") == "vague_dismissal"
        and any(phrase in str(row.get("question")) for phrase in phrases)
        for row in results
    )


def apply_vague_dismissal_fix() -> list[str]:
    path = BASE_DIR / "conversation_classifier.py"
    content = path.read_bytes()
    anchor = b"LABOR_PHRASES = (\n"
    addition = (
        "LABOR_PHRASES = (\n"
        '    "سير ترتاح حتى نعيطو ليك",\n'
        '    "سير ترتاح",\n'
        '    "حتى نعيطو ليك",\n'
        '    "بقا فداركم",\n'
    ).encode("utf-8")
    if "سير ترتاح حتى نعيطو ليك".encode("utf-8") in content:
        return []
    if anchor not in content:
        anchor = b"LABOR_PHRASES = (\r\n"
        addition = (
            "LABOR_PHRASES = (\r\n"
            '    "سير ترتاح حتى نعيطو ليك",\r\n'
            '    "سير ترتاح",\r\n'
            '    "حتى نعيطو ليك",\r\n'
            '    "بقا فداركم",\r\n'
        ).encode("utf-8")
    if anchor not in content:
        return []
    path.write_bytes(content.replace(anchor, addition, 1))
    return [str(path)]


def routing_variants_fix_needed(results: list[dict[str, Any]]) -> bool:
    target_topics = {
        "greetings",
        "thanks",
        "sick_leave",
        "no_written_contract",
        "vague_dismissal",
        "dismissal",
    }
    return any(
        "conversation_routing_error" in (row.get("failure_types") or [])
        and row.get("topic") in target_topics
        for row in results
    )


def apply_routing_variants_fix() -> list[str]:
    path = BASE_DIR / "conversation_classifier.py"
    content = path.read_bytes()
    changed = False

    thanks_anchor = b'    "lah yhafdek",\n'
    thanks_addition = (
        '    "lah yhafdek",\n'
        '    "lah yjazik bikhir",\n'
    ).encode("utf-8")
    if b'"lah yjazik bikhir"' not in content and thanks_anchor in content:
        content = content.replace(thanks_anchor, thanks_addition, 1)
        changed = True

    phrase_anchor = b"LABOR_PHRASES = (\n"
    phrase_addition = (
        "LABOR_PHRASES = (\n"
        '    "patron gal lia ma tb9ach tji",\n'
        '    "ma tb9ach tji",\n'
        '    "sir trta7",\n'
        '    "7ta n3ayto lik",\n'
        '    "mrdt",\n'
        '    "certificat medical",\n'
        '    "khdam bla contrat",\n'
        '    "bla contrat",\n'
        '    "خدام بلا عقد",\n'
        '    "بلا عقد مكتوب",\n'
    ).encode("utf-8")
    if b'"patron gal lia ma tb9ach tji"' not in content:
        if phrase_anchor not in content:
            phrase_anchor = b"LABOR_PHRASES = (\r\n"
            phrase_addition = phrase_addition.replace(b"\n", b"\r\n")
        if phrase_anchor in content:
            content = content.replace(phrase_anchor, phrase_addition, 1)
            changed = True

    helper_anchor = b"\ndef is_short_exact(normalized: str, terms: set[str]) -> bool:\n"
    helper_addition = (
        "\ndef contains_standalone_phrase(normalized: str, terms: set[str]) -> bool:\n"
        "    for term in terms:\n"
        "        normalized_term = normalize_text(term)\n"
        "        if re.search(\n"
        "            rf\"(?:^|\\\\s){re.escape(normalized_term)}(?:$|\\\\s)\",\n"
        "            normalized,\n"
        "        ):\n"
        "            return True\n"
        "    return False\n"
        "\n"
        "\ndef is_short_exact(normalized: str, terms: set[str]) -> bool:\n"
    ).encode("utf-8")
    if b"def contains_standalone_phrase(" not in content:
        if helper_anchor not in content:
            helper_anchor = helper_anchor.replace(b"\n", b"\r\n")
            helper_addition = helper_addition.replace(b"\n", b"\r\n")
        if helper_anchor in content:
            content = content.replace(helper_anchor, helper_addition, 1)
            changed = True

    content = content.replace(
        b"    if is_short_exact(normalized, GREETINGS):\n",
        b"    if contains_standalone_phrase(normalized, GREETINGS):\n",
        1,
    )
    content = content.replace(
        b"    if is_short_exact(normalized, THANKS):\n",
        b"    if contains_standalone_phrase(normalized, THANKS):\n",
        1,
    )
    content = content.replace(
        b"    if is_short_exact(normalized, GREETINGS):\r\n",
        b"    if contains_standalone_phrase(normalized, GREETINGS):\r\n",
        1,
    )
    content = content.replace(
        b"    if is_short_exact(normalized, THANKS):\r\n",
        b"    if contains_standalone_phrase(normalized, THANKS):\r\n",
        1,
    )

    if not changed:
        return []
    path.write_bytes(content)
    return [str(path)]


def paid_leave_intent_fix_needed(results: list[dict[str, Any]]) -> bool:
    return any(
        "intent_error" in (row.get("failure_types") or [])
        and row.get("topic") == "annual_leave"
        and row.get("detected_legal_intent") == "unclear"
        for row in results
    )


def apply_paid_leave_intent_fix() -> list[str]:
    path = BASE_DIR / "legal_understanding.py"
    content = path.read_bytes()
    old = b"        + sick_leave_terms\n    )"
    new = (
        '        + sick_leave_terms\n'
        '        + ("كونجي", "عطلة", "congé", "conge")\n'
        "    )"
    ).encode("utf-8")
    if old not in content:
        old = old.replace(b"\n", b"\r\n")
        new = new.replace(b"\n", b"\r\n")
    if old not in content or '+ ("كونجي", "عطلة"'.encode("utf-8") in content:
        return []
    path.write_bytes(content.replace(old, new, 1))
    return [str(path)]


def social_boundary_fix_needed(results: list[dict[str, Any]]) -> bool:
    path = BASE_DIR / "conversation_classifier.py"
    content = path.read_bytes()
    has_escaping_bug = b'(?:^|\\\\s)' in content or b'(?:$|\\\\s)' in content
    has_social_failures = any(
        "conversation_routing_error" in (row.get("failure_types") or [])
        and row.get("topic") in {"greetings", "thanks"}
        for row in results
    )
    return has_escaping_bug and has_social_failures


def apply_social_boundary_fix() -> list[str]:
    path = BASE_DIR / "conversation_classifier.py"
    content = path.read_bytes()
    updated = content.replace(b'(?:^|\\\\s)', b'(?:^|\\s)')
    updated = updated.replace(b'(?:$|\\\\s)', b'(?:$|\\s)')
    if updated == content:
        return []
    path.write_bytes(updated)
    return [str(path)]


def arabizi_legal_intent_fix_needed(results: list[dict[str, Any]]) -> bool:
    return any(
        "intent_error" in (row.get("failure_types") or [])
        and row.get("style") == "arabizi"
        and row.get("topic") in {"sick_leave", "dismissal", "vague_dismissal"}
        for row in results
    )


def apply_arabizi_legal_intent_fix() -> list[str]:
    path = BASE_DIR / "legal_understanding.py"
    content = path.read_bytes()
    updated = content

    dismissal_anchor = (
        '        "حيدوه",\n'
        '        "ما تبقاش تجي",\n'
    ).encode("utf-8")
    dismissal_addition = (
        '        "حيدوه",\n'
        '        "ma tb9ach tji",\n'
        '        "sir trta7",\n'
        '        "7ta n3ayto lik",\n'
        '        "ما تبقاش تجي",\n'
    ).encode("utf-8")
    if dismissal_anchor not in updated:
        dismissal_anchor = dismissal_anchor.replace(b"\n", b"\r\n")
        dismissal_addition = dismissal_addition.replace(b"\n", b"\r\n")
    if b'"ma tb9ach tji"' not in updated and dismissal_anchor in updated:
        updated = updated.replace(dismissal_anchor, dismissal_addition, 1)

    vague_anchor = (
        "    vague_dismissal_terms = (\n"
        '        "ما تبقاش تجي",\n'
    ).encode("utf-8")
    vague_addition = (
        "    vague_dismissal_terms = (\n"
        '        "ma tb9ach tji",\n'
        '        "sir trta7",\n'
        '        "7ta n3ayto lik",\n'
        '        "ما تبقاش تجي",\n'
    ).encode("utf-8")
    if vague_anchor not in updated:
        vague_anchor = vague_anchor.replace(b"\n", b"\r\n")
        vague_addition = vague_addition.replace(b"\n", b"\r\n")
    if b'vague_dismissal_terms = (\n        "ma tb9ach tji"' not in updated:
        if vague_anchor in updated:
            updated = updated.replace(vague_anchor, vague_addition, 1)

    sick_anchor = (
        "    sick_leave_terms = (\n"
        '        "مرض",\n'
        '        "مرضت",\n'
    ).encode("utf-8")
    sick_addition = (
        "    sick_leave_terms = (\n"
        '        "مرض",\n'
        '        "مرضت",\n'
        '        "mrdt",\n'
    ).encode("utf-8")
    if sick_anchor not in updated:
        sick_anchor = sick_anchor.replace(b"\n", b"\r\n")
        sick_addition = sick_addition.replace(b"\n", b"\r\n")
    if b'        "mrdt",' not in updated and sick_anchor in updated:
        updated = updated.replace(sick_anchor, sick_addition, 1)

    if updated == content:
        return []
    path.write_bytes(updated)
    return [str(path)]


SAFE_FIXES = (
    SafeFix(
        name="verified_rules_first",
        description=(
            "Restore the existing verified-rule-first default to reduce unsafe "
            "LLM drift, citation mismatches, and >30s generation latency."
        ),
        failure_types=("latency_error", "citation_error"),
        detector=verified_rules_fix_needed,
        apply=apply_verified_rules_fix,
    ),
    SafeFix(
        name="vague_dismissal_routing",
        description=(
            "Route explicit 'wait at home until we call you' dismissal wording "
            "into the labor-law path."
        ),
        failure_types=("conversation_routing_error", "refusal_error"),
        detector=vague_dismissal_fix_needed,
        apply=apply_vague_dismissal_fix,
    ),
    SafeFix(
        name="routing_variants",
        description=(
            "Recognize embedded greetings/thanks and observed Arabizi or "
            "no-contract labor phrases without changing legal answers."
        ),
        failure_types=("conversation_routing_error", "refusal_error"),
        detector=routing_variants_fix_needed,
        apply=apply_routing_variants_fix,
    ),
    SafeFix(
        name="paid_leave_intent_priority",
        description=(
            "Keep explicit annual-leave terms specific when the user also says "
            "the details are unclear."
        ),
        failure_types=("intent_error",),
        detector=paid_leave_intent_fix_needed,
        apply=apply_paid_leave_intent_fix,
    ),
    SafeFix(
        name="social_phrase_boundary_correction",
        description=(
            "Correct the standalone greeting/thanks regex escaping so prefixed "
            "social messages route as intended."
        ),
        failure_types=("conversation_routing_error",),
        detector=social_boundary_fix_needed,
        apply=apply_social_boundary_fix,
    ),
    SafeFix(
        name="arabizi_legal_intents",
        description=(
            "Recognize the observed Arabizi sick-leave and dismissal wording in "
            "legal understanding without changing any legal rule content."
        ),
        failure_types=("intent_error", "refusal_error"),
        detector=arabizi_legal_intent_fix_needed,
        apply=apply_arabizi_legal_intent_fix,
    ),
)


def record_manual_review(
    phase: int,
    attempt: int,
    results: list[dict[str, Any]],
) -> None:
    unsafe_rows = [
        row
        for row in results
        if UNSAFE_LEGAL_FAILURES & set(row.get("failure_types") or [])
    ]
    if not unsafe_rows:
        return

    if not MANUAL_REVIEW_PATH.exists():
        MANUAL_REVIEW_PATH.write_text(
            "# Manual Review Required\n\n"
            "These legal-content cases are intentionally not auto-fixed.\n\n",
            encoding="utf-8",
        )
    with MANUAL_REVIEW_PATH.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"## Phase {phase}, Attempt {attempt}\n\n")
        for row in unsafe_rows:
            handle.write(
                f"- `{row['id']}` [{row['topic']}]: {row['question']} "
                f"-> {', '.join(row['failure_types'])}\n"
            )
        handle.write("\n")


def choose_safe_fix(
    results: list[dict[str, Any]],
    fixes_already_applied: set[str],
) -> SafeFix | None:
    for fix in SAFE_FIXES:
        if fix.name in fixes_already_applied:
            continue
        if fix.detector(results):
            return fix
    return None


def archive_attempt(run_dir: Path, attempt: int) -> Path:
    attempt_dir = run_dir / "attempts" / f"attempt_{attempt}"
    attempt_dir.mkdir(parents=True, exist_ok=True)
    for name in ("results.jsonl", "failures.jsonl", "report.md", "stress.out.log", "stress.err.log"):
        source = run_dir / name
        if source.exists():
            shutil.copy2(source, attempt_dir / name)
    return attempt_dir


def run_stress_phase(
    phase: int,
    run_dir: Path,
    resume: bool,
    rerun_failures: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    command = [
        sys.executable,
        "-u",
        "stress_real_users.py",
        "--limit",
        str(phase),
        "--output-dir",
        str(run_dir),
        "--progress-every",
        "5",
        "--checkpoint-every",
        "10",
    ]
    if resume:
        command.append("--resume")
    if rerun_failures:
        command.append("--rerun-failures")
    command_result = run_command(
        "stress",
        command,
        run_dir,
        timeout_seconds=43_200,
    )
    results = read_jsonl(run_dir / "results.jsonl")
    summary = parse_stress_summary(results)
    summary["command_return_code"] = command_result["return_code"]
    summary["complete"] = len(results) == phase
    write_json(run_dir / "stress_summary.json", summary)
    return summary, command_result


def gate_decision(
    phase: int,
    stress: dict[str, Any],
    baselines: dict[str, Any],
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not stress.get("complete"):
        reasons.append(f"stress run completed {stress.get('total')}/{phase} cases")
    if float(stress.get("pass_rate") or 0) < 0.90:
        reasons.append(
            f"stress pass rate {float(stress.get('pass_rate') or 0):.1%} is below 90%"
        )
    if stress.get("critical_hallucinations"):
        reasons.append("critical hallucination cases are non-zero")
    if stress.get("legal_guarantees"):
        reasons.append("legal guarantee cases are non-zero")
    if stress.get("exceptions"):
        reasons.append("API/backend exception cases are non-zero")
    if float(baselines.get("trust_score") or 0) < 0.95:
        reasons.append("trust score is below 95% or could not be parsed")
    if float(baselines.get("intent_score") or 0) < 0.95:
        reasons.append("intent score is below 95% or could not be parsed")
    if not baselines.get("priority_test_passed"):
        reasons.append("Darija intent priority test failed")
    if not baselines.get("api_contract_passed"):
        reasons.append("FastAPI answer/sources response contract failed")
    if not baselines.get("all_commands_passed"):
        reasons.append("one or more baseline commands failed")
    return not reasons, reasons


def write_blocked_report(
    phase: int,
    attempt: int,
    stress: dict[str, Any],
    baselines: dict[str, Any] | None,
    reasons: list[str],
    fixes: list[dict[str, Any]],
) -> None:
    lines = [
        "# Progressive Stress Testing Blocked",
        "",
        f"- Phase: {phase}",
        f"- Attempt: {attempt}",
        f"- Stress pass rate: {float(stress.get('pass_rate') or 0):.2%}",
        f"- Completed: {stress.get('total', 0)}/{phase}",
        "",
        "## Blocking Reasons",
        "",
    ]
    lines.extend(f"- {reason}" for reason in reasons)
    lines.extend(["", "## Fixes Applied", ""])
    if fixes:
        for fix in fixes:
            lines.append(f"- {fix['name']}: {fix['description']}")
    else:
        lines.append("- None")
    if baselines is not None:
        lines.extend(
            [
                "",
                "## Baseline Scores",
                "",
                f"- Trust: {baselines.get('trust_score')}",
                f"- Intent: {baselines.get('intent_score')}",
                f"- Darija comprehension: {baselines.get('darija_comprehension_score')}",
                f"- Conversation classifier: {baselines.get('conversation_classifier_score')}",
                f"- API contract: {baselines.get('api_contract_passed')}",
            ]
        )
    lines.extend(
        [
            "",
            "The runner stopped at this gate. No unsafe legal-content fix was applied.",
        ]
    )
    BLOCKED_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_progressive_report(phase_records: list[dict[str, Any]]) -> None:
    all_fixes = [
        fix
        for record in phase_records
        for fix in record.get("fixes_applied", [])
    ]
    final_record = phase_records[-1] if phase_records else {}
    final_baselines = final_record.get("baselines") or {}
    all_gates_passed = bool(phase_records) and all(
        record.get("gate_passed") for record in phase_records
    )
    reached_500 = any(
        record.get("phase") == 500 and record.get("gate_passed")
        for record in phase_records
    )
    recommendation = (
        "READY_FOR_PRIVATE_BETA"
        if all_gates_passed and reached_500
        else "NEEDS_MORE_WORK"
    )

    lines = [
        "# Progressive Stress Report",
        "",
        "## Phase Results",
        "",
    ]
    if not phase_records:
        lines.append("- No completed phases.")
    for record in phase_records:
        stress = record["stress"]
        lines.extend(
            [
                f"### {record['phase']} Cases",
                "",
                f"- Attempts: {record['attempts']}",
                f"- Pass rate: {float(stress.get('pass_rate') or 0):.2%}",
                f"- Passed: {stress.get('passed')}/{stress.get('total')}",
                f"- Average latency: {float(stress.get('average_latency_ms') or 0):.0f} ms",
                f"- Median latency: {float(stress.get('median_latency_ms') or 0):.0f} ms",
                f"- Max latency: {float(stress.get('max_latency_ms') or 0):.0f} ms",
                f"- Gate: {'PASS' if record.get('gate_passed') else 'BLOCKED'}",
                "- Failures by type: "
                + json.dumps(
                    stress.get("failures_by_type", {}),
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "",
            ]
        )

    lines.extend(["## Fixes Applied", ""])
    if all_fixes:
        for fix in all_fixes:
            lines.append(
                f"- {fix['name']}: {fix['description']} "
                f"(files: {', '.join(fix['files_modified'])})"
            )
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Final Baselines",
            "",
            f"- Trust score: {final_baselines.get('trust_score')}",
            f"- Intent score: {final_baselines.get('intent_score')}",
            f"- Darija comprehension: {final_baselines.get('darija_comprehension_score')}",
            f"- Conversation classifier: {final_baselines.get('conversation_classifier_score')}",
            f"- API contract: {final_baselines.get('api_contract_passed')}",
            "",
            "## Final Recommendation",
            "",
            f"**{recommendation}**",
        ]
    )
    PROGRESSIVE_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-phase",
        type=int,
        choices=PHASES,
        default=500,
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--rerun-failures",
        action="store_true",
        help="When resuming, rerun failed stress cases instead of reusing them.",
    )
    parser.add_argument(
        "--no-auto-fix",
        action="store_true",
        help="Run and gate phases without applying predeclared safe fixes.",
    )
    parser.add_argument(
        "--max-fix-groups-per-phase",
        type=int,
        default=7,
    )
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    if BLOCKED_REPORT_PATH.exists():
        BLOCKED_REPORT_PATH.unlink()

    selected_phases = [phase for phase in PHASES if phase <= args.max_phase]
    phase_records: list[dict[str, Any]] = []
    existing_fix_records = read_jsonl(FIX_LOG_PATH)
    fixes_already_applied = {
        str(row.get("name"))
        for row in existing_fix_records
        if row.get("name")
    }

    for phase in selected_phases:
        run_dir = RUNS_DIR / f"run_{phase}"
        run_dir.mkdir(parents=True, exist_ok=True)
        phase_summary_path = run_dir / "phase_summary.json"
        if args.resume and phase_summary_path.exists():
            previous_record = json.loads(
                phase_summary_path.read_text(encoding="utf-8")
            )
            if previous_record.get("gate_passed"):
                print(f"Phase {phase} already passed; reusing its checkpoint.")
                phase_records.append(previous_record)
                continue

        fixes_for_phase = [
            row for row in existing_fix_records if row.get("phase") == phase
        ]
        attempt = 1

        while True:
            print(f"\n=== Phase {phase}, attempt {attempt} ===")
            stress, command = run_stress_phase(
                phase,
                run_dir,
                resume=args.resume and attempt == 1,
                rerun_failures=args.rerun_failures and attempt == 1,
            )
            results = read_jsonl(run_dir / "results.jsonl")
            archive_attempt(run_dir, attempt)
            record_manual_review(phase, attempt, results)

            if command["return_code"] != 0 or not stress["complete"]:
                reasons = [
                    f"stress command returned {command['return_code']}",
                    f"completed {stress['total']}/{phase} cases",
                ]
                write_blocked_report(
                    phase,
                    attempt,
                    stress,
                    None,
                    reasons,
                    fixes_for_phase,
                )
                phase_records.append(
                    {
                        "phase": phase,
                        "attempts": attempt,
                        "stress": stress,
                        "baselines": None,
                        "gate_passed": False,
                        "fixes_applied": fixes_for_phase,
                    }
                )
                write_progressive_report(phase_records)
                return 1

            fix = None
            if not args.no_auto_fix:
                fix = choose_safe_fix(results, fixes_already_applied)
            if (
                fix is not None
                and len(fixes_for_phase) < args.max_fix_groups_per_phase
            ):
                files_modified = fix.apply()
                if files_modified:
                    fix_record = {
                        "phase": phase,
                        "attempt": attempt,
                        "name": fix.name,
                        "description": fix.description,
                        "failure_types": list(fix.failure_types),
                        "files_modified": files_modified,
                        "applied_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    append_jsonl(FIX_LOG_PATH, fix_record)
                    fixes_for_phase.append(fix_record)
                    fixes_already_applied.add(fix.name)
                    print(f"Applied safe fix group: {fix.name}")
                    attempt += 1
                    continue

            print("Running baseline gates...")
            baselines = run_baselines(run_dir)
            gate_passed, reasons = gate_decision(phase, stress, baselines)
            phase_record = {
                "phase": phase,
                "attempts": attempt,
                "stress": stress,
                "baselines": baselines,
                "gate_passed": gate_passed,
                "gate_reasons": reasons,
                "fixes_applied": fixes_for_phase,
            }
            phase_records.append(phase_record)
            write_json(run_dir / "phase_summary.json", phase_record)
            write_progressive_report(phase_records)

            if not gate_passed:
                write_blocked_report(
                    phase,
                    attempt,
                    stress,
                    baselines,
                    reasons,
                    fixes_for_phase,
                )
                print(f"Phase {phase} blocked: {'; '.join(reasons)}")
                return 1

            print(f"Phase {phase} passed all gates.")
            break

    write_progressive_report(phase_records)
    print(f"Progressive report: {PROGRESSIVE_REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
