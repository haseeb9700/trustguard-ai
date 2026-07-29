"""Single source of truth for the embedding model.

Dense retrieval only works if the query and the stored passages are embedded by
the *same* model. Two vectors from different models are not comparable, and
cosine similarity between them is meaningless — it does not raise, it just
returns numbers, and retrieval quietly degrades to noise.

The model name used to be a literal repeated across ``rag_pipeline`` (which
embeds queries) and ``url_ingestor`` (which embeds passages), plus two scripts.
Nothing tied them together, so changing one and missing another would have
produced exactly that silent failure, or a dimension-mismatch crash if the two
models had different widths (bge-small is 384, base 768, large 1024). Routing
every caller through here makes the mismatch impossible to express.

It also means one model instance instead of one per importing module.

Override for experiments with ``TRUSTGUARD_EMBEDDING_MODEL``. Changing it
invalidates every stored embedding: the vector store must be rebuilt, because
old rows still hold vectors from the previous model.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger("trustguard.embeddings")

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

_model = None
_loaded_name = None


def embedding_model_name() -> str:
    """Return the configured model name."""
    return os.getenv("TRUSTGUARD_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


def get_embedding_model(name: str | None = None):
    """Load (once) and return the sentence-transformer used for retrieval.

    Args:
        name: Override the configured model. Intended for benchmarking several
            models in one process; production should leave this unset.
    """
    global _model, _loaded_name

    target = name or embedding_model_name()
    if _model is None or _loaded_name != target:
        from sentence_transformers import SentenceTransformer

        logger.info("Loading embedding model: %s", target)
        _model = SentenceTransformer(target)
        _loaded_name = target
    return _model
