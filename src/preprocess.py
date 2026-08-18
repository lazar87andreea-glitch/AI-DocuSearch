import re
from typing import List

def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{2,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks. Optimized for memory efficiency."""
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be larger than overlap")
    if not text:
        return []

    chunks: List[str] = []
    start = 0
    length = len(text)
    chunk_count = 0

    try:
        while start < length:
            end = min(start + chunk_size, length)
            chunk = text[start:end]
            chunks.append(chunk)
            chunk_count += 1

            if end == length:
                break

            next_start = end - overlap
            if next_start <= start:
                next_start = end
            start = next_start
    except MemoryError as e:
        import sys
        print(f"[PREPROCESS] MemoryError at chunk {chunk_count} (total text: {length} chars)", file=sys.stderr)
        raise

    return chunks

if __name__ == "__main__":
    sample = "\n".join(["This is line %d" % i for i in range(200)])
    c = chunk_text(clean_text(sample), chunk_size=200, overlap=50)
    print(len(c))
