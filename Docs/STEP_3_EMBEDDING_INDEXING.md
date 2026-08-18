# DocuSearch — Step 3: Embedding & Indexing

## Overview
The embedding and indexing step converts text chunks into semantic embeddings (numerical vector representations) and creates a searchable index. This enables fast semantic similarity search to find the most relevant chunks for a given query.

## Purpose
- Convert text chunks to numerical embeddings using a pre-trained model
- Build a vector index for efficient similarity search
- Enable fast retrieval of semantically relevant chunks
- Support both FAISS (GPU-optimized) and NumPy (fallback) search backends

## Key Concepts

### Embeddings
- **Definition:** Numerical representation of text meaning in high-dimensional space
- **Model:** Sentence Transformers (all-MiniLM-L6-v2) - 384-dimensional embeddings
- **Property:** Similar meaning → similar vectors → close distance in space

### Vector Index
- **Purpose:** Enable fast nearest-neighbor search
- **FAISS:** Facebook's efficient similarity search library (primary backend)
- **Cosine Similarity:** Measure of semantic relatedness between vectors
- **Normalization:** L2 normalization ensures proper cosine similarity computation

---

## Detailed Implementation Steps

### Step 3.1: Initialize EmbedIndex
```python
class EmbedIndex:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
```

**Process:**
1. **Store configuration, defer model loading:**
   - `self.model_name` is stored; the model itself is **not** loaded in `__init__`
   - The model is loaded lazily on first use via `_ensure_model()` (see below)

2. **Initialize Storage:**
   - `self.model` - Transformer model for encoding (`None` until lazily loaded)
   - `self.disabled` - `bool`, set `True` if the model could not be loaded (e.g. `MemoryError`)
   - `self.embeddings` - NumPy array storing all embeddings (`None` until built)
   - `self.index` - FAISS index for efficient search (`None` until built)
   - `self.chunks` - Original text chunks for reference (`None` until built)

**Model Details:**
```
Model: all-MiniLM-L6-v2
- Output dimension: 384 (384-D vectors)
- Training: Trained on 215M sentence pairs
- Performance: Good balance of speed and quality
- Size: ~80 MB
- Use case: General semantic search
```

**Lazy loading — `_ensure_model()`:**
```python
def _ensure_model(self):
    if self.disabled:
        return
    if self.model is not None:
        return
    try:
        from sentence_transformers import SentenceTransformer
        try:
            self.model = SentenceTransformer(self.model_name)
        except MemoryError as me:
            self.model = None
            self.disabled = True
        except Exception:
            raise
    except Exception:
        raise RuntimeError("sentence-transformers is required. Install with `pip install sentence-transformers`")
```

**Error Handling:**
- Raises `RuntimeError` if `sentence-transformers` not installed
- Catches `MemoryError` during model load and sets `self.disabled = True` instead of crashing —
  this is what allows `src/pipeline.py` to fall back to lite mode gracefully

**Example:**
```python
from src.embed_index import EmbedIndex

# Create index object (model is not downloaded yet)
index = EmbedIndex()
# or with custom model:
# index = EmbedIndex("sentence-transformers/all-mpnet-base-v2")
```

---

### Step 3.2: Build Index
```python
def build_index(self, chunks: List[str]):
```

**Process:**

1. **Store Chunks:**
   - Save reference to original chunks: `self.chunks = chunks`
   - Needed for later retrieval by index and by the text-search fallback

2. **Ensure Model Loaded:**
   - Calls `self._ensure_model()`; if that raises or leaves `self.disabled`/`self.model is None`,
     `build_index` stops here with `self.embeddings = None` and `self.index = None` — the chunks are
     still stored so keyword-based fallback search remains possible.

3. **Generate Embeddings:**
   - Use `model.encode(chunks, show_progress_bar=False, convert_to_numpy=True)`
   - Converts each text chunk to 384-D vector
   - Wrapped in a `try`/`except MemoryError`: on failure, sets `self.embeddings = None`,
     `self.index = None`, and `self.disabled = True` instead of crashing

4. **Create FAISS Index:**
   - Initialize `IndexFlatIP` (Inner Product on normalized vectors = cosine similarity)
   - Normalize embeddings with `faiss.normalize_L2` and add to the index
   - Falls back to `self.index = None` (NumPy search) if FAISS import/build fails

**Mathematical Background:**
```
For normalized vectors:
- Cosine similarity = v1 · v2 (dot product)
- Range: -1 to +1 (typically 0 to 1 for similar texts)
- Higher value = more similar
```

