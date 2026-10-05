"""
retrieval.py

Hybrid retrieval layer for StyleScout.

"Hybrid" here means we retrieve over two different kinds of sources and
merge the results:

  1. Structured data  -> the product catalog (data/catalog.csv)
  2. Unstructured data -> the trend notes (data/trend_notes.md)

Both are embedded into the same TF-IDF vector space so a single query
(e.g. "cozy preppy fall outfit under $150") can pull back relevant
catalog items AND relevant trend notes in one search call.

We use scikit-learn's TF-IDF + cosine similarity instead of a heavier
sentence-transformer model. This keeps the project dependency-light and
fast to run locally, which matters for a same-day build. Swapping in a
proper embedding model later (e.g. sentence-transformers or an API
embedding endpoint) is a drop-in replacement for the vectorizer below.
"""

from __future__ import annotations

import re
import pandas as pd
from dataclasses import dataclass
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass
class RetrievedDoc:
    """
    A single retrieved document, normalized so the rest of the agent
    doesn't need to know whether it came from the catalog or the trend
    notes.
    """
    doc_id: str
    source: str        # "catalog" or "trend_notes"
    text: str           # the text that was embedded and searched over
    metadata: dict       # original row / section data
    score: float          # cosine similarity to the query


class HybridIndex:
    """
    Builds one combined TF-IDF index over the catalog and the trend
    notes, and exposes a single `.search()` method over both.
    """

    def __init__(self, catalog_path: Path = None, trend_notes_path: Path = None):
        self.catalog_path = catalog_path or (DATA_DIR / "catalog.csv")
        self.trend_notes_path = trend_notes_path or (DATA_DIR / "trend_notes.md")

        self.catalog_df: pd.DataFrame | None = None
        self.docs: list[RetrievedDoc] = []
        self.vectorizer: TfidfVectorizer | None = None
        self.doc_matrix = None

        self._build()

    # ------------------------------------------------------------------
    # Index construction
    # ------------------------------------------------------------------

    def _build(self) -> None:
        """Load both sources, flatten them into RetrievedDoc rows, and fit TF-IDF."""

        self.docs = []
        self.docs.extend(self._load_catalog())
        self.docs.extend(self._load_trend_notes())

        corpus = [doc.text for doc in self.docs]

        # TF-IDF over unigrams + bigrams picks up short style phrases
        # like "wide leg" or "going out" better than unigrams alone.
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
        )
        self.doc_matrix = self.vectorizer.fit_transform(corpus)

    def _load_catalog(self) -> list[RetrievedDoc]:
        """Turn each catalog row into a searchable text blob."""

        self.catalog_df = pd.read_csv(self.catalog_path)
        docs = []

        for _, row in self.catalog_df.iterrows():
            text = (
                f"{row['name']} - a {row['color']} {row['category']}. "
                f"Style: {row['style_tags']}. Season: {row['season']}. "
                f"Price: ${row['price']:.2f}. Brand: {row['brand']}."
            )
            docs.append(
                RetrievedDoc(
                    doc_id=f"catalog_{row['item_id']}",
                    source="catalog",
                    text=text,
                    metadata=row.to_dict(),
                    score=0.0,
                )
            )

        return docs

    def _load_trend_notes(self) -> list[RetrievedDoc]:
        """
        Split trend_notes.md into one RetrievedDoc per "## trend_xxx"
        section, keeping the tags line so they contribute to the TF-IDF
        signal.
        """

        raw = self.trend_notes_path.read_text()
        sections = re.split(r"\n## ", raw)
        docs = []

        for section in sections:
            section = section.strip()
            if not section or not section.startswith("trend_"):
                continue

            # First line is "trend_001: Title", rest is body text.
            lines = section.splitlines()
            header = lines[0]
            body = "\n".join(lines[1:])
            doc_id = header.split(":")[0].strip()

            docs.append(
                RetrievedDoc(
                    doc_id=doc_id,
                    source="trend_notes",
                    text=f"{header}\n{body}",
                    metadata={"header": header},
                    score=0.0,
                )
            )

        return docs

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 8, source: str | None = None) -> list[RetrievedDoc]:
        """
        Return the top_k documents most similar to `query`.

        Pass source="catalog" or source="trend_notes" to restrict the
        search to just one half of the hybrid index; leave it as None
        to search across both.
        """

        query_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self.doc_matrix).flatten()

        scored = []
        for doc, sim in zip(self.docs, sims):
            if source is not None and doc.source != source:
                continue
            scored.append(
                RetrievedDoc(
                    doc_id=doc.doc_id,
                    source=doc.source,
                    text=doc.text,
                    metadata=doc.metadata,
                    score=float(sim),
                )
            )

        scored.sort(key=lambda d: d.score, reverse=True)
        return scored[:top_k]


if __name__ == "__main__":
    # Quick manual smoke test: run `python retrieval.py` to sanity check
    # the index before wiring it into the agent.
    index = HybridIndex()
    results = index.search("cozy preppy fall outfit under $150", top_k=5)

    for r in results:
        print(f"[{r.source}] {r.doc_id}  score={r.score:.3f}")
        print(f"  {r.text[:100]}...")
