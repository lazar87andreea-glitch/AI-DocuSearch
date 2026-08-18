# Step 5: Pipeline Orchestration

## Overview
The pipeline is the orchestrator that ties all previous steps together into a complete document processing workflow. It manages the flow from document ingestion through answer generation, coordinating all modules into a seamless end-to-end system.

## Purpose
- Orchestrate all processing steps in correct sequence
- Manage data flow between modules
- Provide unified interface for document processing
- Handle complete question-answering workflow
- Return formatted results to user

## System Architecture
```
Document Input
      ↓
[1] Ingest → Raw Text
      ↓
[2] Preprocess → Cleaned Chunks
      ↓
[3] Embedding & Index → Searchable Index
      ↓
[4] AI Query → Answer with Context
      ↓
Result Output
```

---

## Detailed Implementation Steps

### Step 5.1: Build Pipeline
```python
def build_pipeline(file_path: str, use_embeddings: bool | None = None) -> Dict[str, Any]:
```

**Process:**

1. **Extract Text (Step 1)**
   - Call `extract_text(file_path)` from ingest module
   - Reads PDF, DOCX, or text file
   - Returns raw text string; warns to `stderr` if extracted text exceeds 50 MB

2. **Clean & Chunk (Step 2)**
   - Call `clean_text(text)` to remove artifacts
   - Call `chunk_text(cleaned)` to create overlapping chunks (default `chunk_size=500, overlap=100`)

3. **Decide lite mode vs. full embeddings**
   - If `use_embeddings` is not passed explicitly, it is derived from the `DOCUSEARCH_LITE_MODE`
     environment variable (default `"true"`): lite mode is on unless the variable is explicitly falsy.
   - If lite mode is active, the function returns immediately with `index: None` — no embedding
     model is loaded at all.

4. **Memory guard (only when not in lite mode)**
   - Before loading the embedding model, checks available physical memory on Windows via
     `ctypes`/`GlobalMemoryStatusEx`.
   - If available memory is below 2 GB, falls back to lite mode (`index: None`) instead of risking
     an out-of-memory crash.

5. **Build Index (Step 3)**
   - Create `EmbedIndex()` object and call `index.build_index(chunks)`.
   - If the index reports `disabled=True` or has no embeddings (e.g. model failed to load or ran
     out of memory), falls back to lite mode as well.

6. **Return Pipeline State**
   - Dictionary with `index`, `chunks`, and `lite_mode: bool`.
   - `index` is `None` whenever lite mode is active.

**Implementation (simplified; actual code adds `stderr` debug logging at each step):**
```python
from .ingest import extract_text
from .preprocess import clean_text, chunk_text
from .embed_index import EmbedIndex
from .ai_query import generate_answer_with_meta
from typing import Dict, Any
import os
import time

def build_pipeline(file_path: str, use_embeddings: bool | None = None) -> Dict[str, Any]:
    text = extract_text(file_path)
    cleaned = clean_text(text)
    chunks = chunk_text(cleaned)

    if use_embeddings is None:
        lite_mode = os.getenv("DOCUSEARCH_LITE_MODE", "true").strip().lower()
        use_embeddings = lite_mode not in {"1", "true", "yes", "on"}

    if not use_embeddings:
        return {"index": None, "chunks": chunks, "lite_mode": True}

    if _available_memory_gb() < 2.0:
        return {"index": None, "chunks": chunks, "lite_mode": True}

    index = EmbedIndex()
    index.build_index(chunks)
    if index.disabled or index.embeddings is None:
        return {"index": None, "chunks": chunks, "lite_mode": True}

    return {"index": index, "chunks": chunks, "lite_mode": False}
```

**Example:**
```python
# Initialize pipeline from document (mode chosen by DOCUSEARCH_LITE_MODE env var)
pipeline = build_pipeline("documents/contract.pdf")

# Force full embedding mode regardless of the env var
pipeline = build_pipeline("documents/contract.pdf", use_embeddings=True)
```

---

### Step 5.1b: Lite Mode & Memory Fallback