**Implementation:**
```python
def build_index(self, chunks: List[str]):
    self.chunks = chunks
    try:
        self._ensure_model()
    except Exception:
        self.disabled = True

    if self.disabled or self.model is None:
        self.embeddings = None
        self.index = None
        return

    try:
        self.embeddings = self.model.encode(chunks, show_progress_bar=False, convert_to_numpy=True)
    except MemoryError:
        self.embeddings = None
        self.index = None
        self.disabled = True
        return

    try:
        import faiss
        d = self.embeddings.shape[1]  # 384 dimensions
        self.index = faiss.IndexFlatIP(d)
        faiss.normalize_L2(self.embeddings)
        self.index.add(self.embeddings)
    except Exception:
        # Fallback: keep embeddings, use numpy search
        self.index = None
```

**Example:**
```python
chunks = [
    "The contract starts on January 1, 2024",
    "Payment terms are net 30 days",
    "Renewal occurs annually in December",
]

index.build_index(chunks)
# Ready for semantic search, unless disabled=True (then only chunks are stored)
```

---

### Step 3.3: Numpy Search (Fallback)
```python
def _numpy_search(self, query_embedding: np.ndarray, k: int = 3) -> Tuple[List[int], List[float]]:
```

**Process:**

1. **Normalize Query:**
   - Divide query embedding by its magnitude
   - Ensures same scale as indexed embeddings

2. **Compute Similarities:**
   - Matrix multiplication: embeddings @ query
   - Results in cosine similarity scores
   - Each score represents similarity to one chunk

3. **Rank & Select Top-K:**
   - Sort by similarity score (descending)
   - Select top k results
   - Return indices and scores

**Implementation:**
```python
def _numpy_search(self, query_embedding: np.ndarray, k: int = 3):
    emb = self.embeddings
    if emb is None:
        return [], []
    
    # Normalize query
    from numpy.linalg import norm
    q = query_embedding / (norm(query_embedding) + 1e-10)
    
    # Normalize embeddings
    em = emb / (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-10)
    
    # Compute similarities
    sims = (em @ q).tolist()
    
    # Sort and select top-k
    idx_scores = sorted(
        enumerate(sims), 
        key=lambda x: x[1], 
        reverse=True
    )[:k]
    
    indices = [i for i, s in idx_scores]
    scores = [s for i, s in idx_scores]
    return indices, scores
```

---

### Step 3.3b: Simple Text Search (No-Embeddings Fallback)
```python
def _simple_text_search(self, query: str, k: int = 3) -> Tuple[List[int], List[float]]:
```

Used by `search()` when `self.disabled` is `True` or embeddings were never built (e.g. low-memory
environments). Scores each chunk by token overlap with the query — no model or vectors required:

```python
def _simple_text_search(self, query: str, k: int = 3):
    if not self.chunks:
        return [], []
    q_tokens = set(query.lower().split())
    scores = []
    for i, c in enumerate(self.chunks):
        c_tokens = set(c.lower().split())
        overlap = len(q_tokens & c_tokens)
        scores.append((i, float(overlap)))
    scores = sorted(scores, key=lambda x: x[1], reverse=True)[:k]
    indices = [i for i, s in scores]
    sc = [s for i, s in scores]
    return indices, sc
```

---

### Step 3.4: Search Method
```python
def search(self, query: str, k: int = 3):
```

**Process:**

1. **Ensure model is loaded:**
   - Calls `self._ensure_model()`; any failure sets `self.disabled = True`

2. **No-embeddings fallback:**
   - If `self.disabled`, `self.model is None`, or `self.embeddings is None`, uses
     `_simple_text_search()` (Step 3.3b) instead of vector search

3. **Encode Query:**
   - Convert query string to embedding using same model
   - `model.encode([query], convert_to_numpy=True)[0]`
   - Wrapped in a `try`/`except MemoryError`: on failure returns `{"indices": [], "scores": []}`

4. **Try FAISS Search:**
   - If FAISS index exists, use it
   - Normalize query vector
   - Search for k nearest neighbors

5. **Fallback to NumPy:**
   - If FAISS fails or unavailable, use `_numpy_search` (Step 3.3)

6. **Return Results:**
   - Dictionary with `"indices"` (chunk indices) and `"scores"` (similarity scores)

**Implementation:**
```python
def search(self, query: str, k: int = 3):
    try:
        self._ensure_model()
    except Exception:
        self.disabled = True

    if self.disabled or self.model is None or self.embeddings is None:
        inds, scores = self._simple_text_search(query, k=k)
        return {"indices": inds, "scores": scores}

    try:
        q_emb = self.model.encode([query], convert_to_numpy=True)[0]
    except MemoryError:
        return {"indices": [], "scores": []}

    try:
        if self.index is not None:
            import faiss
            faiss.normalize_L2(q_emb.reshape(1, -1))
            D, I = self.index.search(q_emb.reshape(1, -1), k)
            return {"indices": I[0].tolist(), "scores": D[0].tolist()}
    except Exception:
        pass

    inds, scores = self._numpy_search(q_emb, k=k)
    return {"indices": inds, "scores": scores}
```

