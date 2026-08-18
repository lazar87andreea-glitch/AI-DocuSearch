import os
import sys
import tempfile
import time

# Prevent OpenBLAS/NumPy memory issues on low-memory machines.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.ingest import extract_text
from src.ai_query import generate_answer_with_meta
from src.pipeline import build_pipeline, answer_question

try:
    from langsmith import traceable
except Exception:
    # LangSmith is optional; no-op decorator keeps tracing calls safe when it's not installed.
    from typing import Callable, TypeVar

    _F = TypeVar("_F", bound=Callable[..., object])

    def traceable(*_args, **_kwargs) -> Callable[[_F], _F]:
        def _decorator(fn: _F) -> _F:
            return fn
        return _decorator

st.set_page_config(page_title="DocuSearch", layout="centered")
st.title("DocuSearch")
st.markdown(
    "Upload a document, ask a question, then run **RAG**, **Direct LLM**, and **Hybrid** "
    "modes side by side and compare their speed, retrieval, and token usage."
)


def save_uploaded(uploaded_file):
    suffix = os.path.splitext(uploaded_file.name)[1]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded_file.getbuffer())
    tmp.flush()
    tmp.close()
    return tmp.name


@traceable(run_type="chain", name="web_app.rag_mode")
def run_rag(file_path: str, question: str) -> dict:
    t0 = time.perf_counter()
    pipeline = build_pipeline(file_path, use_embeddings=True)
    build_seconds = time.perf_counter() - t0
    result = answer_question(pipeline, question)
    result["build_seconds"] = build_seconds
    result["total_seconds"] += build_seconds
    result["fallback_reason"] = None
    return result


@traceable(run_type="chain", name="web_app.direct_llm_mode")
def run_direct(document_text: str, question: str) -> dict:
    prompt = f"Document text:\n{document_text}\n\nQuestion: {question}\n\nAnswer based on the document above."
    meta = generate_answer_with_meta(prompt)
    return {
        "query": question,
        "raw_answer": meta["answer"],
        "source_chunks": [],
        "lite_mode": True,
        "build_seconds": 0.0,
        "retrieval_seconds": 0.0,
        "generation_seconds": meta["elapsed_seconds"],
        "total_seconds": meta["elapsed_seconds"],
        "chunk_count": 0,
        "context_chars": len(document_text),
        "prompt_tokens": meta["prompt_tokens"],
        "completion_tokens": meta["completion_tokens"],
        "total_tokens": meta["total_tokens"],
        "estimated_tokens": meta["estimated_tokens"],
        "used_live_api": meta["used_live_api"],
        "fallback_reason": None,
    }


@traceable(run_type="chain", name="web_app.hybrid_mode")
def run_hybrid(file_path: str, document_text: str, question: str) -> dict:
    try:
        return run_rag(file_path, question)
    except Exception as e:
        print(f"[HYBRID] Full pipeline failed, falling back to direct LLM: {type(e).__name__}: {e}", file=sys.stderr)
        result = run_direct(document_text, question)
        result["fallback_reason"] = f"{type(e).__name__}: {e}"
        return result


def render_metrics(result: dict):
    cols = st.columns(4)
    cols[0].metric("Total time", f"{result['total_seconds']:.2f}s")
    cols[1].metric("Chunks used", result["chunk_count"])
    cols[2].metric("Context size", f"{result['context_chars']:,} chars")
    tok_label = "Tokens (est.)" if result["estimated_tokens"] else "Tokens (actual)"
    cols[3].metric(tok_label, f"{result['total_tokens']:,}")

    with st.expander("Detailed timing & tokens"):
        st.write(f"- Build/index time: {result['build_seconds']:.2f}s")
        st.write(f"- Retrieval time: {result['retrieval_seconds']:.2f}s")
        st.write(f"- Generation time: {result['generation_seconds']:.2f}s")
        st.write(f"- Prompt tokens: {result['prompt_tokens']:,}")
        st.write(f"- Completion tokens: {result['completion_tokens']:,}")
        st.write(f"- Live API used: {'Yes' if result['used_live_api'] else 'No (simulated fallback)'}")
        if result["lite_mode"]:
            reason = result.get("fallback_reason")
            st.write(f"- ⚠ Ran in lite/keyword-search mode{f' (fallback cause: {reason})' if reason else ''}")


if "file_path" not in st.session_state:
    st.session_state.file_path = None
