import re
from typing import List

PDF_PAGE_MARKER_PATTERN = re.compile(r"(?m)^\[PDF_PAGE:(\d+)\]\s*$")


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{2,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _chunk_segment(text: str, chunk_size: int, overlap: int) -> List[str]:
    chunks: List[str] = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + chunk_size, length)
        chunks.append(text[start:end])
        if end == length:
            break
        start = end - overlap

    return chunks


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks. Optimized for memory efficiency."""
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be larger than overlap")
    if not text:
        return []

    try:
        page_markers = list(PDF_PAGE_MARKER_PATTERN.finditer(text))
        if not page_markers:
            return _chunk_segment(text, chunk_size, overlap)

        chunks: List[str] = []
        leading_text = text[:page_markers[0].start()].strip()
        if leading_text:
            chunks.extend(_chunk_segment(leading_text, chunk_size, overlap))

        for marker_index, marker in enumerate(page_markers):
            content_start = marker.end()
            content_end = (
                page_markers[marker_index + 1].start()
                if marker_index + 1 < len(page_markers)
                else len(text)
            )
            page_number = marker.group(1)
            page_content = text[content_start:content_end].strip()
            page_marker = f"[PDF_PAGE:{page_number}]"
            if not page_content:
                chunks.append(page_marker)
                continue
            chunks.extend(
                f"{page_marker}\n{chunk}"
                for chunk in _chunk_segment(page_content, chunk_size, overlap)
            )

        return chunks
    except MemoryError as e:
        import sys
        print(f"[PREPROCESS] MemoryError while chunking {len(text)} chars", file=sys.stderr)
        raise

if __name__ == "__main__":
    sample = "\n".join(["This is line %d" % i for i in range(200)])
    c = chunk_text(clean_text(sample), chunk_size=200, overlap=50)
    print(len(c))
