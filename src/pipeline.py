import os
import time
from .ingest import extract_text
from .preprocess import clean_text, chunk_text
from .embed_index import EmbedIndex
from .ai_query import generate_answer_with_meta
from .prompt_loader import load_prompt_with_temperature
from typing import Dict, Any

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


@traceable(run_type="chain", name="answer_question")
def answer_question(
    pipeline: Dict[str, Any], question: str, top_k: int = 3, temperature: float | None = None
) -> Dict[str, Any]:
    chunks = pipeline.get("chunks", [])
    retrieval_start = time.perf_counter()
    if pipeline.get("index") is None:
        indices = _lightweight_indices(chunks, question, top_k=top_k)
        lite_mode = True
    else:
        idx = pipeline["index"].search(question, k=top_k)
        indices = idx.get("indices", [])
        lite_mode = False
    retrieval_seconds = time.perf_counter() - retrieval_start

    context = "\n\n".join(chunks[i] for i in indices if i < len(chunks))
    prompt, file_temperature = load_prompt_with_temperature("rag_prompt", context=context, question=question)
    meta = generate_answer_with_meta(prompt, temperature=temperature if temperature is not None else file_temperature)

    return {
        "query": question,
        "raw_answer": meta["answer"],
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
        "temperature": meta["temperature"],
    }


if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 3:
        print("Usage: python -m src.pipeline <file> <question>")
        sys.exit(1)
    p = build_pipeline(sys.argv[1])
    out = answer_question(p, " ".join(sys.argv[2:]))
    print(json.dumps(out, indent=2, ensure_ascii=False))
