from __future__ import annotations

import argparse
import hashlib
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


def inspect(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    try:
        with ZipFile(path) as archive:
            files = [item for item in archive.infolist() if not item.is_dir()]
            extensions = Counter(Path(item.filename).suffix.lower() or "<none>" for item in files)
            return {
                "file": path.name,
                "size_bytes": path.stat().st_size,
                "sha256": digest(path),
                "entries": len(files),
                "extensions": dict(sorted(extensions.items())),
                "uncompressed_bytes": sum(item.file_size for item in files),
                "names": [item.filename for item in files],
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
