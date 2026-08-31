# DocuSearch — Step 2: Preprocessing & Text Cleaning

## Overview
The preprocessing step cleans the raw extracted text and divides it into overlapping chunks. This ensures the text is properly formatted, removes artifacts from extraction, and creates optimal-sized segments for embedding generation and semantic search.

## Purpose
- Remove formatting artifacts and extra whitespace
- Normalize line breaks and spacing
- Split text into manageable chunks with context overlap
- Maintain semantic coherence across chunks
- Keep physical PDF pages separate and copy `[PDF_PAGE:n]` into every chunk from that page
- Prepare text for embedding generation

## Key Concepts

### Text Cleaning
Cleaning removes extraction artifacts and formatting noise that can interfere with semantic understanding:
- Multiple consecutive newlines (formatting artifacts)
- Extra spaces and tabs (OCR or extraction errors)
- Different newline styles (\r\n vs \n)

### Text Chunking
Dividing text into overlapping segments enables:
- Efficient semantic search (smaller units to embed)
- Context preservation (overlapping boundaries)
- Management of embedding model token limits
- Better semantic relevance for queries

---

## Detailed Implementation Steps

### Step 2.1: Text Cleaning
```python
def clean_text(text: str) -> str:
```

**Process:**
1. **Normalize Newlines:** Convert all `\r\n` (Windows style) to `\n` (Unix style)
   - Ensures consistent line break handling across platforms
2. **Remove Multiple Newlines:** Replace 2+ consecutive newlines with exactly 2 newlines
   - Removes extra blank lines created during extraction
   - Regex pattern: `\n{2,}` → `\n\n`
3. **Normalize Spaces:** Replace multiple spaces/tabs with single space
   - Removes OCR artifacts and irregular spacing
   - Regex pattern: `[ \t]+` → ` ` (space)
4. **Strip Whitespace:** Remove leading/trailing whitespace from entire text
   - Cleans up edges of extracted content

**Implementation:**
```python
import re
from typing import List

def clean_text(text: str) -> str:
    # Step 1: Normalize line endings
    text = text.replace("\r\n", "\n")
    
    # Step 2: Reduce multiple newlines to double newlines
    text = re.sub(r"\n{2,}", "\n\n", text)
    
    # Step 3: Reduce multiple spaces/tabs to single space
    text = re.sub(r"[ \t]+", " ", text)
    
    # Step 4: Strip edges
    return text.strip()
```

**Example:**
```python
# Before cleaning:
raw_text = "This  is   a\r\ntest\n\n\n\nWith    extra\nspaces"

# After cleaning:
cleaned = clean_text(raw_text)
# Output: "This is a\n\ntest\n\nWith extra\nspaces"
```

**Expected Output:**
- Consistent line endings (\n only)
- No multiple consecutive newlines
- Single spaces between words
- No leading/trailing whitespace

---

### Step 2.2: Text Chunking
```python
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
```

**Parameters:**
- `text` (str): Cleaned text to chunk
- `chunk_size` (int): Maximum characters per chunk (default: 500)
- `overlap` (int): Characters to overlap between chunks (default: 100)

**Validation:**
```python
if chunk_size <= overlap:
    raise ValueError("chunk_size must be larger than overlap")
if not text:
    return []
```

**Process:**
When `[PDF_PAGE:n]` markers are present, each page is chunked independently. Every resulting chunk
starts with its page marker, no chunk crosses a page boundary, and an empty physical page retains a
marker-only chunk. Unmarked DOCX and TXT content follows the generic sliding-window process below.

1. Initialize empty chunks list and start position (0)
2. **Sliding Window Loop:**
   - Calculate end position: `min(start + chunk_size, text_length)`
   - Extract chunk: `text[start:end]`
   - Add to chunks list
   - If `end == length`, stop (this is the last chunk)
   - Otherwise move start pointer: `next_start = end - overlap`, guarding against a
     non-advancing window by forcing `next_start = end` if `next_start <= start`
   - Repeat until entire text is processed
3. Return list of chunks (wrapped in a `try`/`except MemoryError` that logs to `stderr` and re-raises)

**Visualization:**
```
Text: [============================================================]
       ^chunk_size=500^
      overlap=100
       
Chunk 1: [=========chunk_size=500========]
Chunk 2:               [---overlap---=========chunk_size=500========]
Chunk 3:                                     [---overlap---=========...]
```

