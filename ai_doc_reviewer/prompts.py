from __future__ import annotations

import json
from typing import Any, Literal


def _system_json_only(extra: str = "") -> str:
    base = "\n".join(
        [
            "You MUST output ONLY a single valid JSON object and nothing else.",
            "- No Markdown.",
            "- Do not use triple backticks.",
            "- Do not add explanations, headings, or any text outside the JSON.",
        ]
    )
    return (base + ("\n" + extra if extra else "")).strip()


PRIMARY_SCHEMA = {
    "answer": "string",
    "confidence": "1-100 int",
    "questions": ["string"],
    "expected_confidence_after_answers": "1-100 int",
    "question_impact": [
        {
            "question": "string",
            "expected_confidence_gain": "0-30 int",
            "why_this_helps": "string",
        }
    ],
}

FINAL_SCHEMA = {"answer": "string", "confidence": "1-100 int"}


def build_primary_messages(task_text: str, prompt_corpus_text: str) -> list[dict[str, Any]]:
    system = "\n".join(
        [
            "You are a document analysis assistant.",
            _system_json_only(),
            "Primary analysis JSON schema:",
            json.dumps(PRIMARY_SCHEMA, ensure_ascii=False, indent=2),
            "Rules:",
            "1) First determine confidence as an integer from 1 to 100.",
            "2) Then generate questions count strictly by thresholds:",
            "   - confidence < 50  => 3 questions",
            "   - confidence < 65  => 2 questions",
            "   - confidence < 80  => 1 questions",
            "   - confidence >= 80 => 0 questions",
            "3) Do not hallucinate facts not present in the provided context.",
            "4) Ensure the JSON is valid and matches the schema.",
        ]
    )
    user = "\n".join(
        [
            "TASK:",
            task_text.strip(),
            "",
            "CONTEXT (Prompt Corpus):",
            prompt_corpus_text.strip(),
        ]
    ).strip()
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_manual_question_messages(task_text: str, prompt_corpus_text: str) -> list[dict[str, Any]]:
    system = "\n".join(
        [
            _system_json_only(),
            "Schema:",
            json.dumps({"questions": ["string"]}, ensure_ascii=False),
            "Rules:",
            "- Generate exactly ONE question.",
            "- The question must be the single most useful missing piece of information.",
        ]
    )
    user = "\n".join(
        [
            "TASK:",
            task_text.strip(),
            "",
            "CONTEXT (Prompt Corpus):",
            prompt_corpus_text.strip(),
        ]
    ).strip()
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_final_messages(
    task_text: str, prompt_corpus_text: str, qa_block_text: str
) -> list[dict[str, Any]]:
    system = "\n".join(
        [
            _system_json_only(),
            "Final analysis JSON schema:",
            json.dumps(FINAL_SCHEMA, ensure_ascii=False),
            "Rules:",
            "- Use the provided context and Q_AND_A.",
            "- Do not generate questions.",
        ]
    )
    user = "\n".join(
        [
            "TASK:",
            task_text.strip(),
            "",
            "CONTEXT (Prompt Corpus):",
            prompt_corpus_text.strip(),
            "",
            "Q_AND_A:",
            qa_block_text.strip(),
        ]
    ).strip()
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]

