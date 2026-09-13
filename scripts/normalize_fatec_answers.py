from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

QUESTION_COUNT_RE = re.compile(r"cont[eé]m\s+(\d{1,3})\s*\([^)]*\)\s*quest", re.IGNORECASE)
ANSWER_RE = re.compile(r"(?<!\d)(\d{1,3})\s*:?\s+([A-E])\b", re.IGNORECASE)


def pdf_text(path: Path, first_pages_only: bool = False) -> str:
    command = ["pdftotext", "-layout"]
    if first_pages_only:
        command += ["-f", "1", "-l", "2"]
    command += [str(path), "-"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"pdftotext failed for {path}: {result.stderr.strip()}")
    return result.stdout


def select_variant(text: str, variant: str | None) -> str:
    if not variant:
        return text
    upper = text.upper()
    marker = f"PROVA TIPO {variant.upper()}"
    start = upper.find(marker)
    if start == -1:
        raise RuntimeError(f"could not find {marker} in answer key")
    next_marker = "PROVA TIPO B" if variant.upper() == "A" else None
    if next_marker:
        end = upper.find(next_marker, start + len(marker))
        if end != -1:
            return text[start:end]
    return text[start:]


def parse_answers(text: str, expected: int) -> dict[int, str]:
    answers: dict[int, str] = {}
    for line in text.splitlines():
        for match in ANSWER_RE.finditer(line):
            number = int(match.group(1))
            if number < 1 or number > expected:
                continue
            answer = match.group(2).upper()
            previous = answers.get(number)
            if previous and previous != answer:
                raise RuntimeError(f"conflicting answers for question {number}: {previous}/{answer}")
            answers[number] = answer

    missing = [number for number in range(1, expected + 1) if number not in answers]
    if missing:
        raise RuntimeError(f"missing answers: {missing}")
    if len(answers) != expected:
        raise RuntimeError(f"expected {expected} answers, got {len(answers)}")
    return answers


def expected_count(exam_pdf: Path) -> int:
    text = pdf_text(exam_pdf, first_pages_only=True)
    match = QUESTION_COUNT_RE.search(text)
    if not match:
        raise RuntimeError(f"could not determine question count from {exam_pdf}")
    return int(match.group(1))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sanitized-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.sanitized_dir.resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    normalized: list[dict] = []

    for entry in manifest["accepted"]:
        edition = entry["edition"]
        files = {item["role"]: root / item["path"] for item in entry["files"]}
        exam_pdf = files["exam"]
        key_pdf = files["answer-key"]
        count = expected_count(exam_pdf)
        variant = "A" if edition == "2025.1" else None
        key_text = select_variant(pdf_text(key_pdf), variant)
        answers = parse_answers(key_text, count)

        normalized.append(
            {
                "edition_id": edition,
                "year": int(edition.split(".")[0]),
                "phase": "single",
                "variant": variant,
                "expected_questions": count,
                "allowed_letters": ["A", "B", "C", "D", "E"],
                "answer_key_status": "final",
                "answer_key": {str(number): answers[number] for number in range(1, count + 1)},
                "files": entry["files"],
                "ignored_extras": entry.get("ignored_extras", []),
            }
        )

    payload = {
        "schema_version": 1,
        "provider_id": "fatec",
        "source": manifest["source"],
        "source_sha256": manifest["source_sha256"],
        "statement_mode": "reference-only",
        "response_model": "single-choice",
        "editions": normalized,
        "blocked": manifest["blocked"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "editions": len(normalized),
        "questions": sum(item["expected_questions"] for item in normalized),
        "blocked": len(payload["blocked"]),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