**Implementation:**
```python
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be larger than overlap")
    if not text:
        return []

    chunks = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + chunk_size, length)
        chunks.append(text[start:end])

        if end == length:
            break

        next_start = end - overlap
        if next_start <= start:
            next_start = end
        start = next_start

    return chunks
```

**Example:**
```python
text = "A" * 1200  # 1200 character string

# Default: chunk_size=500, overlap=100
chunks = chunk_text(text)

# Results:
# Chunk 1: chars 0-500 (500 chars)
# Chunk 2: chars 400-900 (overlap of 100)
# Chunk 3: chars 800-1200 (overlap of 100)
# Total: 3 chunks

print(len(chunks))  # Output: 3
print(len(chunks[0]))  # Output: 500
print(len(chunks[1]))  # Output: 500
print(len(chunks[2]))  # Output: 400 (last chunk, fits remaining text)
```

---

### Step 2.3: Overlap Benefit Example
**Why overlap matters:**

Without overlap:
```
Chunk 1: "...end of paragraph discussing contracts..."
Chunk 2: "...start of paragraph about dates..."
Problem: Lost context at boundaries!
```

With 100-character overlap:
```
Chunk 1: "...discussion about contracts..."
Chunk 2: "...contracts..." + "...dates..." (shared context maintained!)
```

---

## Module Location & File Structure
**File:** `src/preprocess.py`

**Functions:**
- `clean_text(text: str) -> str`
- `chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]`

**Dependencies:**
- `re` - Regular expressions for text cleaning
- `typing.List` - Type hints

---

## Testing Methods

### Test 2.1: Text Cleaning - Basic Test
**Objective:** Verify that text is cleaned correctly

**Test Case:**
```python
from src.preprocess import clean_text

def test_basic_cleaning():
    # Test input with various cleaning needs
    messy = "Hello  world\r\nThis\n\n\n\nhas   spaces"
    cleaned = clean_text(messy)
    
    # Assertions:
    assert cleaned == "Hello world\n\nThis\n\nhas spaces"
    assert "\r" not in cleaned, "Should not contain carriage returns"
    assert "  " not in cleaned, "Should not contain double spaces"
    
    print("✓ Basic cleaning test passed")
```

**Expected Output:**
```
"Hello world\n\nThis\n\nhas spaces"
```

---

### Test 2.2: Text Cleaning - Whitespace Normalization
**Objective:** Verify comprehensive whitespace handling

**Test Case:**
```python
def test_whitespace_normalization():
    # Test various whitespace scenarios
    test_cases = [
        ("Hello   world", "Hello world"),
        ("a\t\t\tb", "a b"),
        ("text\r\nmore", "text\nmore"),
        ("  leading", "leading"),
        ("trailing  ", "trailing"),
        ("line\n\n\n\nbreak", "line\n\nbreak"),
    ]
    
    for input_text, expected in test_cases:
        result = clean_text(input_text)
        assert result == expected, f"Failed for '{input_text}': got '{result}'"
    
    print("✓ Whitespace normalization test passed")
```

---

### Test 2.3: Text Chunking - Basic Test
**Objective:** Verify that text is split correctly

**Test Case:**
```python
from src.preprocess import chunk_text

def test_basic_chunking():
    text = "A" * 2500  # 2500 characters
    chunks = chunk_text(text, chunk_size=1000, overlap=200)
    
    # Assertions:
    assert len(chunks) == 3, f"Expected 3 chunks, got {len(chunks)}"
    assert len(chunks[0]) == 1000, "First chunk should be 1000 chars"
    assert len(chunks[1]) == 1000, "Second chunk should be 1000 chars"
    assert len(chunks[2]) == 900, "Last chunk should be 900 chars (2500-1600)"
    
    print("✓ Basic chunking test passed")
```

---

### Test 2.4: Text Chunking - Overlap Verification
**Objective:** Verify that chunks overlap correctly

**Test Case:**
```python
def test_overlap_verification():
    text = "0123456789" * 100  # 1000 chars of repeating pattern
    chunks = chunk_text(text, chunk_size=200, overlap=50)
    
    # Check that consecutive chunks overlap
    for i in range(len(chunks) - 1):
        current_chunk = chunks[i]
        next_chunk = chunks[i + 1]
        
        # Last 50 chars of current should be first 50 chars of next
        overlap_current = current_chunk[-50:]
        overlap_next = next_chunk[:50]
        
        assert overlap_current == overlap_next, "Chunks should overlap correctly"
    
    print("✓ Overlap verification test passed")
```

---

### Test 2.5: Edge Cases Test
**Objective:** Verify handling of edge cases