if "document_text" not in st.session_state:
    st.session_state.document_text = None
if "extraction_seconds" not in st.session_state:
    st.session_state.extraction_seconds = None
if "results" not in st.session_state:
    st.session_state.results = {}
if "last_question" not in st.session_state:
    st.session_state.last_question = ""

uploaded = st.file_uploader("Upload a PDF, DOCX or TXT file", type=["pdf", "docx", "txt"])

if uploaded is not None and st.session_state.get("uploaded_name") != uploaded.name:
    st.session_state.uploaded_name = uploaded.name
    st.session_state.file_path = save_uploaded(uploaded)
    st.session_state.results = {}
    with st.spinner("Extracting document text..."):
        t0 = time.perf_counter()
        try:
            st.session_state.document_text = extract_text(st.session_state.file_path)
            st.session_state.extraction_seconds = time.perf_counter() - t0
        except Exception as e:
            st.error(f"Failed to extract text: {e}")
            st.session_state.document_text = None

if st.session_state.document_text:
    size_mb = len(st.session_state.document_text) / (1024 * 1024)
    st.success(
        f"✓ Extracted {len(st.session_state.document_text)} chars ({size_mb:.2f} MB) "
        f"in {st.session_state.extraction_seconds:.2f}s"
    )

question = st.text_input("Ask a question about the document")
if question != st.session_state.last_question:
    st.session_state.last_question = question
    st.session_state.results = {}

can_run = bool(st.session_state.document_text) and bool(question)

tab_rag, tab_direct, tab_hybrid = st.tabs(["🔎 RAG Mode", "⚡ Direct LLM Mode", "🔀 Hybrid Mode"])

with tab_rag:
    st.markdown(
        "Full pipeline: chunk the document, build an embedding index, retrieve the most "
        "relevant chunks, then ask the LLM using only that context."
    )
    if st.button("Run RAG", disabled=not can_run, key="run_rag"):
        with st.spinner("Building index and retrieving..."):
            try:
                st.session_state.results["RAG"] = run_rag(st.session_state.file_path, question)
            except Exception as e:
                st.error(f"RAG mode failed: {type(e).__name__}: {e}")
    if "RAG" in st.session_state.results:
        r = st.session_state.results["RAG"]
        st.subheader("Answer")
        st.write(r["raw_answer"])
        render_metrics(r)

with tab_direct:
    st.markdown(
        "Sends the entire extracted document text directly to the LLM \u2014 no chunking, "
        "no embeddings, no retrieval step."
    )
    if st.button("Run Direct LLM", disabled=not can_run, key="run_direct"):
        with st.spinner("Asking the LLM..."):
            st.session_state.results["Direct LLM"] = run_direct(st.session_state.document_text, question)
    if "Direct LLM" in st.session_state.results:
        r = st.session_state.results["Direct LLM"]
        st.subheader("Answer")
        st.write(r["raw_answer"])
        render_metrics(r)

with tab_hybrid:
    st.markdown(
        "Tries the full RAG pipeline first; automatically falls back to Direct LLM mode "
        "if the embedding pipeline fails (e.g. low memory or a missing dependency)."
    )
    if st.button("Run Hybrid", disabled=not can_run, key="run_hybrid"):
        with st.spinner("Running hybrid pipeline..."):
            st.session_state.results["Hybrid"] = run_hybrid(
                st.session_state.file_path, st.session_state.document_text, question
            )
    if "Hybrid" in st.session_state.results:
        r = st.session_state.results["Hybrid"]
        st.subheader("Answer")
        st.write(r["raw_answer"])
        render_metrics(r)

if len(st.session_state.results) > 1:
    st.markdown("---")
    st.subheader("Compare modes")
    rows = []
    for mode_name, r in st.session_state.results.items():
        rows.append(
            {
                "Mode": mode_name,
                "Total time (s)": round(r["total_seconds"], 2),
                "Chunks used": r["chunk_count"],
                "Context chars": r["context_chars"],
                "Prompt tokens": r["prompt_tokens"],
                "Completion tokens": r["completion_tokens"],
                "Total tokens": r["total_tokens"],
                "Tokens estimated?": "Yes" if r["estimated_tokens"] else "No",
                "Live API": "Yes" if r["used_live_api"] else "No",
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown(
    "**Safe default**: RAG/Hybrid mode automatically falls back to lightweight keyword search "
    "if embedding models can't be loaded, so the app never crashes the browser."
)
