from typing import List, Tuple
import numpy as np
import sys


class EmbedIndex:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.disabled = False
        self.embeddings = None
        self.index = None
        self.chunks = None

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
                print(f"[EMBED_INDEX] MemoryError loading model: {me}", file=sys.stderr)
                self.model = None
                self.disabled = True
            except Exception:
                # Other errors (network/download) should surface
                raise
        except Exception:
            raise RuntimeError("sentence-transformers is required. Install with `pip install sentence-transformers`")

    def build_index(self, chunks: List[str]):
        self.chunks = chunks
        # Try to load model lazily; if not possible, mark disabled and keep chunks only
        try:
            self._ensure_model()
        except Exception:
            self.disabled = True

        if self.disabled or self.model is None:
            # cannot build embeddings; keep chunks for fallback text search
            self.embeddings = None
            self.index = None
            return

        try:
            self.embeddings = self.model.encode(chunks, show_progress_bar=False, convert_to_numpy=True)
        except MemoryError as me:
            print(f"[EMBED_INDEX] MemoryError during encode: {me}", file=sys.stderr)
            self.embeddings = None
            self.index = None
            self.disabled = True
            return

        try:
            import faiss
            d = self.embeddings.shape[1]
            self.index = faiss.IndexFlatIP(d)
            # normalize for cosine similarity
            faiss.normalize_L2(self.embeddings)
            self.index.add(self.embeddings)
        except Exception:
            # fallback: keep embeddings and do numpy search
            self.index = None

    def _numpy_search(self, query_embedding: np.ndarray, k: int = 3) -> Tuple[List[int], List[float]]:
        emb = self.embeddings
        if emb is None:
            return [], []
        from numpy.linalg import norm
        q = query_embedding / (norm(query_embedding) + 1e-10)
        em = emb / (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-10)
        sims = (em @ q).tolist()
        idx_scores = sorted(enumerate(sims), key=lambda x: x[1], reverse=True)[:k]
        indices = [i for i, s in idx_scores]
        scores = [s for i, s in idx_scores]
        return indices, scores

    def _simple_text_search(self, query: str, k: int = 3) -> Tuple[List[int], List[float]]:
        # lightweight fallback: token-overlap scoring (cheap)
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

    def search(self, query: str, k: int = 3):
        # If embeddings are available, use them; otherwise fallback to simple text search
        try:
            # ensure model exists before attempting encoding for query
            self._ensure_model()
        except Exception:
            self.disabled = True

        if self.disabled or self.model is None or self.embeddings is None:
            inds, scores = self._simple_text_search(query, k=k)
            return {"indices": inds, "scores": scores}

        try:
            q_emb = self.model.encode([query], convert_to_numpy=True)[0]
        except MemoryError as me:
            print(f"[EMBED_INDEX] MemoryError encoding query: {me}", file=sys.stderr)
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


if __name__ == "__main__":
    ei = EmbedIndex()
    chunks = ["This is a test.", "Another sentence.", "Something else about contracts."]
    ei.build_index(chunks)
    print(ei.search("contracts", k=2))