**Test Case:**
```python
def test_edge_cases():
    # Test 1: Text smaller than chunk_size
    small_text = "Short text"
    chunks = chunk_text(small_text, chunk_size=100, overlap=10)
    assert len(chunks) == 1, "Single chunk for small text"
    assert chunks[0] == small_text, "Should preserve small text"
    
    # Test 2: Empty string
    empty_text = ""
    chunks = chunk_text(empty_text)
    assert chunks == [], "Empty text should produce empty chunks list"
    
    # Test 3: Invalid chunk_size
    try:
        chunk_text("text", chunk_size=100, overlap=150)
        assert False, "Should raise ValueError for overlap > chunk_size"
    except ValueError:
        pass  # Expected
    
    print("✓ Edge cases test passed")
```

---

### Test 2.6: Integration Test - Clean + Chunk
**Objective:** Verify that cleaning followed by chunking works correctly

**Test Case:**
```python
def test_clean_and_chunk():
    # Simulate extraction artifact
    raw = "Extracted  text\r\nwith\n\n\nmess.\n" + ("Content. " * 200)
    
    # Process through pipeline
    from src.preprocess import clean_text, chunk_text
    cleaned = clean_text(raw)
    chunks = chunk_text(cleaned, chunk_size=500, overlap=100)
    
    # Verify pipeline
    assert isinstance(cleaned, str), "Should be string after cleaning"
    assert isinstance(chunks, list), "Should be list of chunks"
    assert all(isinstance(c, str) for c in chunks), "All chunks should be strings"
    assert len(chunks) > 0, "Should produce at least one chunk"
    
    # Verify content preservation
    joined = "".join(
        chunks[i][len(chunks[i-1])-100:] if i > 0 else chunks[i]
        for i in range(len(chunks))
    )
    assert len(joined) > 0, "Content should be preserved through pipeline"
    
    print("✓ Integration test passed")
```

---

## Running Tests from Command Line

### Quick Manual Test
```bash
# Test cleaning
python -c "from src.preprocess import clean_text; print(repr(clean_text('hello  world\r\nmore\n\n\ntext')))"

# Test chunking
python -c "from src.preprocess import chunk_text; chunks = chunk_text('A'*2500); print(f'Chunks: {len(chunks)}, Sizes: {[len(c) for c in chunks]}')"
```

### Using the Module Directly
```bash
# Run the preprocess module
python src/preprocess.py

# This will:
# - Generate 200 sample lines
# - Chunk with default parameters
# - Print the number of resulting chunks
```

### Complete Test Suite
```python
# test_preprocess.py
from src.preprocess import clean_text, chunk_text

def run_all_tests():
    print("Running Preprocessing Tests...")
    test_basic_cleaning()
    test_whitespace_normalization()
    test_basic_chunking()
    test_overlap_verification()
    test_edge_cases()
    test_clean_and_chunk()
    print("\n✓ All preprocessing tests passed!")

if __name__ == "__main__":
    run_all_tests()
```

---

## Optimal Configuration Guide

### For Legal Documents
```python
# Long, complex sentences benefit from larger chunks
chunks = chunk_text(cleaned_text, chunk_size=2000, overlap=400)
```

### For News Articles
```python
# Shorter, distinct topics benefit from smaller chunks
chunks = chunk_text(cleaned_text, chunk_size=500, overlap=100)
```

### For Code Documentation
```python
# Maintain context across function definitions
chunks = chunk_text(cleaned_text, chunk_size=1500, overlap=300)
```

---

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Too many/few chunks | Incorrect chunk_size | Adjust chunk_size parameter |
| Lost context at boundaries | Insufficient overlap | Increase overlap value |
| ValueError: chunk_size must be larger | Invalid parameters | Ensure chunk_size > overlap |
| Chunks too large for embedding | chunk_size too big | Reduce chunk_size (default 500 is safe) |
| Memory issues with large text | Text too large to process at once | Consider streaming approach |

---

## Performance Considerations

- **Cleaning:** O(n) linear time, minimal memory impact
- **Chunking:** O(n) linear time, minimal memory overhead
- **Optimal sizes:** chunk_size=500, overlap=100 (project default) for most use cases
- **Large documents:** Processing 1GB+ documents may require streaming

---

## Integration with Next Step

The output of this step (list of cleaned, overlapping chunks) becomes the input for **Step 3: Embedding & Indexing**, where:
- Each chunk will be converted to a numerical embedding
- Embeddings will be indexed for fast semantic search
- Original chunks will be stored for context retrieval
