import os
import re
import time
from .ingest import extract_text
from .preprocess import clean_text, chunk_text
from .embed_index import EmbedIndex
from .ai_query import generate_answer_with_meta
from .prompt_loader import load_prompt_with_temperature
from typing import Dict, Any

PDF_PAGE_CHUNK_PATTERN = re.compile(r"^\[PDF_PAGE:(\d+)\]")
PDF_PAGE_REQUEST_PATTERN = re.compile(
    r"\b(?:pdf\s+)?(?:page|pages|pagina|pagină|pagini|paginile|página|páginas|seite|seiten)"
    r"\s*(?:(?:number|no\.?|nr\.?|numéro|numero|nummer)\s*)?(\d+)"
    r"(?:\s*(?:-|–|—|to|through|bis|à|hasta|până\s+la)\s*(\d+))?\b",
    re.IGNORECASE,
)
MAX_REQUESTED_PDF_PAGES = 5
MAX_PAGE_CONTEXT_CHARS = 30_000

# Import traceable from langsmith (initialized by web_app with credentials)
try:
    from langsmith import traceable  # type: ignore[reportUnknownVariableType]
except Exception:
    # LangSmith is optional; no-op decorator keeps tracing calls safe when it's not installed.
    from typing import Callable, TypeVar

    _F = TypeVar("_F", bound=Callable[..., Any])

    def traceable(*_args: Any, **_kwargs: Any) -> Callable[[_F], _F]:
        def _decorator(fn: _F) -> _F:
            return fn
        return _decorator


@traceable(run_type="chain", name="build_pipeline")
def build_pipeline(file_path: str, use_embeddings: bool | None = None) -> Dict[str, Any]:
    import sys
    print(f"[PIPELINE] Starting build_pipeline for {file_path}", file=sys.stderr)

    print(f"[PIPELINE] Extracting text...", file=sys.stderr)
    text = extract_text(file_path)
    return build_pipeline_from_text(text, use_embeddings=use_embeddings)


@traceable(run_type="chain", name="build_pipeline_from_text")
def build_pipeline_from_text(text: str, use_embeddings: bool | None = None) -> Dict[str, Any]:
    import sys
    text_size_mb = len(text) / (1024 * 1024)
    print(f"[PIPELINE] Extracted {len(text)} chars ({text_size_mb:.2f} MB)", file=sys.stderr)
    
    if text_size_mb > 50:
        print(f"[PIPELINE] WARNING: Text is very large ({text_size_mb:.2f} MB). This may cause memory issues.", file=sys.stderr)
    
    print(f"[PIPELINE] Cleaning text...", file=sys.stderr)
    cleaned = clean_text(text)
    print(f"[PIPELINE] Cleaned to {len(cleaned)} chars", file=sys.stderr)
    
    print(f"[PIPELINE] Chunking text...", file=sys.stderr)
    try:
        chunks = chunk_text(cleaned)
        print(f"[PIPELINE] Created {len(chunks)} chunks", file=sys.stderr)
    except Exception as e:
        print(f"[PIPELINE] ERROR during chunking: {type(e).__name__}: {e}", file=sys.stderr)
        raise

    if use_embeddings is None:
        lite_mode = os.getenv("DOCUSEARCH_LITE_MODE", "true").strip().lower()
        use_embeddings = lite_mode not in {"1", "true", "yes", "on"}
        print(f"[PIPELINE] DOCUSEARCH_LITE_MODE={lite_mode}, use_embeddings={use_embeddings}", file=sys.stderr)
    else:
        lite_mode = not use_embeddings
        print(f"[PIPELINE] use_embeddings override: {use_embeddings}", file=sys.stderr)

    if not use_embeddings:
        print(f"[PIPELINE] Using LITE mode (no embeddings)", file=sys.stderr)
        return {"index": None, "chunks": chunks, "lite_mode": True}
    # Before attempting to load embedding models, do a quick memory check to avoid OOM crashes.
    def _available_memory_gb():
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_uint64),
                    ("ullAvailPhys", ctypes.c_uint64),
                    ("ullTotalPageFile", ctypes.c_uint64),
                    ("ullAvailPageFile", ctypes.c_uint64),
                    ("ullTotalVirtual", ctypes.c_uint64),
                    ("ullAvailVirtual", ctypes.c_uint64),
                    ("ullAvailExtendedVirtual", ctypes.c_uint64),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "kernel32"):
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                return stat.ullAvailPhys / (1024 ** 3)
        except Exception:
            pass
        return 0

    avail_gb = _available_memory_gb()
    print(f"[PIPELINE] Available memory: {avail_gb:.2f} GB", file=sys.stderr)
    # If less than 2 GB available, avoid embeddings
    if avail_gb and avail_gb < 2.0:
        print(f"[PIPELINE] Low memory ({avail_gb:.2f} GB). Falling back to LITE mode.", file=sys.stderr)
        return {"index": None, "chunks": chunks, "lite_mode": True}

    print(f"[PIPELINE] Building embedding index...", file=sys.stderr)
    index = EmbedIndex()
    index.build_index(chunks)
    # If index could not build embeddings (due to MemoryError or missing model), fall back to lite mode
    try:
        if getattr(index, "disabled", False) or index.embeddings is None:
            print(f"[PIPELINE] Embedding index not available, falling back to LITE mode", file=sys.stderr)
            return {"index": None, "chunks": chunks, "lite_mode": True}
    except Exception:
        # conservative fallback
        print(f"[PIPELINE] Warning: unable to verify index state; using LITE mode", file=sys.stderr)
        return {"index": None, "chunks": chunks, "lite_mode": True}

    print(f"[PIPELINE] Index built successfully", file=sys.stderr)
    return {"index": index, "chunks": chunks, "lite_mode": False}


