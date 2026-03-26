"""Semantic search for ISTAT dataflows using sentence-transformers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..api.models import DataflowInfo

logger = logging.getLogger(__name__)

MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'
EMBEDDINGS_CACHE_KEY = 'embeddings:dataflows:v1'

_model_instance: Any = None


def _get_model() -> Any:
    """Return cached SentenceTransformer model (loads once per process)."""
    global _model_instance
    if _model_instance is None:
        from sentence_transformers import SentenceTransformer
        logger.info(f'Loading SentenceTransformer model: {MODEL_NAME}')
        _model_instance = SentenceTransformer(MODEL_NAME)
    return _model_instance


def _build_dataflow_text(df: DataflowInfo) -> str:
    parts = [df.id, df.name_it, df.name_en, df.description_it, df.description_en]
    return ' '.join(p for p in parts if p)


def is_available() -> bool:
    """Return True if sentence-transformers and numpy are installed."""
    try:
        import sentence_transformers  # noqa: F401
        import numpy  # noqa: F401
        return True
    except ImportError:
        return False


def semantic_search(
    query: str,
    dataflows: list[DataflowInfo],
    cached_embeddings: Any,
    max_results: int = 10,
) -> tuple[list[DataflowInfo], Any]:
    """Search dataflows by semantic similarity.

    Args:
        query: Free-text query (can be multilingual)
        dataflows: Full list of DataflowInfo objects
        cached_embeddings: Previously computed embeddings (list[list[float]]), or None
        max_results: Maximum number of results to return

    Returns:
        Tuple of (matched dataflows, embeddings for caching)
    """
    import numpy as np

    model = _get_model()
    texts = [_build_dataflow_text(df) for df in dataflows]

    use_cache = (
        isinstance(cached_embeddings, list)
        and len(cached_embeddings) == len(dataflows)
    )

    if use_cache:
        corpus_vecs = cached_embeddings
        logger.info('Using cached dataflow embeddings')
    else:
        if cached_embeddings is None:
            logger.info('Computing dataflow embeddings (first run, will be cached)')
        else:
            logger.info(
                'Cached dataflow embeddings are missing or stale; recomputing embeddings'
            )
        corpus_vecs = model.encode(
            texts, convert_to_numpy=True, show_progress_bar=False
        ).tolist()

    query_vec = model.encode([query], convert_to_numpy=True, show_progress_bar=False)[0]

    corpus = np.array(corpus_vecs, dtype=float)
    q = np.array(query_vec, dtype=float)

    norms_c = np.linalg.norm(corpus, axis=1, keepdims=True)
    norm_q = np.linalg.norm(q)
    scores = (corpus / norms_c) @ (q / norm_q)

    top_indices = np.argsort(scores)[::-1][:max_results]
    results = [dataflows[i] for i in top_indices if scores[i] > 0.1]

    logger.info(
        f'Semantic search: query="{query}" → {len(results)} results '
        f'(top score={float(scores[top_indices[0]]):.3f})'
    )

    return results, corpus_vecs
