from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import time
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources"


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_manifests() -> list[tuple[Path, dict[str, Any]]]:
    manifests: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(SOURCES.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or not isinstance(data.get("collections"), list):
            raise RuntimeError(f"invalid source manifest: {path}")
        manifests.append((path, data))
    if not manifests:
        raise RuntimeError("no source manifests found")
    return manifests


def merged_collections(manifests: list[tuple[Path, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for manifest_path, manifest in manifests:
        for collection in manifest["collections"]:
            slug = str(collection.get("id") or "").strip()
            if not slug:
                raise RuntimeError(f"collection without id: {manifest_path}")
            current = merged.setdefault(
                slug,
                {
                    "id": slug,
                    "display_name": collection.get("display_name") or slug.upper(),
                    "exams": [],
                    "source_manifests": [],
                    "source_labels": [],
                },
            )
            current["exams"].extend(collection.get("exams", []))
            current["source_manifests"].append(str(manifest_path.relative_to(ROOT)))
            if manifest.get("source"):
                current["source_labels"].append(str(manifest["source"]))
    return merged


def eear_bucket(year: int) -> str:
    if year >= 2023:
        return "eear-2023-2025"
    if year >= 2020:
        return "eear-2020-2022"
    return "eear-pre2020"


def packages_for(collections: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    packages: list[dict[str, Any]] = []
    for collection in collections.values():
        slug = collection["id"]
        exams = list(collection["exams"])
        if slug == "eear":
            groups: dict[str, list[dict[str, Any]]] = {}
            for exam in exams:
                groups.setdefault(eear_bucket(int(exam["year"])), []).append(exam)
            for package_id, group in sorted(groups.items()):
                packages.append({**collection, "package_id": package_id, "exams": group})
            continue
        if slug == "esa":
            # Compatibilidade com o release histórico: apenas ESA Geral entra neste pacote.
            exams = [exam for exam in exams if "geral" in str(exam.get("label", "")).lower()]
        packages.append({**collection, "package_id": slug, "exams": exams})
    return sorted(packages, key=lambda item: item["package_id"])


def make_opener() -> urllib.request.OpenerDirector:
    opener = urllib.request.build_opener()
    opener.addheaders = [
        ("User-Agent", "Mozilla/5.0 (compatible; StudiumLabsCorpus/1.0; +https://github.com/macielhgustavo/enemlab-corpus)"),
        ("Accept", "application/pdf,*/*;q=0.8"),
    ]
    return opener


def download(opener: urllib.request.OpenerDirector, url: str, dest: Path) -> tuple[str, int]:
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with opener.open(url, timeout=60) as response, dest.open("wb") as out:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
            raw = dest.read_bytes()
            if len(raw) < 1024 or not raw.startswith(b"%PDF"):
                raise RuntimeError(f"response is not a valid PDF ({len(raw)} bytes)")
            return sha256_bytes(raw), len(raw)
        except Exception as exc:  # diagnostic boundary: record exact URL/package later
            last_error = exc
            dest.unlink(missing_ok=True)
            if attempt < 3:
                time.sleep(2**attempt)
    raise RuntimeError(f"{url}: {last_error}")


def build_one(package: dict[str, Any], work_root: Path, output_dir: Path) -> dict[str, Any]:
    package_id = package["package_id"]
    collection_dir = work_root / package_id
    collection_dir.mkdir(parents=True, exist_ok=True)
    opener = make_opener()
    resolved: list[dict[str, Any]] = []
    seen_filenames: set[str] = set()

    for exam in sorted(package["exams"], key=lambda item: (int(item["year"]), str(item.get("label", "")))):
        files = exam.get("files")
        if not isinstance(files, list) or not files:
            raise RuntimeError(f"{package_id}: exam has no files: {exam.get('label')}")
        resolved_exam = {key: value for key, value in exam.items() if key != "files"}
        resolved_files: list[dict[str, Any]] = []
        for item in files:
            filename = str(item.get("filename") or "").strip()
            url = str(item.get("url") or "").strip()
            if not filename or not url:
                raise RuntimeError(f"{package_id}: invalid file entry in {exam.get('label')}")
            if filename in seen_filenames:
                raise RuntimeError(f"{package_id}: duplicate filename: {filename}")
            seen_filenames.add(filename)
            dest = collection_dir / filename
            try:
                digest, size = download(opener, url, dest)
            except Exception as exc:
                raise RuntimeError(
                    f"package={package_id} exam={exam.get('label')} file={filename} download failed: {exc}"
                ) from exc
            resolved_files.append({**item, "sha256": digest, "size_bytes": size})
            print(f"OK package={package_id} file={filename} bytes={size} sha256={digest}", flush=True)
        resolved_exam["files"] = resolved_files
        resolved.append(resolved_exam)

    manifest = {
        "schema_version": 1,
        "package_id": package_id,
        "collection": package["id"],
        "display_name": package["display_name"],
        "source": " + ".join(sorted(set(package.get("source_labels", [])))) or "mixed",
        "generated_from": package["source_manifests"],
        "exams": resolved,
    }
    (collection_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    sums = [
        f"{sha256_bytes(path.read_bytes())}  {path.name}"
        for path in sorted(collection_dir.glob("*.pdf"))
    ]
    (collection_dir / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")

    archive_base = output_dir / package_id
    zip_path = Path(shutil.make_archive(str(archive_base), "zip", root_dir=collection_dir))
    if zip_path.stat().st_size >= 95 * 1024 * 1024:
        zip_path.unlink(missing_ok=True)
        raise RuntimeError(f"{package_id}: package reached 95 MiB; split it")
    return {
        "asset": zip_path.name,
        "collection": package["id"],
        "exams": len(resolved),
        "pdfs": sum(len(exam["files"]) for exam in resolved),
        "size_bytes": zip_path.stat().st_size,
        "sha256": sha256_bytes(zip_path.read_bytes()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / ".cache" / "corpus-build")
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    work_root = output_dir / "work"
    shutil.rmtree(output_dir, ignore_errors=True)
    work_root.mkdir(parents=True, exist_ok=True)

    manifests = load_manifests()
    packages = packages_for(merged_collections(manifests))
    built: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for package in packages:
        package_id = package["package_id"]
        print(f"BUILD package={package_id}", flush=True)
        try:
            built.append(build_one(package, work_root, output_dir))
        except Exception as exc:
            failures.append({"package_id": package_id, "error": str(exc)})
            print(f"FAIL package={package_id}: {exc}", flush=True)

    release_index = {
        "schema_version": 1,
        "release_tag": "corpus-latest",
        "source_commit": os.environ.get("GITHUB_SHA"),
        "source_manifests": [str(path.relative_to(ROOT)) for path, _ in manifests],
        "assets": built,
        "failures": failures,
    }
    (output_dir / "corpus-release.json").write_text(
        json.dumps(release_index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(release_index, ensure_ascii=False, indent=2), flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