def _lightweight_indices(chunks: list[str], question: str, top_k: int = 3) -> list[int]:
    q = question.lower()
    scored: list[tuple[int, int]] = []
    for idx, chunk in enumerate(chunks):
        score = sum(1 for token in q.split() if token and token in chunk.lower())
        scored.append((idx, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    selected = [idx for idx, _ in scored[:top_k] if idx < len(chunks)]
    if not selected:
        selected = [0] if chunks else []
    return selected


def _requested_pdf_pages(question: str) -> list[int]:
    match = PDF_PAGE_REQUEST_PATTERN.search(question)
    if not match:
        return []

    first_page = int(match.group(1))
    last_page = int(match.group(2) or first_page)
    if first_page < 1 or last_page < first_page:
        return []
    return list(range(first_page, min(last_page, first_page + MAX_REQUESTED_PDF_PAGES - 1) + 1))


def _pdf_page_request_is_truncated(question: str, page_numbers: list[int]) -> bool:
    match = PDF_PAGE_REQUEST_PATTERN.search(question)
    return bool(
        match
        and match.group(2)
        and page_numbers
        and int(match.group(2)) > page_numbers[-1]
    )


def _indices_for_pdf_pages(chunks: list[str], page_numbers: list[int]) -> list[int]:
    requested = set(page_numbers)
    indices: list[int] = []
    for index, chunk in enumerate(chunks):
        marker = PDF_PAGE_CHUNK_PATTERN.match(chunk)
        if marker and int(marker.group(1)) in requested:
            indices.append(index)
    return indices


@traceable(run_type="chain", name="answer_question")
def answer_question(
    pipeline: Dict[str, Any], question: str, top_k: int = 3, temperature: float | None = None, document_info: str = "Unknown"
) -> Dict[str, Any]:
    chunks = pipeline.get("chunks", [])
    retrieval_start = time.perf_counter()
    requested_pages = _requested_pdf_pages(question)
    page_indices = _indices_for_pdf_pages(chunks, requested_pages)
    if requested_pages:
        indices = page_indices
        lite_mode = pipeline.get("index") is None
    elif pipeline.get("index") is None:
        indices = _lightweight_indices(chunks, question, top_k=top_k)
        lite_mode = True
    else:
        idx = pipeline["index"].search(question, k=top_k)
        indices = idx.get("indices", [])
        lite_mode = False
    retrieval_seconds = time.perf_counter() - retrieval_start

    context = "\n\n".join(chunks[i] for i in indices if i < len(chunks))
    if requested_pages:
        requested_label = ", ".join(str(page) for page in requested_pages)
        range_notice = ""
        if _pdf_page_request_is_truncated(question, requested_pages):
            range_notice = (
                f" The request exceeded the {MAX_REQUESTED_PDF_PAGES}-page limit, so only "
                "these first requested pages are included. Ask for the remaining pages in a "
                "separate question."
            )
        if context:
            context = (
                f"[PAGE_REQUEST: Physical PDF page(s) {requested_label}. PDF page numbers may "
                f"differ from page numbers printed inside the document.{range_notice}]\n\n"
                f"{context[:MAX_PAGE_CONTEXT_CHARS]}"
            )
        else:
            available_pages = sorted(
                {
                    int(marker.group(1))
                    for chunk in chunks
                    if (marker := PDF_PAGE_CHUNK_PATTERN.match(chunk))
                }
            )
            available_label = (
                f"1-{available_pages[-1]}" if available_pages else "none"
            )
            context = (
                f"[PAGE_REQUEST_UNAVAILABLE: Physical PDF page(s) {requested_label} were "
                f"requested, but no matching page text was extracted. Available physical PDF "
                f"pages: {available_label}. Explain this limitation without inventing content.]"
            )
    prompt, file_temperature = load_prompt_with_temperature("rag_prompt", context=context, question=question, document_info=document_info)
    meta = generate_answer_with_meta(prompt, temperature=temperature if temperature is not None else file_temperature)

    return {
        "query": question,
        "raw_answer": meta["answer"],
        "response_status": meta["response_status"],
        "error_type": meta["error_type"],
        "error_message": meta["error_message"],
        "source_chunks": indices,
        "lite_mode": lite_mode,
        "retrieval_seconds": retrieval_seconds,
        "generation_seconds": meta["elapsed_seconds"],
        "total_seconds": retrieval_seconds + meta["elapsed_seconds"],
        "chunk_count": len(indices),
        "context_chars": len(context),
        "prompt_tokens": meta["prompt_tokens"],
        "completion_tokens": meta["completion_tokens"],
        "total_tokens": meta["total_tokens"],
        "estimated_tokens": meta["estimated_tokens"],
        "used_live_api": meta["used_live_api"],
        "langsmith_run_id": meta["langsmith_run_id"],
        "temperature": meta["temperature"],
        "requested_pdf_pages": requested_pages,
    }


if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 3:
        print("Usage: python -m src.pipeline <file> <question>")
        sys.exit(1)
    p = build_pipeline(sys.argv[1])
    out = answer_question(p, " ".join(sys.argv[2:]))
    print(json.dumps(out, indent=2, ensure_ascii=False))
