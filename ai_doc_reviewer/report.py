from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .types import PromptCorpus


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_prompt_corpus_summary(prompt: PromptCorpus) -> dict[str, Any]:
    trimmed = []
    removed = []
    pdf_pages = []
    table_ranges = []

    for f in prompt["files"]:
        c = f["compression"]
        before = int(c.get("evidence_before_tokens_est", 0))
        after = int(c.get("evidence_after_tokens_est", 0))
        if after == 0 and bool(c.get("evidence_removed", False)):
            removed.append(f["rel_path"])
        elif after < before:
            trimmed.append(
                {
                    "rel_path": f["rel_path"],
                    "evidence_before_tokens_est": before,
                    "evidence_after_tokens_est": after,
                }
            )

        if c.get("pdf_included_pages") is not None:
            pdf_pages.append(
                {"rel_path": f["rel_path"], "included_pages": c.get("pdf_included_pages")}
            )
        if c.get("table_included_ranges") is not None:
            table_ranges.append(
                {"rel_path": f["rel_path"], "ranges": c.get("table_included_ranges")}
            )

    return {
        "evidence_trimmed_files": trimmed,
        "evidence_removed_files": removed,
        "pdf_included_pages": pdf_pages,
        "table_included_ranges": table_ranges,
    }

