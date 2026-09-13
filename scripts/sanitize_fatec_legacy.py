from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

EDITION_ARCHIVES = {
    "2022.2": "prova-e-gabarito-fatecs-2022-2.rar",
    "2023.1": "provas-e-gabaritos-fatecs-2023-1.zip",
    "2023.2": "prova-e-gabarito-fatecs-2023-2.rar",
    "2024.1": "provas-e-gabaritos-fatecs-2024-1.zip",
    "2024.2": "provas-e-gabaritos-fatecs-2024-2.zip",
    "2025.1": "provas-e-gabaritos-fatec-2025-1.zip",
    "2025.2": "provas-e-gabaritos-fatec-20252.zip",
    "2026.1": "provas-e-gabaritos-fatec-2026.zip",
    "2026.2": "provas-e-gabaritos-fatec-20262.zip",
}

BLOCKED_EDITIONS = {
    "2024.1": "legacy archive contains a FATEC answer key but the supposed exam PDF is a SISU/UFC document",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def seven_zip_extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["7z", "x", "-y", str(archive), f"-o{destination}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"7z failed for {archive.name}: {result.stderr.strip() or result.stdout.strip()}")


def pdfs_under(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.pdf") if path.is_file())


def is_pdf(path: Path) -> bool:
    return path.stat().st_size >= 1024 and path.read_bytes()[:4] == b"%PDF"


def classify_documents(paths: list[Path]) -> tuple[Path | None, Path | None, list[Path]]:
    valid = [path for path in paths if is_pdf(path)]
    answer_keys = [path for path in valid if "gabarito" in path.name.lower()]
    exams = [
        path
        for path in valid
        if "prova" in path.name.lower()
        and "gabarito" not in path.name.lower()
        and "prouni" not in path.name.lower()
    ]
    extras = [path for path in valid if path not in answer_keys and path not in exams]
    exam = exams[0] if len(exams) == 1 else None
    answer_key = answer_keys[0] if len(answer_keys) == 1 else None
    return exam, answer_key, extras


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("fatec.zip"))
    parser.add_argument("--output-dir", type=Path, default=Path(".cache/fatec-sanitized"))
    args = parser.parse_args()

    source = args.input.resolve()
    output = args.output_dir.resolve()
    work = output / "work"
    shutil.rmtree(output, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)

    outer = work / "outer"
    seven_zip_extract(source, outer)
    archives = {path.name: path for path in outer.rglob("*") if path.is_file()}

    accepted: list[dict] = []
    blocked: list[dict] = []

    clean_root = output / "documents"
    clean_root.mkdir(parents=True, exist_ok=True)

    for edition, archive_name in EDITION_ARCHIVES.items():
        nested = archives.get(archive_name)
        if not nested:
            blocked.append({"edition": edition, "reason": f"missing nested archive: {archive_name}"})
            continue
        if edition in BLOCKED_EDITIONS:
            blocked.append({"edition": edition, "archive": archive_name, "reason": BLOCKED_EDITIONS[edition]})
            continue

        extracted = work / edition
        try:
            seven_zip_extract(nested, extracted)
        except Exception as exc:
            blocked.append({"edition": edition, "archive": archive_name, "reason": str(exc)})
            continue

        exam, answer_key, extras = classify_documents(pdfs_under(extracted))
        if not exam or not answer_key:
            blocked.append({
                "edition": edition,
                "archive": archive_name,
                "reason": "could not prove exactly one exam PDF and one answer-key PDF",
                "pdfs": [path.name for path in pdfs_under(extracted)],
            })
            continue

        edition_dir = clean_root / edition
        edition_dir.mkdir(parents=True, exist_ok=True)
        exam_out = edition_dir / f"fatec-{edition}-prova.pdf"
        key_out = edition_dir / f"fatec-{edition}-gabarito.pdf"
        shutil.copy2(exam, exam_out)
        shutil.copy2(answer_key, key_out)

        accepted.append({
            "edition": edition,
            "source_archive": archive_name,
            "files": [
                {"role": "exam", "path": str(exam_out.relative_to(output)), "sha256": sha256(exam_out), "size_bytes": exam_out.stat().st_size},
                {"role": "answer-key", "path": str(key_out.relative_to(output)), "sha256": sha256(key_out), "size_bytes": key_out.stat().st_size},
            ],
            "ignored_extras": [path.name for path in extras],
        })

    manifest = {
        "schema_version": 1,
        "source": "repository legacy fatec.zip",
        "source_sha256": sha256(source),
        "policy": "accept only editions with exactly one valid exam PDF and one valid answer-key PDF",
        "accepted": accepted,
        "blocked": blocked,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    archive_base = output.parent / "fatec-sanitized"
    shutil.make_archive(str(archive_base), "zip", root_dir=output, base_dir="documents")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 1 if any(item["edition"] != "2024.1" for item in blocked) else 0


if __name__ == "__main__":
    raise SystemExit(main())
