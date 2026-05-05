from __future__ import annotations

import json
import os
import uuid

import streamlit as st

from ai_doc_reviewer.compress import build_prompt_corpus_mvp, render_prompt_corpus_text
from ai_doc_reviewer.openrouter import chat_json, make_client, reformat_to_json
from ai_doc_reviewer.parse import build_full_corpus
from ai_doc_reviewer.report import build_prompt_corpus_summary, now_iso
from ai_doc_reviewer.scan import scan_folder
from ai_doc_reviewer.tokens import estimate_tokens
from ai_doc_reviewer.types import AppSettings


st.set_page_config(page_title="ai-doc-reviewer (MVP)", layout="wide")


def browse_folder_dialog(initial: str | None = None) -> str | None:
    """
    Best-effort native folder picker for local Windows runs.
    In some environments (headless/remote) this may be unavailable.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(
            initialdir=initial or os.getcwd(),
            title="Select folder",
            mustexist=True,
        )
        root.destroy()
        return selected or None
    except Exception:
        return None


def get_settings() -> AppSettings:
    s = st.session_state.get("settings")
    if isinstance(s, AppSettings):
        return s
    s = AppSettings()
    st.session_state.settings = s
    return s


def set_settings(**kwargs) -> None:
    st.session_state.settings = AppSettings(**kwargs)


def main() -> None:
    st.title("ai-doc-reviewer (MVP)")

    settings = get_settings()

    with st.sidebar:
        st.header("LLM Provider (MVP: OpenRouter)")
        api_key = st.text_input("API key", type="password", value=st.session_state.get("api_key", ""))
        st.session_state.api_key = api_key
        model = st.text_input("Model", value=st.session_state.get("model", "openai/gpt-4o-mini"))
        st.session_state.model = model
        ca_bundle_path = st.text_input(
            "CA bundle path (optional)",
            value=getattr(settings, "ca_bundle_path", ""),
            help="Use if you get SSL CERTIFICATE_VERIFY_FAILED (corporate proxy).",
        )
        disable_ssl_verify = st.checkbox(
            "Disable SSL verification (unsafe)",
            value=bool(getattr(settings, "disable_ssl_verify", False)),
            help="Only for troubleshooting in trusted environments.",
        )

        st.header("Folder")
        c1, c2 = st.columns([4, 1])
        with c1:
            folder = st.text_input("Path", value=st.session_state.get("folder", ""))
        with c2:
            if st.button("Browse"):
                picked = browse_folder_dialog(st.session_state.get("folder", "") or None)
                if picked:
                    st.session_state.folder = picked
                    st.rerun()
                else:
                    st.warning("Folder picker is unavailable here. Paste the path manually.")
        st.session_state.folder = folder
        load = st.button("Load materials")

        st.header("Limits & Tokens")
        prompt_budget_tokens = st.number_input("prompt_budget_tokens", min_value=1000, value=settings.prompt_budget_tokens, step=1000)
        max_output_tokens = st.number_input("max_output_tokens", min_value=256, value=settings.max_output_tokens, step=256)
        per_file_structure_tokens = st.number_input("per_file_structure_tokens", min_value=100, value=settings.per_file_structure_tokens, step=100)
        per_file_evidence_tokens = st.number_input("per_file_evidence_tokens", min_value=100, value=settings.per_file_evidence_tokens, step=100)
        pdf_evidence_pages_max = st.number_input("pdf_evidence_pages_max", min_value=1, value=settings.pdf_evidence_pages_max, step=1)
        evidence_keep_first_n_files = st.number_input("evidence_keep_first_n_files", min_value=0, value=settings.evidence_keep_first_n_files, step=1)
        token_k = st.number_input("k (token estimate)", min_value=1.5, max_value=6.0, value=float(settings.token_k), step=0.1)

        if st.button("Apply settings"):
            set_settings(
                prompt_budget_tokens=int(prompt_budget_tokens),
                max_output_tokens=int(max_output_tokens),
                per_file_structure_tokens=int(per_file_structure_tokens),
                per_file_evidence_tokens=int(per_file_evidence_tokens),
                pdf_evidence_pages_max=int(pdf_evidence_pages_max),
                evidence_keep_first_n_files=int(evidence_keep_first_n_files),
                token_k=float(token_k),
                ca_bundle_path=str(ca_bundle_path or ""),
                disable_ssl_verify=bool(disable_ssl_verify),
            )
            st.rerun()

    if load:
        if not folder:
            st.error("Folder path is empty")
        else:
            scanned = scan_folder(folder)
            full, meta_by_path = build_full_corpus(scanned, k=settings.token_k, pdf_pages_max=settings.pdf_evidence_pages_max)
            st.session_state.scanned = scanned
            st.session_state.full = full
            st.session_state.meta_by_path = meta_by_path

    full = st.session_state.get("full")
    meta_by_path = st.session_state.get("meta_by_path", {})

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Full Corpus (files)")
        if full:
            st.caption(f"tokens_full_corpus_est: {full['tokens_full_corpus_est']}")
            st.dataframe(
                [
                    {
                        "rel_path": f["rel_path"],
                        "ext": f["ext"],
                        "parse": f["parse"],
                        "tokens_full": f["tokens_full_est"]["total"],
                    }
                    for f in full["files"]
                ],
                use_container_width=True,
                height=350,
            )
        else:
            st.info("Load a folder to build Full Corpus.")

    with col2:
        st.subheader("Prompt Corpus (MVP compression)")
        prompt = None
        prompt_text = ""
        if full:
            instructions_tokens_est = 1000  # coarse; keeps margin
            task_text = st.session_state.get("task_text", "")
            task_tokens_est = estimate_tokens(task_text, settings.token_k) if task_text else 0
            prompt = build_prompt_corpus_mvp(
                full,
                prompt_budget_tokens=settings.prompt_budget_tokens,
                per_file_structure_tokens=settings.per_file_structure_tokens,
                per_file_evidence_tokens=settings.per_file_evidence_tokens,
                pdf_evidence_pages_max=settings.pdf_evidence_pages_max,
                evidence_keep_first_n_files=settings.evidence_keep_first_n_files,
                k=settings.token_k,
                instructions_tokens_est=instructions_tokens_est,
                task_tokens_est=task_tokens_est,
                meta_by_path=meta_by_path,
            )
            prompt_text = render_prompt_corpus_text(prompt, full)
            st.caption(
                f"tokens_prompt_corpus_est: {prompt['tokens_prompt_corpus_est']} | "
                f"tokens_prompt_total_est: {prompt['tokens_prompt_total_est']} | "
                f"fits: {prompt['tokens_prompt_total_est'] <= settings.prompt_budget_tokens}"
            )
            st.dataframe(
                [
                    {
                        "rel_path": f["rel_path"],
                        "tokens_prompt": f["tokens_prompt_est"]["total"],
                        "evidence_removed": bool(f["compression"].get("evidence_removed", False)),
                    }
                    for f in prompt["files"]
                ],
                use_container_width=True,
                height=350,
            )
            st.session_state.prompt = prompt
            st.session_state.prompt_text = prompt_text

    st.subheader("Previews")
    pcol1, pcol2 = st.columns(2)
    with pcol1:
        st.caption("Full Corpus preview (rendered)")
        if full:
            rendered_full = []
            for f in full["files"]:
                rendered_full.append(
                    "\n".join(
                        [
                            f"FILE: {f['rel_path']} | TYPE: {f['ext']} | SIZE: {f['size_bytes']} | PARSE: {f['parse']}",
                            "STRUCTURE:",
                            f["structure_text"],
                            "EVIDENCE:",
                            f["evidence_text"],
                        ]
                    ).strip()
                )
            st.text_area("Full", value="\n\n---\n\n".join(rendered_full), height=300)
        else:
            st.text_area("Full", value="", height=300)
    with pcol2:
        st.caption("Prompt Corpus preview (exactly what is sent)")
        st.text_area("Prompt", value=st.session_state.get("prompt_text", ""), height=300)

    st.subheader("Analysis")
    task_text = st.text_area("Task", value=st.session_state.get("task_text", ""), height=120)
    st.session_state.task_text = task_text

    bcol1, bcol2, bcol3 = st.columns([1, 1, 2])
    with bcol1:
        do_analyze = st.button("Analyze (primary)")
    with bcol2:
        do_manual_q = st.button("Manual question (F6)")
    with bcol3:
        export_report = st.button("Export report.json")

    if do_analyze or do_manual_q:
        if not (api_key and model and full and st.session_state.get("prompt_text")):
            st.error("Missing API key/model or corpus not built.")
        else:
            from ai_doc_reviewer.prompts import (
                build_manual_question_messages,
                build_primary_messages,
            )

            client = make_client(
                api_key,
                ca_bundle_path=settings.ca_bundle_path,
                disable_ssl_verify=settings.disable_ssl_verify,
            )
            messages = (
                build_manual_question_messages(task_text, st.session_state.prompt_text)
                if do_manual_q
                else build_primary_messages(task_text, st.session_state.prompt_text)
            )
            trace_id = f"req_{uuid.uuid4().hex[:8]}"
            st.session_state.trace_id = trace_id
            try:
                parsed, raw = chat_json(
                    client=client,
                    model=model,
                    messages=messages,
                    max_output_tokens=settings.max_output_tokens,
                )
                st.session_state.llm_raw = raw
                st.session_state.llm = parsed
            except Exception as e:
                st.warning(f"Primary request failed: {type(e).__name__}: {e}")
                # If network/SSL error, don't attempt JSON reformat.
                if "CERTIFICATE_VERIFY_FAILED" in str(e) or "SSL" in str(e):
                    st.info(
                        "Looks like an SSL certificate issue. "
                        "If you're behind a corporate proxy, set 'CA bundle path' "
                        "or (temporarily) enable 'Disable SSL verification (unsafe)'."
                    )
                    return
                raw = getattr(e, "message", "") or str(e)
                try:
                    parsed2, raw2 = reformat_to_json(
                        client=client,
                        model=model,
                        raw_text=raw,
                        max_output_tokens=settings.max_output_tokens,
                    )
                    st.session_state.llm_raw = raw2
                    st.session_state.llm = parsed2
                except Exception as e2:
                    st.error(f"Reformat-to-json failed: {e2}")

    llm = st.session_state.get("llm")
    if llm:
        st.subheader("LLM response (parsed JSON)")
        st.json(llm)

    if export_report:
        if not (full and st.session_state.get("prompt")):
            st.error("Nothing to export yet.")
        else:
            prompt = st.session_state.prompt
            report = {
                "trace_id": st.session_state.get("trace_id", ""),
                "timestamp": now_iso(),
                "model": model,
                "task_text": task_text,
                "tokens_full_corpus_est": full["tokens_full_corpus_est"],
                "tokens_prompt_corpus_est": prompt["tokens_prompt_corpus_est"],
                "tokens_prompt_total_est": prompt["tokens_prompt_total_est"],
                "prompt_corpus_summary": build_prompt_corpus_summary(prompt),
                "llm_response": st.session_state.get("llm", None),
            }
            st.download_button(
                "Download report.json",
                data=json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name="report.json",
                mime="application/json",
            )


if __name__ == "__main__":
    main()

