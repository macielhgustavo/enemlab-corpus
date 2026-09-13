from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources"


def load_source_manifests() -> list[tuple[Path, dict]]:
    out: list[tuple[Path, dict]] = []
    for path in sorted(SOURCES.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            raise RuntimeError(f"invalid manifest schema: {path}")
        if not isinstance(data.get("collections"), list):
            raise RuntimeError(f"missing collections: {path}")
        out.append((path, data))
    return out


def package_name(collection_id: str, year: int) -> str:
    if collection_id == "eear":
        if year >= 2023:
            return "eear-2023-2025"
        if year >= 2020:
            return "eear-2020-2022"
        return "eear-pre2020"
    return collection_id


def collect() -> dict:
    packages: dict[str, dict] = {}
    seen_identity: set[tuple[str, int, str]] = set()
    seen_url: set[str] = set()
    files = 0
    exams = 0
    warnings: list[str] = []

    for manifest_path, manifest in load_source_manifests():
        for collection in manifest["collections"]:
            cid = str(collection.get("id") or "").strip()
            if not cid:
                raise RuntimeError(f"collection without id: {manifest_path}")
            for exam in collection.get("exams", []):
                year = exam.get("year")
                label = str(exam.get("label") or "").strip()
                source_page = str(exam.get("source_page") or "").strip()
                if not isinstance(year, int) or not label or not source_page:
                    raise RuntimeError(f"invalid exam in {manifest_path}: {exam}")
                identity = (cid, year, label)
                if identity in seen_identity:
                    warnings.append(f"duplicate exam identity: {identity}")
                    continue
                seen_identity.add(identity)

                package = package_name(cid, year)
                bucket = packages.setdefault(package, {"collections": set(), "exams": 0, "files": 0, "years": set()})
                bucket["collections"].add(cid)
                bucket["exams"] += 1
                bucket["years"].add(year)
                exams += 1

                exam_files = exam.get("files")
                if not isinstance(exam_files, list) or not exam_files:
                    raise RuntimeError(f"exam without files: {identity}")
                local_names: set[str] = set()
                for item in exam_files:
                    filename = str(item.get("filename") or "").strip()
                    url = str(item.get("url") or "").strip()
                    kind = str(item.get("kind") or "").strip()
                    if not filename or not url or not kind:
                        raise RuntimeError(f"invalid file entry in {identity}: {item}")
                    if filename in local_names:
                        raise RuntimeError(f"duplicate filename in one exam: {filename}")
                    local_names.add(filename)
                    if url in seen_url:
                        warnings.append(f"reused document url: {url}")
                    seen_url.add(url)
                    bucket["files"] += 1
                    files += 1

    normalized = {
        name: {
            "collections": sorted(value["collections"]),
            "exams": value["exams"],
            "files": value["files"],
            "years": sorted(value["years"]),
        }
        for name, value in sorted(packages.items())
    }
    return {
        "schema_version": 1,
        "source_manifests": len(load_source_manifests()),
        "exams": exams,
        "files": files,
        "packages": normalized,
        "warnings": warnings,
    }


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def inspect_zip(path: Path) -> dict:
    with ZipFile(path) as archive:
        names = set(archive.namelist())
        if "manifest.json" not in names or "SHA256SUMS.txt" not in names:
            raise RuntimeError(f"{path.name}: missing manifest.json or SHA256SUMS.txt")
        manifest = json.loads(archive.read("manifest.json"))
        sums = {}
        for line in archive.read("SHA256SUMS.txt").decode("utf-8").splitlines():
            if not line.strip():
                continue
            digest, filename = line.split(None, 1)
            sums[filename.strip()] = digest.strip().lower()

        pdfs = sorted(name for name in names if name.lower().endswith(".pdf"))
        failures: list[str] = []
        for filename in pdfs:
            digest = sha256_bytes(archive.read(filename))
            expected = sums.get(filename)
            if expected != digest:
                failures.append(f"sha mismatch: {filename}")

        declared_files = sum(len(exam.get("files", [])) for exam in manifest.get("exams", []))
        if declared_files != len(pdfs):
            failures.append(f"manifest files={declared_files}, zip pdfs={len(pdfs)}")

        return {
            "asset": path.name,
            "package_id": manifest.get("package_id"),
            "collection": manifest.get("collection"),
            "exams": len(manifest.get("exams", [])),
            "pdfs": len(pdfs),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_bytes(path.read_bytes()),
            "failures": failures,
        }


def inspect_release(directory: Path, expected_packages: set[str]) -> list[dict]:
    results: list[dict] = []
    for package in sorted(expected_packages):
        path = directory / f"{package}.zip"
        if not path.exists():
            results.append({"asset": path.name, "missing": True})
            continue
        results.append(inspect_zip(path))
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", dest="json_path")
    parser.add_argument("--release-dir", type=Path)
    args = parser.parse_args()

    report = collect()
    if args.release_dir:
        report["release"] = inspect_release(args.release_dir, set(report["packages"]))

    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.json_path:
        Path(args.json_path).write_text(text + "\n", encoding="utf-8")

    release_failures = [
        item for item in report.get("release", [])
        if item.get("missing") or item.get("failures")
    ]
    return 1 if release_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