The project's default stance (see `MASTER_GUIDE.md`) is retrieval-based when resources allow, with a
lightweight fallback for stability. `build_pipeline` implements this directly:

| Condition | Result |
|---|---|
| `DOCUSEARCH_LITE_MODE=true` (default) and `use_embeddings` not overridden | Lite mode — `index=None` |
| `use_embeddings=True` passed explicitly | Full embedding attempt, subject to the memory guard below |
| Available memory < 2 GB | Forced lite mode, even if `use_embeddings=True` |
| `EmbedIndex` fails to load the model or build embeddings (e.g. `MemoryError`) | Forced lite mode |

When `index` is `None`, `answer_question` (Step 5.2) uses a keyword-overlap search instead of
semantic search — see `_lightweight_indices` below.

---

### Step 5.2: Answer Question
```python
def answer_question(pipeline: Dict[str, Any], question: str, top_k: int = 3) -> Dict[str, Any]:
```

**Process:**

1. **Branch on lite mode (timed)**
   - If `pipeline["index"] is None` (lite mode), retrieval uses `_lightweight_indices` (keyword
     overlap) instead of semantic search — see Step 5.2b.
   - Otherwise, calls `pipeline["index"].search(question, k=top_k)` for semantic retrieval.
   - Wall-clock time for this step is captured as `retrieval_seconds`.

2. **Construct Context String**
   - Extract chunks at returned indices (bounds-checked against `len(chunks)`)
   - Join with double newlines for clarity

3. **Build Prompt (Step 4)**
   - Combine context with question and instructions for answer format

4. **Generate Answer (Step 4, timed and with token metrics)**
   - Call `generate_answer_with_meta(prompt)` — live call to the configured LLM provider, or
     simulated fallback — returning the answer plus `elapsed_seconds`, token counts, and whether
     the tokens are estimated or came from the provider's real `usage` field.

5. **Format Results**
   - Return dictionary with `query`, `raw_answer`, `source_chunks`, `lite_mode`, plus metrics:
     `retrieval_seconds`, `generation_seconds`, `total_seconds`, `chunk_count`, `context_chars`,
     `prompt_tokens`, `completion_tokens`, `total_tokens`, `estimated_tokens`, `used_live_api`

**Implementation:**
```python
def answer_question(pipeline: Dict[str, Any], question: str, top_k: int = 3) -> Dict[str, Any]:
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
    prompt = f"Context:\n{context}\n\nQuestion: {question}\nAnswer concisely and list source chunk indices."
    meta = generate_answer_with_meta(prompt)

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
    }
```

**Example:**
```python
# Ask question about document
result = answer_question(pipeline, "What are the contract dates?", top_k=3)

print(result)
# Output: {
#     "query": "What are the contract dates?",
#     "raw_answer": "The contract runs from January 1...",
#     "source_chunks": [0, 2, 5],
#     "lite_mode": False,
#     "retrieval_seconds": 0.01,
#     "generation_seconds": 1.42,
#     "total_seconds": 1.43,
#     "chunk_count": 3,
#     "context_chars": 842,
#     "prompt_tokens": 210,
#     "completion_tokens": 48,
#     "total_tokens": 258,
#     "estimated_tokens": False,
#     "used_live_api": True
# }
```

---

### Step 5.2b: Lightweight Keyword Search (`_lightweight_indices`)

Used only when `pipeline["index"] is None` (lite mode). It scores each chunk by how many
lowercased question tokens it contains — no embeddings involved:

```python
def _lightweight_indices(chunks: list[str], question: str, top_k: int = 3):
    q = question.lower()
    scored = []
    for idx, chunk in enumerate(chunks):
        score = sum(1 for token in q.split() if token and token in chunk.lower())
        scored.append((idx, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    selected = [idx for idx, _ in scored[:top_k] if idx < len(chunks)]
    if not selected:
        selected = [0] if chunks else []
    return selected
```

If no chunk contains any matching token, it falls back to returning just chunk `0` (if any chunks
exist) rather than an empty result.

---

### Step 5.3: Retrieval Quality Parameters