**Example:**
```python
# Search for relevant chunks
results = index.search("What are the contract dates?", k=3)

print(results)
# Output: {
#     "indices": [0, 2, 1],
#     "scores": [0.85, 0.72, 0.61]
# }

# Retrieve top chunk
top_chunk = chunks[results["indices"][0]]
print(top_chunk)
```

---

## Module Location & File Structure
**File:** `src/embed_index.py`

**Class:** `EmbedIndex`

**Methods:**
- `__init__(model_name: str = "all-MiniLM-L6-v2")`
- `_ensure_model()` (internal, lazy model loading with `MemoryError` handling)
- `build_index(chunks: List[str])`
- `search(query: str, k: int = 3) -> Dict`
- `_numpy_search(query_embedding: np.ndarray, k: int = 3) -> Tuple`
- `_simple_text_search(query: str, k: int = 3) -> Tuple` (internal, no-embeddings token-overlap fallback)

**Dependencies:**
- `sentence-transformers` - Embedding model
- `faiss-cpu` - Vector search (optional)
- `numpy` - Array operations

---

## Testing Methods

### Test 3.1: Model Initialization Test
**Objective:** Verify that the model is deferred until first use (lazy loading)

**Test Case:**
```python
from src.embed_index import EmbedIndex

def test_model_initialization():
    # Initialize index (does NOT download/load the model yet)
    index = EmbedIndex()
    
    # Assertions:
    assert index.model is None, "Model should not be loaded until first use"
    assert index.disabled is False, "Should not be disabled initially"
    assert index.embeddings is None, "Embeddings should be None before build"
    assert index.chunks is None, "Chunks should be None before build"
    
    print("✓ Model initialization test passed")
```

---

### Test 3.2: Index Building Test
**Objective:** Verify that embeddings are generated and indexed correctly

**Test Case:**
```python
def test_index_building():
    index = EmbedIndex()
    chunks = [
        "The contract starts on January 1, 2024",
        "Payment terms are net 30 days",
        "Renewal occurs annually in December",
    ]
    
    # Build index
    index.build_index(chunks)
    
    # Assertions:
    assert index.chunks == chunks, "Chunks should be stored"
    assert index.embeddings is not None, "Embeddings should be generated"
    assert index.embeddings.shape == (3, 384), "Should have 3 embeddings of 384-D"
    assert index.index is not None or index.embeddings is not None, \
        "Should have either FAISS or NumPy search available"
    
    print("✓ Index building test passed")
```

---

### Test 3.3: Embedding Shape Test
**Objective:** Verify embedding dimensions

**Test Case:**
```python
def test_embedding_dimensions():
    index = EmbedIndex()
    chunks = ["Sample text 1", "Sample text 2", "Sample text 3"]
    index.build_index(chunks)
    
    # Check shape
    num_chunks, embedding_dim = index.embeddings.shape
    assert num_chunks == 3, f"Expected 3 embeddings, got {num_chunks}"
    assert embedding_dim == 384, f"Expected 384 dimensions, got {embedding_dim}"
    
    # Check normalization (L2 norm should be ~1)
    from numpy.linalg import norm
    for i, emb in enumerate(index.embeddings):
        nrm = norm(emb)
        assert 0.99 < nrm <= 1.01, f"Embedding {i} not properly normalized"
    
    print("✓ Embedding dimension test passed")
```

---

### Test 3.4: Search Functionality Test
**Objective:** Verify that semantic search returns relevant results

**Test Case:**
```python
def test_search_functionality():
    index = EmbedIndex()
    chunks = [
        "The contract starts on January 1, 2024",
        "Payment terms are net 30 days",
        "Renewal occurs annually in December",
    ]
    index.build_index(chunks)
    
    # Search for contract dates
    results = index.search("When does contract start?", k=2)
    
    # Assertions:
    assert "indices" in results, "Should return indices"
    assert "scores" in results, "Should return scores"
    assert len(results["indices"]) <= 2, "Should return at most k results"
    assert len(results["indices"]) > 0, "Should return at least one result"
    
    # Top result should be about dates
    top_idx = results["indices"][0]
    assert "January" in chunks[top_idx], "Should find date-related chunk"
    
    print("✓ Search functionality test passed")
```

---

