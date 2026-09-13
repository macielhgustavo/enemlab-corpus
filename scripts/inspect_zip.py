from __future__ import annotations

import argparse
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from zipfile import BadZipFile, ZipFile


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def archive_summary(archive: ZipFile) -> dict:
    files = [item for item in archive.infolist() if not item.is_dir()]
    extensions = Counter(Path(item.filename).suffix.lower() or "<none>" for item in files)
    return {
        "entries": len(files),
        "extensions": dict(sorted(extensions.items())),
        "uncompressed_bytes": sum(item.file_size for item in files),
        "names": [item.filename for item in files],
    }


def nested_archives(archive: ZipFile) -> list[dict]:
    nested: list[dict] = []
    for item in archive.infolist():
        if item.is_dir():
            continue
        suffix = Path(item.filename).suffix.lower()
        if suffix == ".zip":
            raw = archive.read(item)
            try:
                with ZipFile(io.BytesIO(raw)) as child:
                    nested.append({
                        "name": item.filename,
                        "format": "zip",
                        "inspectable": True,
                        **archive_summary(child),
                    })
            except BadZipFile:
                nested.append({
                    "name": item.filename,
                    "format": "zip",
                    "inspectable": False,
                    "error": "invalid nested zip",
                })
        elif suffix == ".rar":
            nested.append({
                "name": item.filename,
                "format": "rar",
                "inspectable": False,
                "reason": "RAR is not parsed by Python stdlib",
            })
    return nested


def inspect(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    try:
        with ZipFile(path) as archive:
            return {
                "file": path.name,
                "size_bytes": path.stat().st_size,
                "sha256": digest(path),
                **archive_summary(archive),
                "nested_archives": nested_archives(archive),
            }
    except BadZipFile as exc:
        raise RuntimeError(f"invalid zip: {path}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip", type=Path)
    parser.add_argument("--json", dest="json_path")
    args = parser.parse_args()
    report = inspect(args.zip)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.json_path:
        Path(args.json_path).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
