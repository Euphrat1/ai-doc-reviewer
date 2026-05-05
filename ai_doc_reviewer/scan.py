from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ALLOWED_EXTS = {
    ".txt",
    ".md",
    ".csv",
    ".xlsx",
    ".xml",
    ".bpmn",
    ".drawio",
    ".png",
    ".jpg",
    ".pdf",
}


@dataclass(frozen=True)
class ScannedFile:
    abs_path: str
    rel_path: str
    ext: str
    size_bytes: int


def scan_folder(folder: str) -> list[ScannedFile]:
    root = Path(folder).resolve()
    out: list[ScannedFile] = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            p = Path(dirpath) / name
            ext = p.suffix.lower()
            if ext not in ALLOWED_EXTS:
                continue
            try:
                size = p.stat().st_size
            except OSError:
                size = 0
            rel = str(p.resolve().relative_to(root)).replace("\\", "/")
            out.append(
                ScannedFile(
                    abs_path=str(p),
                    rel_path=rel,
                    ext=ext,
                    size_bytes=int(size),
                )
            )
    out.sort(key=lambda x: x.rel_path)
    return out

