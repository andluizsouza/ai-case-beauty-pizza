"""Parâmetros centrais de modelagem.

Centraliza nomes e versões de todos os modelos utilizados no projeto,
evitando strings duplicadas espalhadas pelo código.
"""

# ---------------------------------------------------------------------------
# LLM — Modelo de linguagem (Google Gemini)
# ---------------------------------------------------------------------------

LLM_MODEL_ID: str = "gemini-2.5-flash"
"""Identificador do modelo LLM usado pelos agentes."""

# ---------------------------------------------------------------------------
# Embeddings — Modelo de embeddings (Google Gemini)
# ---------------------------------------------------------------------------

EMBEDDING_MODEL_ID: str = "gemini-embedding-001"
"""Identificador do modelo de embeddings para busca semântica no cardápio."""
