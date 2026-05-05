from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import pandas as pd
from PIL import Image
from pypdf import PdfReader

from .scan import ScannedFile
from .tokens import estimate_tokens, normalize_text
from .types import FullCorpus, FullFile, ParseStatus, TokenEst


def _read_text_file(path: str) -> str:
    raw = Path(path).read_bytes()
    for enc in ("utf-8", "utf-8-sig", "cp1251"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")


def _token_est(structure: str, evidence: str, k: float) -> TokenEst:
    ts = estimate_tokens(structure, k)
    te = estimate_tokens(evidence, k)
    return {"structure": ts, "evidence": te, "total": ts + te}


def _parse_xml_like(text: str) -> tuple[str, str, ParseStatus]:
    try:
        root = ET.fromstring(text)
    except Exception as e:
        return (f"PARSE_ERROR: {type(e).__name__}: {e}", "", "fail")

    tag_counts: dict[str, int] = {}
    texts: list[str] = []
    for el in root.iter():
        tag_counts[el.tag] = tag_counts.get(el.tag, 0) + 1
        if el.text and el.text.strip():
            t = " ".join(el.text.split())
            if t:
                texts.append(t)

    top_tags = sorted(tag_counts.items(), key=lambda kv: kv[1], reverse=True)[:20]
    structure = "ROOT: " + root.tag + "\n" + "TOP_TAGS: " + ", ".join(
        f"{k}({v})" for k, v in top_tags
    )
    evidence = "\n".join(texts[:200])
    return (structure, evidence, "ok")


def parse_file(sf: ScannedFile, *, k: float, pdf_pages_max: int) -> tuple[FullFile, dict[str, Any]]:
    """
    Returns (full_file, type_meta minimal for compression transparency).
    type_meta is internal; it is used to populate pdf_included_pages/table_included_ranges.
    """
    structure = ""
    evidence = ""
    status: ParseStatus = "ok"
    type_meta: dict[str, Any] = {"pdf_pages_included": None, "table_ranges": None}

    try:
        if sf.ext in (".txt", ".md"):
            txt = normalize_text(_read_text_file(sf.abs_path))
            structure = "TYPE: text"
            evidence = txt

        elif sf.ext == ".csv":
            txt = _read_text_file(sf.abs_path)
            f = io.StringIO(txt)
            reader = csv.reader(f)
            rows = list(reader)
            cols = rows[0] if rows else []
            structure = f"COLS: {', '.join(cols[:50])}\nROWS: {max(len(rows)-1, 0)}"
            head = rows[: min(len(rows), 201)]
            buf = io.StringIO()
            w = csv.writer(buf)
            for r in head:
                w.writerow(r)
            evidence = buf.getvalue()
            type_meta["table_ranges"] = ["first 200 rows"]

        elif sf.ext == ".xlsx":
            xls = pd.ExcelFile(sf.abs_path)
            sheets = xls.sheet_names
            structure = "SHEETS: " + ", ".join(sheets[:50])
            # MVP: parse first sheet fully enough for evidence
            df = pd.read_excel(sf.abs_path, sheet_name=sheets[0] if sheets else 0)
            evidence = df.head(200).to_csv(index=False)
            type_meta["table_ranges"] = ["first 200 rows (sheet 1)"]
            if len(sheets) > 1:
                status = "warn"
                structure += "\nWARN: multiple sheets; MVP evidence uses first sheet only"

        elif sf.ext in (".xml", ".bpmn", ".drawio"):
            txt = _read_text_file(sf.abs_path)
            structure, evidence, status = _parse_xml_like(txt)
            if sf.ext in (".bpmn", ".drawio") and status == "fail":
                # best-effort: already fail
                pass

        elif sf.ext == ".pdf":
            reader = PdfReader(sf.abs_path)
            total_pages = len(reader.pages)
            pages = list(range(1, min(total_pages, max(pdf_pages_max, 1)) + 1))
            type_meta["pdf_pages_included"] = pages
            structure = f"PAGES: {total_pages}"
            parts: list[str] = []
            for i in pages:
                page = reader.pages[i - 1]
                t = page.extract_text() or ""
                t = normalize_text(t).strip()
                parts.append(f"PDF_TEXT p.{i}:\n{t}")
            evidence = "\n\n".join(parts).strip()
            if not evidence:
                status = "warn"
                structure += "\nWARN: no extractable text (OCR may be needed)"

        elif sf.ext in (".png", ".jpg"):
            img = Image.open(sf.abs_path)
            structure = f"IMAGE: {img.width}x{img.height}"
            evidence = ""

        else:
            status = "fail"
            structure = f"PARSE_ERROR: unsupported ext {sf.ext}"
            evidence = ""

    except Exception as e:
        status = "fail"
        structure = f"PARSE_ERROR: {type(e).__name__}: {e}"
        evidence = ""

    structure = normalize_text(structure).strip()
    evidence = normalize_text(evidence).strip()
    tokens = _token_est(structure, evidence, k)

    full: FullFile = {
        "rel_path": sf.rel_path,
        "ext": sf.ext,
        "size_bytes": sf.size_bytes,
        "parse": status,
        "structure_text": structure,
        "evidence_text": evidence,
        "tokens_full_est": tokens,
    }
    return full, type_meta


def build_full_corpus(
    scanned: list[ScannedFile], *, k: float, pdf_pages_max: int
) -> tuple[FullCorpus, dict[str, dict[str, Any]]]:
    files: list[FullFile] = []
    meta_by_path: dict[str, dict[str, Any]] = {}
    for sf in scanned:
        ff, meta = parse_file(sf, k=k, pdf_pages_max=pdf_pages_max)
        files.append(ff)
        meta_by_path[ff["rel_path"]] = meta

    total = sum(f["tokens_full_est"]["total"] for f in files)
    corpus: FullCorpus = {
        "token_estimation": {"k": float(k)},
        "files": files,
        "tokens_full_corpus_est": int(total),
    }
    return corpus, meta_by_path

