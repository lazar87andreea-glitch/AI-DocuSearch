# DocuSearch — Step 1: Document Ingestion & Text Extraction

## Overview
The ingestion step is responsible for extracting raw text from various document formats (PDF, DOCX, and plain text files). This is the first step in the document processing pipeline that reads document files and converts them into plain text.

## Purpose
- Extract text content from multiple document formats
- Handle different file types automatically based on file extension
- Provide error handling and fallback mechanisms
- Enable seamless integration with downstream processing steps

## Supported File Formats
- **PDF** (.pdf) - Using `pypdf` library
- **Word Documents** (.docx, .doc) - Using `python-docx` library
- **Plain Text** (.txt, .md, etc.) - Using Python's built-in file reader

---

## Detailed Implementation Steps

### Step 1.1: PDF Text Extraction
```python
def extract_text_from_pdf(path: str) -> str:
```

**Process:**
1. Import the `PdfReader` class from `pypdf`
2. Initialize a `PdfReader` object with the file path
3. Iterate through all pages in the PDF
4. Extract text from each page using `.extract_text()`
5. Handle empty pages with fallback to empty string
6. Join all page texts with newline separators

**Error Handling:**
- If `pypdf` is not installed, raises `RuntimeError` with installation instructions

**Example:**
```python
# Extract text from a PDF file
text = extract_text_from_pdf("documents/contract.pdf")
print(text)  # Output: Full text content of the PDF
```

---

### Step 1.2: DOCX Text Extraction
```python
def extract_text_from_docx(path: str) -> str:
```

**Process:**
1. Import the `Document` class from `docx` (python-docx)
2. Load the DOCX file as a Document object
3. Iterate through all paragraphs in the document
4. Extract text from each paragraph
5. Join all paragraphs with newline separators

**Error Handling:**
- If `python-docx` is not installed, raises `RuntimeError` with installation instructions
- Empty paragraphs are skipped automatically

**Example:**
```python
# Extract text from a Word document
text = extract_text_from_docx("documents/report.docx")
print(text)  # Output: Full text content of the DOCX
```

Note: `extract_text_from_docx` also extracts table contents, joining each row's non-empty cells
with ` | ` and appending them as additional lines after the paragraph text.

---

### Step 1.2b: PDF OCR Fallback (Scanned PDFs)
```python
def extract_text_from_pdf_ocr(path: str, poppler_path: str | None = None) -> str:
```

**Purpose:** Some PDFs contain scanned images with no extractable text layer. This fallback
renders each page to an image and runs OCR to recover the text.

**Process:**
1. Convert PDF pages to images using `pdf2image.convert_from_path` (300 DPI)
2. Run `pytesseract.image_to_string` on each page image
3. Join all page texts with newline separators

**Configuration (optional environment variables):**
- `TESSERACT_CMD` — path to the Tesseract executable, if not on `PATH`
- `POPPLER_PATH` — path to the Poppler `bin` directory, if not on `PATH` (used by `pdf2image`)

**Error Handling:**
- Raises `RuntimeError` with install instructions if `pdf2image` or `pytesseract` is missing
- Per-page OCR failures are swallowed and treated as empty text for that page (not a hard failure)

**Additional dependencies (not in `requirements.txt` by default):**
- `pdf2image`, `pillow`, `pytesseract` (Python packages)
- Poppler and Tesseract OCR system binaries must be installed separately

**Example:**
```python
from src.ingest import extract_text_from_pdf_ocr

text = extract_text_from_pdf_ocr("documents/scanned.pdf", poppler_path=r"C:\poppler\bin")
```

---

### Step 1.3: Unified File Handler
```python
def extract_text(path: str) -> str:
```

**Process:**
1. Check if file exists using `os.path.exists()`
2. Extract file extension using `os.path.splitext()`
3. Convert extension to lowercase for case-insensitive matching
4. Route to appropriate extraction function based on extension:
   - `.pdf` → `extract_text_from_pdf()`; if that returns empty/blank text, automatically retries
     with `extract_text_from_pdf_ocr()` (using `POPPLER_PATH` if set) before giving up
   - `.docx` → `extract_text_from_docx()`
   - `.doc` → raises `RuntimeError` (legacy `.doc` is **not** supported; convert to `.docx` or plain text first)
   - All other formats → `extract_text_from_text_file()` (plain text reader)
