import argparse
import json
import re
import sys
from pathlib import Path

import requests

from rag import INSUFFICIENT_CONTEXT_MESSAGE, ask_chatbot

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CASES_PATH = BASE_DIR / "eval_cases.jsonl"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def load_cases(path: Path):
    cases = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on {path}:{line_number}") from exc
    return cases


def has_source_citation(answer: str, min_sources: int) -> bool:
    if min_sources <= 0:
        return True
    citations = re.findall(r"\[المصدر\s+\d+،\s+الصفحة\s+[^\]]+\]", answer)
    return len(set(citations)) >= min_sources


def score_case(case: dict, answer: str):
    normalized_answer = normalize(answer)
    failures = []

    for term in case.get("required_terms", []):
        if normalize(term) not in normalized_answer:
            failures.append(f"missing required term: {term}")

    for term in case.get("forbidden_terms", []):
        if normalize(term) in normalized_answer:
            failures.append(f"contains forbidden term: {term}")

    if case.get("expect_refusal"):
        refusal_markers = [
            normalize(INSUFFICIENT_CONTEXT_MESSAGE),
            "خارج",
            "ماشي فاختصاص",
            "محدود",
        ]
        if not any(marker in normalized_answer for marker in refusal_markers):
            failures.append("expected a refusal or insufficient-context answer")

    if not has_source_citation(answer, int(case.get("min_sources", 1))):
        failures.append("missing source citation")

    return failures


def main():
    parser = argparse.ArgumentParser(
        description="Run a trust evaluation set against the local legal RAG chatbot."
    )
    parser.add_argument("--cases", default=str(DEFAULT_CASES_PATH))
    parser.add_argument("--n-results", type=int, default=None)
    parser.add_argument("--report", default=None)
    args = parser.parse_args()

    cases = load_cases(Path(args.cases))
    results = []
    passed = 0

    for case in cases:
        question = case["question"]
        print(f"\n[{case['id']}] {question}")

        try:
            if args.n_results is None:
                answer, sources = ask_chatbot(question, return_sources=True)
            else:
                answer, sources = ask_chatbot(
                    question,
                    n_results=args.n_results,
                    return_sources=True,
                )
        except requests.exceptions.ConnectionError:
            print("\nOllama is not running on localhost:11434.")
            print("Start it with: ollama serve")
            return 2
        except requests.exceptions.Timeout:
            print("\nOllama timed out while evaluating this case.")
            print("Try a smaller chat model or fewer retrieval results.")
            return 2

        failures = score_case(case, answer)
        ok = not failures
        passed += int(ok)

        print("PASS" if ok else "FAIL")
        if failures:
            for failure in failures:
                print(f"- {failure}")
        print("Sources:", ", ".join(f"p{s.page}" for s in sources) or "none")

        results.append(
            {
                "id": case["id"],
                "question": question,
                "passed": ok,
                "failures": failures,
                "answer": answer,
                "sources": [
                    {
                        "number": source.number,
                        "page": source.page,
                        "distance": source.distance,
                    }
                    for source in sources
                ],
            }
        )

    trust_score = passed / len(cases) if cases else 0
    print(f"\nTrust score: {passed}/{len(cases)} ({trust_score:.0%})")
    if trust_score < 0.90:
        print("Status: NOT TRUSTED YET. Add failures to eval_cases.jsonl and improve RAG.")
    else:
        print("Status: TRUSTED FOR THIS TEST SET. Keep adding real-world cases.")

    if args.report:
        report_path = Path(args.report)
        report_path.write_text(
            json.dumps(
                {
                    "passed": passed,
                    "total": len(cases),
                    "trust_score": trust_score,
                    "results": results,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"Report written to {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
