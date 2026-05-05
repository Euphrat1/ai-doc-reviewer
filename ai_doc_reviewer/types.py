from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional, TypedDict

ParseStatus = Literal["ok", "warn", "fail"]


class TokenEst(TypedDict):
    structure: int
    evidence: int
    total: int


class CompressionInfo(TypedDict, total=False):
    evidence_before_tokens_est: int
    evidence_after_tokens_est: int
    evidence_removed: bool
    pdf_included_pages: list[int] | None
    table_included_ranges: list[str] | None


class PromptFile(TypedDict):
    rel_path: str
    structure_text: str
    evidence_text: str
    tokens_prompt_est: TokenEst
    compression: CompressionInfo


class FullFile(TypedDict):
    rel_path: str
    ext: str
    size_bytes: int
    parse: ParseStatus
    structure_text: str
    evidence_text: str
    tokens_full_est: TokenEst


class FullCorpus(TypedDict):
    token_estimation: dict[str, float]
    files: list[FullFile]
    tokens_full_corpus_est: int


class PromptCorpus(TypedDict):
    policy: dict[str, Any]
    files: list[PromptFile]
    tokens_prompt_corpus_est: int
    tokens_prompt_total_est: int


@dataclass(frozen=True)
class AppSettings:
    prompt_budget_tokens: int = 70_000
    max_output_tokens: int = 4_000
    per_file_structure_tokens: int = 1_000
    per_file_evidence_tokens: int = 5_000
    pdf_evidence_pages_max: int = 12
    evidence_keep_first_n_files: int = 10
    token_k: float = 3.0
    ca_bundle_path: str = ""
    disable_ssl_verify: bool = False

