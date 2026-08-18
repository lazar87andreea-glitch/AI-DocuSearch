import os
import sys
import importlib.util
from src.ingest import extract_text


def test_extract_text_plain_text():
    path = "temp_ingest_test.txt"
    content = "Hello world\nThis is a test."
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    try:
        result = extract_text(path)
        assert result == content, f"Expected {content!r}, got {result!r}"
    finally:
        os.remove(path)


def test_extract_text_file_not_found():
    missing_path = "this_file_does_not_exist.txt"
    try:
        extract_text(missing_path)
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError:
        pass


def test_extract_text_docx_support():
    spec = importlib.util.find_spec("docx")
    if spec is None:
        print("SKIPPED: python-docx is not installed")
        return

    from docx import Document

    path = "temp_ingest_test.docx"
    doc = Document()
    doc.add_paragraph("Hello DOCX")
    doc.add_paragraph("This is a document test.")
    doc.save(path)

    try:
        result = extract_text(path)
        assert "Hello DOCX" in result, "DOCX paragraph missing"
        assert "This is a document test." in result, "DOCX paragraph missing"
    finally:
        os.remove(path)


def test_extract_text_doc_unsupported():
    path = "temp_ingest_test.doc"
    with open(path, "w", encoding="utf-8") as f:
        f.write("Dummy legacy doc content")

    try:
        try:
            extract_text(path)
            assert False, "Expected RuntimeError for .doc support"
        except RuntimeError as exc:
            assert ".doc format is not supported" in str(exc)
    finally:
        os.remove(path)


def run_tests():
    test_extract_text_plain_text()
    test_extract_text_file_not_found()
    test_extract_text_docx_support()
    test_extract_text_doc_unsupported()
    print("All ingestion tests completed.")


def run_extract(path: str):
    content = extract_text(path)
    print(content)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        run_tests()
    elif len(sys.argv) == 2:
        run_extract(sys.argv[1])
    else:
        print("Usage:\n  python test_ingest.py           # run ingestion tests\n  python test_ingest.py <file>    # extract text from a file")
        sys.exit(1)