**Top-K Parameter:**
- `top_k=1` - Single most relevant chunk (fast, less context)
- `top_k=3` - Balanced (default, good for most queries)
- `top_k=5` - More context (slower, comprehensive)
- `top_k=10` - Maximum context (slowest, may include noise)

**Recommendation:**
```python
# For factual questions (short answers)
answer_question(pipeline, question, top_k=2)

# For complex questions (detailed answers)
answer_question(pipeline, question, top_k=5)

# For exploratory questions (comprehensive context)
answer_question(pipeline, question, top_k=10)
```

---

## Module Location & File Structure
**File:** `src/pipeline.py`

**Functions:**
- `build_pipeline(file_path: str, use_embeddings: bool | None = None) -> Dict[str, Any]`
- `answer_question(pipeline: Dict[str, Any], question: str, top_k: int = 3) -> Dict[str, Any]`
- `_lightweight_indices(chunks: list[str], question: str, top_k: int = 3) -> list[int]` (internal, lite-mode retrieval)
- `_available_memory_gb() -> float` (internal, Windows-only memory check)

**Module Imports:**
```python
from .ingest import extract_text
from .preprocess import clean_text, chunk_text
from .embed_index import EmbedIndex
from .ai_query import generate_answer_with_meta
from typing import Dict, Any
import time
```

**Environment variables:**
- `DOCUSEARCH_LITE_MODE` — controls the default of `use_embeddings` when not passed explicitly (defaults to lite mode on)

**Dependencies:**
- All previous steps (ingest, preprocess, embed_index, ai_query)
- `langsmith` (optional) — if installed and `LANGSMITH_TRACING=true`, `build_pipeline` and
  `answer_question` are each wrapped in `@traceable(run_type="chain", ...)`, so a call to
  `answer_question` shows up nested under `build_pipeline` (and under `generate_answer`, from
  Step 4) as a single trace tree in the LangSmith dashboard.

---

## Complete Workflow Example

```python
from src.pipeline import build_pipeline, answer_question

# Step 1: Build pipeline from document
print("1. Loading document...")
pipeline = build_pipeline("examples/sample.pdf")
print(f"   Document loaded. {len(pipeline['chunks'])} chunks created.")

# Step 2: Ask multiple questions
questions = [
    "What are the contract dates?",
    "What are the payment terms?",
    "When does renewal occur?",
]

for q in questions:
    print(f"\n2. Answering: {q}")
    result = answer_question(pipeline, q, top_k=3)
    print(f"   Answer: {result['raw_answer'][:200]}...")
    print(f"   Source chunks: {result['source_chunks']}")
```

---

## Testing Methods

### Test 5.1: Pipeline Initialization Test
**Objective:** Verify that pipeline builds correctly

**Test Case:**
```python
from src.pipeline import build_pipeline
import os

def test_pipeline_initialization():
    # Use test document
    test_file = "examples/sample.pdf"
    
    # Skip if test file doesn't exist
    if not os.path.exists(test_file):
        print("⊘ Test file not found, skipping test")
        return
    
    # Build pipeline
    pipeline = build_pipeline(test_file)
    
    # Assertions:
    assert isinstance(pipeline, dict), "Pipeline should be dictionary"
    assert "index" in pipeline, "Pipeline should have 'index' key"
    assert "chunks" in pipeline, "Pipeline should have 'chunks' key"
    assert len(pipeline["chunks"]) > 0, "Should have at least one chunk"
    
    print("✓ Pipeline initialization test passed")
```

---

### Test 5.2: Answer Generation Test
**Objective:** Verify complete question-answering workflow

**Test Case:**
```python
from src.pipeline import build_pipeline, answer_question

def test_answer_generation():
    # Prepare test data
    test_file = "examples/sample.pdf"
    
    if not os.path.exists(test_file):
        print("⊘ Test file not found, skipping test")
        return
    
    # Build pipeline
    pipeline = build_pipeline(test_file)
    
    # Ask question
    question = "What is discussed in this document?"
    result = answer_question(pipeline, question)
    
    # Assertions:
    assert isinstance(result, dict), "Result should be dictionary"
    assert "query" in result, "Result should have 'query'"
    assert "raw_answer" in result, "Result should have 'raw_answer'"
    assert "source_chunks" in result, "Result should have 'source_chunks'"
    
    assert result["query"] == question, "Query should match input"
    assert isinstance(result["raw_answer"], str), "Answer should be string"
    assert len(result["raw_answer"]) > 0, "Answer should not be empty"
    assert isinstance(result["source_chunks"], list), "Source chunks should be list"
    
    print("✓ Answer generation test passed")
```