5. Return extracted text as string

**Error Handling:**
- Raises `FileNotFoundError` if file doesn't exist
- Raises `RuntimeError` for unsupported `.doc` files
- If OCR fallback also fails for a PDF, silently returns whatever (possibly empty) text was
  already extracted rather than raising
- Uses UTF-8 encoding with error tolerance for text files (`errors="ignore"`)

**Example:**
```python
# Universal extraction - automatically detects format
text = extract_text("documents/sample.pdf")  # Works with PDF (with OCR fallback if scanned)
text = extract_text("documents/report.docx") # Works with DOCX
text = extract_text("documents/notes.txt")   # Works with TXT
```

---

## Module Location & File Structure
**File:** `src/ingest.py`

**Functions:**
- `extract_text_from_pdf(path: str) -> str`
- `extract_text_from_pdf_ocr(path: str, poppler_path: str | None = None) -> str`
- `extract_text_from_docx(path: str) -> str`
- `extract_text_from_text_file(path: str) -> str`
- `extract_text(path: str) -> str`

**Dependencies:**
- `pypdf` - PDF text extraction
- `python-docx` - DOCX text extraction
- `pdf2image`, `pytesseract`, `pillow` - OCR fallback (optional, plus system Poppler/Tesseract binaries)
- `os` - File system operations

---

## Testing Methods

### Test 1.1: PDF Extraction Test
**Objective:** Verify that PDF files are correctly parsed and text is extracted

**Setup:**
```python
import os
from src.ingest import extract_text_from_pdf

# Create a sample PDF or use existing one
test_file = "examples/sample.pdf"
```

**Test Case:**
```python
def test_pdf_extraction():
    text = extract_text_from_pdf(test_file)
    
    # Assertions:
    assert isinstance(text, str), "Output should be a string"
    assert len(text) > 0, "Text should not be empty"
    assert "\n" in text, "Text should preserve page separations"
    print("✓ PDF extraction test passed")
```

**Expected Output:**
- Non-empty string
- Text containing document content
- Multiple lines (page separations preserved)

---

### Test 1.2: DOCX Extraction Test
**Objective:** Verify that Word documents are correctly parsed

**Setup:**
```python
from src.ingest import extract_text_from_docx

test_file = "examples/sample.docx"
```

**Test Case:**
```python
def test_docx_extraction():
    text = extract_text_from_docx(test_file)
    
    # Assertions:
    assert isinstance(text, str), "Output should be a string"
    assert len(text) > 0, "Text should not be empty"
    assert "\n" in text, "Paragraphs should be separated"
    print("✓ DOCX extraction test passed")
```

**Expected Output:**
- Non-empty string
- All paragraph content preserved
- Newline separators between paragraphs

---

### Test 1.3: File Format Detection Test
**Objective:** Verify that the unified handler correctly routes to format-specific functions

**Setup:**
```python
from src.ingest import extract_text

# Prepare test files with different extensions
pdf_file = "examples/sample.pdf"
docx_file = "examples/sample.docx"
txt_file = "examples/sample.txt"
```

**Test Case:**
```python
def test_file_format_detection():
    # Test PDF detection
    pdf_text = extract_text(pdf_file)
    assert isinstance(pdf_text, str) and len(pdf_text) > 0
    
    # Test DOCX detection
    docx_text = extract_text(docx_file)
    assert isinstance(docx_text, str) and len(docx_text) > 0
    
    # Test TXT detection
    txt_text = extract_text(txt_file)
    assert isinstance(txt_text, str) and len(txt_text) > 0
    
    print("✓ File format detection test passed")
```

**Expected Output:**
- All formats extracted successfully
- Correct routing to format-specific handlers

---

### Test 1.4: Error Handling Test
**Objective:** Verify proper error handling for missing/invalid files

**Test Case:**
```python
def test_error_handling():
    # Test non-existent file
    try:
        extract_text("nonexistent.pdf")
        assert False, "Should raise FileNotFoundError"
    except FileNotFoundError:
        print("✓ Correctly raises FileNotFoundError for missing files")
    
    # Test unsupported format handling
    # (should fallback to text reading)
    text = extract_text("examples/sample.unknown")
    assert isinstance(text, str)
    print("✓ Correctly handles unsupported formats")
```

