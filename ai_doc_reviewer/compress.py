from __future__ import annotations

from typing import Any

from .tokens import estimate_tokens
from .types import FullCorpus, PromptCorpus, PromptFile, TokenEst


def _trim_to_tokens(text: str, *, k: float, max_tokens: int) -> str:
    if max_tokens <= 0:
        return ""
    # MVP: approximate by chars; cut by proportion.
    max_chars = int(max_tokens * k)
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def _est(structure: str, evidence: str, k: float) -> TokenEst:
    ts = estimate_tokens(structure, k)
    te = estimate_tokens(evidence, k)
    return {"structure": ts, "evidence": te, "total": ts + te}


def build_prompt_corpus_mvp(
    full: FullCorpus,
    *,
    prompt_budget_tokens: int,
    per_file_structure_tokens: int,
    per_file_evidence_tokens: int,
    pdf_evidence_pages_max: int,
    evidence_keep_first_n_files: int,
    k: float,
    instructions_tokens_est: int,
    task_tokens_est: int,
    meta_by_path: dict[str, dict[str, Any]] | None = None,
) -> PromptCorpus:
    """
    MVP policy (tech_req.md F1.3.MVP):
    - STRUCTURE always (trimmed)
    - EVIDENCE only for first N files; if budget exceeded, reduce N
    - For pdf: we already limited pages at parse-time; we only report included pages here.
    """
    meta_by_path = meta_by_path or {}
    files_full = full["files"]

    def build_with_n(n: int) -> tuple[list[PromptFile], int]:
        prompt_files: list[PromptFile] = []
        for idx, f in enumerate(files_full):
            structure = _trim_to_tokens(
                f["structure_text"], k=k, max_tokens=per_file_structure_tokens
            )
            evidence_before = estimate_tokens(f["evidence_text"], k)
            evidence = ""
            removed = True
            if idx < n:
                evidence = _trim_to_tokens(
                    f["evidence_text"], k=k, max_tokens=per_file_evidence_tokens
                )
                removed = False
            evidence_after = estimate_tokens(evidence, k)
            tokens = _est(structure, evidence, k)

            meta = meta_by_path.get(f["rel_path"], {})
            pdf_pages = meta.get("pdf_pages_included")
            table_ranges = meta.get("table_ranges")

            prompt_files.append(
                {
                    "rel_path": f["rel_path"],
                    "structure_text": structure,
                    "evidence_text": evidence,
                    "tokens_prompt_est": tokens,
                    "compression": {
                        "evidence_before_tokens_est": int(evidence_before),
                        "evidence_after_tokens_est": int(evidence_after),
                        "evidence_removed": bool(removed),
                        "pdf_included_pages": pdf_pages if pdf_pages is not None else None,
                        "table_included_ranges": table_ranges
                        if table_ranges is not None
                        else None,
                    },
                }
            )

        corpus_tokens = sum(pf["tokens_prompt_est"]["total"] for pf in prompt_files)
        total_tokens = int(instructions_tokens_est + task_tokens_est + corpus_tokens)
        return prompt_files, total_tokens

    n = max(int(evidence_keep_first_n_files), 0)
    if n > len(files_full):
        n = len(files_full)

    prompt_files, total = build_with_n(n)
    while total > prompt_budget_tokens and n > 0:
        n -= 1
        prompt_files, total = build_with_n(n)

    corpus_tokens = sum(pf["tokens_prompt_est"]["total"] for pf in prompt_files)
    return {
        "policy": {
            "prompt_budget_tokens": int(prompt_budget_tokens),
            "per_file_structure_tokens": int(per_file_structure_tokens),
            "per_file_evidence_tokens": int(per_file_evidence_tokens),
            "pdf_evidence_pages_max": int(pdf_evidence_pages_max),
            "evidence_keep_first_n_files": int(n),
        },
        "files": prompt_files,
        "tokens_prompt_corpus_est": int(corpus_tokens),
        "tokens_prompt_total_est": int(
            instructions_tokens_est + task_tokens_est + corpus_tokens
        ),
    }


def render_prompt_corpus_text(prompt: PromptCorpus, full: FullCorpus) -> str:
    full_by_path = {f["rel_path"]: f for f in full["files"]}
    blocks: list[str] = []
    for pf in prompt["files"]:
        ff = full_by_path.get(pf["rel_path"])
        if not ff:
            continue
        header = (
            f"FILE: {ff['rel_path']} | TYPE: {ff['ext']} | SIZE: {ff['size_bytes']} | PARSE: {ff['parse']}"
        )
        blocks.append(
            "\n".join(
                [
                    header,
                    "STRUCTURE:",
                    pf["structure_text"],
                    "EVIDENCE:",
                    pf["evidence_text"],
                ]
            ).strip()
        )
    return "\n\n---\n\n".join(blocks).strip()