---

### Test 5.3: Top-K Parameter Test
**Objective:** Verify top_k parameter controls retrieval

**Test Case:**
```python
def test_top_k_parameter():
    test_file = "examples/sample.pdf"
    
    if not os.path.exists(test_file):
        print("⊘ Test file not found, skipping test")
        return
    
    pipeline = build_pipeline(test_file)
    question = "Sample question"
    
    # Test different k values
    for k in [1, 3, 5]:
        result = answer_question(pipeline, question, top_k=k)
        
        num_sources = len(result["source_chunks"])
        expected = min(k, len(pipeline["chunks"]))
        assert num_sources <= expected, \
            f"Should return at most {expected} sources for k={k}"
    
    print("✓ Top-K parameter test passed")
```

---

### Test 5.4: Multi-Question Test
**Objective:** Verify pipeline can handle multiple questions

**Test Case:**
```python
def test_multiple_questions():
    test_file = "examples/sample.pdf"
    
    if not os.path.exists(test_file):
        print("⊘ Test file not found, skipping test")
        return
    
    pipeline = build_pipeline(test_file)
    
    # Ask multiple questions
    questions = [
        "What is this about?",
        "Tell me more details",
        "When is something mentioned?",
    ]
    
    for q in questions:
        result = answer_question(pipeline, q)
        
        assert isinstance(result, dict), f"Failed for question: {q}"
        assert len(result["raw_answer"]) > 0, f"No answer for: {q}"
    
    print("✓ Multiple questions test passed")
```

---

### Test 5.5: Result Format Test
**Objective:** Verify result format is correct and complete

**Test Case:**
```python
def test_result_format():
    test_file = "examples/sample.pdf"
    
    if not os.path.exists(test_file):
        print("⊘ Test file not found, skipping test")
        return
    
    pipeline = build_pipeline(test_file)
    question = "Test question"
    result = answer_question(pipeline, question)
    
    # Check structure
    assert isinstance(result, dict), "Result should be dict"
    
    # Check all required fields
    required_fields = ["query", "raw_answer", "source_chunks"]
    for field in required_fields:
        assert field in result, f"Missing field: {field}"
    
    # Check field types
    assert isinstance(result["query"], str), "Query should be string"
    assert isinstance(result["raw_answer"], str), "Answer should be string"
    assert isinstance(result["source_chunks"], list), "Source chunks should be list"
    
    # Check field content
    assert result["query"] == question, "Query should match input"
    assert len(result["raw_answer"]) > 0, "Answer should not be empty"
    assert all(isinstance(i, int) for i in result["source_chunks"]), \
        "Source chunk indices should be integers"
    assert all(0 <= i < len(pipeline["chunks"]) for i in result["source_chunks"]), \
        "Source chunk indices should be valid"
    
    print("✓ Result format test passed")
```

---

### Test 5.6: Source Chunk Validity Test
**Objective:** Verify returned source chunks are valid and retrievable

**Test Case:**
```python
def test_source_chunk_validity():
    test_file = "examples/sample.pdf"
    
    if not os.path.exists(test_file):
        print("⊘ Test file not found, skipping test")
        return
    
    pipeline = build_pipeline(test_file)
    result = answer_question(pipeline, "Sample question", top_k=3)
    
    # Verify all source chunks are accessible
    for idx in result["source_chunks"]:
        assert 0 <= idx < len(pipeline["chunks"]), \
            f"Invalid chunk index: {idx}"
        
        chunk = pipeline["chunks"][idx]
        assert isinstance(chunk, str), "Chunk should be string"
        assert len(chunk) > 0, "Chunk should not be empty"
    
    print("✓ Source chunk validity test passed")
```

---