**Expected Behavior:**
- Raises `FileNotFoundError` for missing files
- Falls back to text reader for unknown extensions
- Handles encoding errors gracefully

---

### Test 1.5: Content Integrity Test
**Objective:** Verify that no content is lost during extraction

**Test Case:**
```python
def test_content_integrity():
    # Extract text from document
    text = extract_text("examples/sample.pdf")
    
    # Check for common document elements
    checks = [
        (len(text) > 100, "Text should contain substantial content"),
        (text == text.strip(), "Text should be properly stripped"),
        ("\n\n" in text or "\n" in text, "Text should contain line breaks"),
    ]
    
    for condition, message in checks:
        assert condition, message
    
    print("✓ Content integrity test passed")
```

---

## Running Tests from Command Line

### Quick Manual Test
```bash
# Test PDF extraction
python -c "from src.ingest import extract_text; print(extract_text('examples/sample.pdf')[:200])"

# Test DOCX extraction
python -c "from src.ingest import extract_text; print(extract_text('examples/sample.docx')[:200])"
```

### Using the Module Directly
```bash
# Run the ingest module with file argument
python src/ingest.py examples/sample.pdf

# This will print the first 1000 characters of extracted text
```

### Complete Test Suite Example
```python
# test_ingest.py
from src.ingest import extract_text, extract_text_from_pdf, extract_text_from_docx
import os

def run_all_tests():
    print("Running Ingestion Tests...")
    test_file_format_detection()
    test_error_handling()
    test_content_integrity()
    print("\n✓ All tests passed!")

if __name__ == "__main__":
    run_all_tests()
```

Run with:
```bash
python test_ingest.py
```

---

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError: No module named 'pypdf'` | Library not installed | `pip install pypdf` |
| `ModuleNotFoundError: No module named 'docx'` | Library not installed | `pip install python-docx` |
| `FileNotFoundError` | File path incorrect or doesn't exist | Verify file path and existence |
| Empty string returned | File is empty or corrupted | Check file integrity |
| Encoding errors in text files | Mixed encoding or special characters | Already handled with UTF-8 fallback |

---

## OCR on Streamlit Cloud

### System Dependencies

For OCR support on Streamlit Cloud, the `packages.txt` file must include:

```
tesseract-ocr
poppler-utils
libtesseract-dev
```

These system packages are automatically installed during Streamlit Cloud deployment.

### Language Support

Tesseract includes English by default. For other languages (e.g., Romanian):

**On local development:**
- Install language data: `apt-get install tesseract-ocr-ron` (Romanian)
- Or use environment variable: `TESSERACT_CONFIG` with language code: `export TESSDATA_PREFIX=/path/to/tessdata`

**On Streamlit Cloud:**
- Language packs are installed automatically with `tesseract-ocr` package
- Romanian OCR works out-of-the-box

### Troubleshooting OCR

| Issue | Cause | Solution |
|-------|-------|----------|
| "pdf2image not found" | Missing Python package | Ensure `pdf2image` in `requirements.txt` |
| "poppler-utils not found" | Missing system package | Ensure `poppler-utils` in `packages.txt` |
| "pytesseract not found" | Missing Python package | Ensure `pytesseract` in `requirements.txt` |
| OCR very slow (60+ seconds) | Large or high-DPI PDF | Normal for scanned documents; consider splitting them |
| Poor OCR results | Low quality scan or non-Latin script | Rescan at higher DPI or convert to digital PDF |

---

## Performance Considerations

- **Large PDFs:** Processing very large PDFs (100+ MB) may take time; consider processing in chunks
- **Memory Usage:** Entire document is loaded into memory; not suitable for streaming scenarios
- **Encoding:** UTF-8 fallback handles most encodings but may lose some characters

---

## Integration with Next Step

The output of this step (plain text) becomes the input for **Step 2: Preprocessing & Text Cleaning**, where the text will be:
- Cleaned of formatting artifacts
- Divided into manageable chunks
- Prepared for embedding generation