### Test 3.5: Similarity Score Test
**Objective:** Verify that similarity scores are meaningful

**Test Case:**
```python
def test_similarity_scores():
    index = EmbedIndex()
    chunks = [
        "The quick brown fox jumps over the lazy dog",
        "A fast brown fox leaps over a lazy dog",  # Very similar
        "The weather is sunny today",  # Different topic
    ]
    index.build_index(chunks)
    
    # Search for a similar query
    results = index.search("Quick brown fox", k=3)
    
    # Check scores are in valid range
    scores = results["scores"]
    for score in scores:
        assert 0 <= score <= 1, f"Score should be 0-1, got {score}"
    
    # First two chunks should have higher similarity
    assert scores[0] > scores[1] or scores[0] == scores[1], \
        "Score 0 should be >= Score 1"
    assert scores[1] > scores[2], \
        "Similar chunks should score higher than different topics"
    
    print("✓ Similarity score test passed")
```

---

### Test 3.6: Top-K Parameter Test
**Objective:** Verify that k parameter works correctly

**Test Case:**
```python
def test_top_k_parameter():
    index = EmbedIndex()
    chunks = [f"Document {i}" for i in range(10)]
    index.build_index(chunks)
    
    query = "Document"
    
    # Test different k values
    for k in [1, 3, 5, 10]:
        results = index.search(query, k=k)
        assert len(results["indices"]) == min(k, 10), \
            f"Should return {min(k, 10)} results for k={k}"
    
    print("✓ Top-K parameter test passed")
```

---

### Test 3.7: Fallback to NumPy Test
**Objective:** Verify NumPy fallback works when FAISS unavailable

**Test Case:**
```python
def test_numpy_fallback():
    index = EmbedIndex()
    chunks = ["Sample 1", "Sample 2", "Sample 3"]
    index.build_index(chunks)
    
    # Manually disable FAISS to test fallback
    index.index = None
    
    # Search should still work
    results = index.search("Sample", k=2)
    
    assert "indices" in results, "Should return results with NumPy"
    assert len(results["indices"]) > 0, "NumPy fallback should work"
    
    print("✓ NumPy fallback test passed")
```

---

## Running Tests from Command Line

### Quick Manual Test
```bash
# Test embedding generation
python -c "from src.embed_index import EmbedIndex; ei = EmbedIndex(); chunks = ['Sample text']; ei.build_index(chunks); print(f'Shape: {ei.embeddings.shape}')"

# Test search
python -c "from src.embed_index import EmbedIndex; ei = EmbedIndex(); chunks = ['The contract starts in January', 'Payment terms are 30 days']; ei.build_index(chunks); print(ei.search('When does contract start?', k=2))"
```

### Using the Module Directly
```bash
# Run the embed_index module
python src/embed_index.py

# This will:
# - Create sample chunks
# - Build an index
# - Perform a test search
# - Print results
```

### Complete Test Suite
```python
# test_embed_index.py
from src.embed_index import EmbedIndex

def run_all_tests():
    print("Running Embedding & Indexing Tests...")
    test_model_initialization()
    test_index_building()
    test_embedding_dimensions()
    test_search_functionality()
    test_similarity_scores()
    test_top_k_parameter()
    test_numpy_fallback()
    print("\n✓ All embedding tests passed!")

if __name__ == "__main__":
    run_all_tests()
```

---

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| First run takes long | Model downloading (200MB) | Patient - automatic caching after first use |
| `ModuleNotFoundError: sentence_transformers` | Library not installed | `pip install sentence-transformers` |
| `ModuleNotFoundError: faiss` | FAISS not installed | `pip install faiss-cpu` (or faiss-gpu) |
| No results from search | Model or index not initialized | Call `build_index()` before `search()` |
| Low similarity scores | Model unfamiliarity with domain | Consider fine-tuned models for specialized domains |
| Memory issues | Too many large chunks | Reduce chunk size or number of chunks |

---

## Performance Optimization

### For Large Datasets (1000+ chunks)
```python
# Use FAISS quantization for memory efficiency
# Consider GPU version: faiss-gpu instead of faiss-cpu
```

### For Production Deployment
```python
# Use all-mpnet-base-v2 for better quality
index = EmbedIndex("sentence-transformers/all-mpnet-base-v2")
```

### For Mobile/Edge
```python
# Use lightweight model
index = EmbedIndex("sentence-transformers/all-MiniLM-L6-v2")  # Already optimized
```

---

## Integration with Next Step

The output of this step (indexed embeddings and search results) becomes the input for **Step 4: AI Query & Answer Generation**, where:
- Retrieved chunks will be used as context
- Context will be combined with query
- LLM will generate final answer based on retrieved context