## DocuSearch — Running Tests from Command Line

### Quick Manual Test
```bash
# Test pipeline build
python -c "from src.pipeline import build_pipeline; p = build_pipeline('examples/sample.pdf'); print(f'Chunks: {len(p[\"chunks\"])}')"

# Test Q&A
python -c "from src.pipeline import build_pipeline, answer_question; p = build_pipeline('examples/sample.pdf'); r = answer_question(p, 'What is discussed?'); print(r['raw_answer'][:100])"
```

### Using the Module Directly
```bash
# Run the pipeline module
python src/pipeline.py <file> <question>

# Example:
python src/pipeline.py examples/sample.pdf "What are the main points?"
```

### Using the Demo Script
```bash
# Run demo with proper argument handling
python demo.py examples/sample.pdf "What are the contract dates?"
```

### Complete Test Suite
```python
# test_pipeline.py
from src.pipeline import build_pipeline, answer_question
import os

def run_all_tests():
    print("Running Pipeline Tests...")
    test_pipeline_initialization()
    test_answer_generation()
    test_top_k_parameter()
    test_multiple_questions()
    test_result_format()
    test_source_chunk_validity()
    print("\n✓ All pipeline tests passed!")

if __name__ == "__main__":
    run_all_tests()
```

Run with:
```bash
python test_pipeline.py
```

---

## Performance Metrics

### Typical Execution Time (by step)
| Step | Time | Notes |
|------|------|-------|
| Ingest | 1-5s | Depends on document size |
| Preprocess | <1s | Very fast |
| Build Index | 5-30s | Embedding generation (cached after first use) |
| Answer Query | 5-60s | Depends on context size and LLM speed |
| **Total** | **15-100s** | Dominated by embedding and LLM steps |

### Optimization Tips
1. **First Run:** Takes longer due to model downloads
2. **Subsequent Runs:** Faster (models cached)
3. **Batch Queries:** Reuse same pipeline for multiple questions
4. **Reduce Chunks:** Fewer chunks = faster embedding
5. **Reduce Context:** Smaller top_k = faster LLM response

---

## Advanced Configuration

### Custom Chunk Parameters
```python
# From pipeline, modify chunking strategy
def build_pipeline_custom(file_path: str, chunk_size=2000, overlap=500):
    text = extract_text(file_path)
    cleaned = clean_text(text)
    chunks = chunk_text(cleaned, chunk_size=chunk_size, overlap=overlap)
    # ... rest of pipeline
```

### Custom Top-K Strategy
```python
# Adaptive top-k based on query type
def answer_question_adaptive(pipeline, question, top_k=None):
    if top_k is None:
        # Smart default based on question length
        top_k = 3 if len(question) < 50 else 5
    
    return answer_question(pipeline, question, top_k=top_k)
```

---

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Very slow first run | Model downloading | Patience - automatic caching |
| Out of memory | Document too large | Reduce chunk size or number |
| Poor answer quality | Bad retrieval | Adjust top_k or prompt |
| Irrelevant sources | Weak semantic search | Check chunk size and overlap |
| Timeout errors | LLM too slow | Reduce context size (top_k) |
| "Module not found" | Missing dependencies | `pip install -r requirements.txt` |

---

## Integration Guide

### Using in Python Code
```python
from src.pipeline import build_pipeline, answer_question

# Initialize once
pipeline = build_pipeline("document.pdf")

# Reuse for multiple questions
for question in user_questions:
    result = answer_question(pipeline, question)
    print(result["raw_answer"])
```

### Using via Command Line
```bash
# Single query
python demo.py document.pdf "Your question here?"

# Multiple queries (in a loop)
for q in "question1" "question2"; do
    python demo.py document.pdf "$q"
done
```

### Using as Module
```python
# In another project
import sys
sys.path.append('path/to/agent')

from src.pipeline import build_pipeline, answer_question
```

---

## Next Steps

After understanding the pipeline, you can:
1. **Run the demo** to see end-to-end workflow
2. **Test individual steps** to verify each component
3. **Customize parameters** for your use case
4. **Deploy** as API or service
5. **Fine-tune** based on your domain
