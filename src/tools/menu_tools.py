"""Tools de consulta ao cardápio da Beauty Pizza.

Implementa busca semântica (RAG com Embeddings via Gemini) sobre o banco
SQLite do cardápio, aberto exclusivamente em modo read-only (``?mode=ro``).
"""

import logging
import sqlite3
from pathlib import Path

from google import genai

from src.config import settings
from src.model_params import EMBEDDING_MODEL_ID

logger = logging.getLogger("beauty_pizza")


def _get_embedding(text: str) -> list[float]:
    """Gera embedding para um texto usando o modelo Gemini."""
    client = genai.Client(api_key=settings.gemini_api_key)
    result = client.models.embed_content(model=EMBEDDING_MODEL_ID, contents=text)
    return result.embeddings[0].values


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calcula a similaridade de cosseno entre dois vetores."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# Database helpers (read-only)
# ---------------------------------------------------------------------------


def _get_readonly_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Abre conexão read-only com o banco do cardápio.

    Args:
        db_path: Caminho para o arquivo .db. Se ``None``, usa o caminho
                 configurado em ``settings.knowledge_base_path``.

    Returns:
        Conexão SQLite em modo read-only.

    Raises:
        sqlite3.OperationalError: Se o banco não existir ou não for acessível.
    """
    path = Path(db_path or settings.knowledge_base_path).resolve()
    uri = f"file:{path}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _load_menu_items(db_path: str | None = None) -> list[dict]:
    """Carrega todos os itens do cardápio com preços.

    Returns:
        Lista de dicionários com sabor, descrição, ingredientes,
        tamanho, borda e preço.
    """
    conn = _get_readonly_connection(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT p.sabor, p.descricao, p.ingredientes,
                   t.tamanho, b.tipo AS borda, pr.preco
            FROM precos pr
            JOIN pizzas p ON p.id = pr.pizza_id
            JOIN tamanhos t ON t.id = pr.tamanho_id
            JOIN bordas b ON b.id = pr.borda_id
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def search_menu(query: str, db_path: str | None = None, top_k: int = 5) -> list[dict]:
    """Busca semântica no cardápio usando RAG com embeddings Gemini.

    Gera embeddings para cada item do cardápio e para a query do usuário,
    retornando os ``top_k`` itens mais similares por similaridade de cosseno.

    Args:
        query: Texto de busca do usuário (ex: "pizza de calabresa grande").
        db_path: Caminho opcional para o banco SQLite (para testes).
        top_k: Quantidade máxima de resultados a retornar.

    Returns:
        Lista de dicionários com os itens mais relevantes do cardápio,
        ordenados por similaridade decrescente. Cada item contém:
        ``sabor``, ``descricao``, ``ingredientes``, ``tamanho``,
        ``borda``, ``preco``, ``score``.
    """
    logger.info("search_menu chamado com query='%s'", query)

    try:
        items = _load_menu_items(db_path)
        if not items:
            logger.warning("Cardápio vazio — nenhum item encontrado no banco")
            return []

        query_embedding = _get_embedding(query)

        scored_items = []
        for item in items:
            text = (
                f"{item['sabor']} {item['descricao']} "
                f"{item['ingredientes']} {item['tamanho']} {item['borda']}"
            )
            item_embedding = _get_embedding(text)
            score = _cosine_similarity(query_embedding, item_embedding)
            scored_items.append({**item, "score": round(score, 4)})

        scored_items.sort(key=lambda x: x["score"], reverse=True)
        results = scored_items[:top_k]

        logger.info(
            "search_menu retornou %d resultados (top score=%.4f)",
            len(results),
            results[0]["score"] if results else 0,
        )
        return results

    except Exception:
        logger.exception("Erro ao executar search_menu")
        raise


def get_pizza_price(
    sabor: str, tamanho: str, borda: str, db_path: str | None = None
) -> dict | None:
    """Busca o preço exato de uma combinação sabor + tamanho + borda.

    Args:
        sabor: Nome do sabor (ex: "Margherita").
        tamanho: Tamanho da pizza ("Pequena", "Média", "Grande").
        borda: Tipo da borda ("Tradicional", "Recheada com Cheddar", etc.).
        db_path: Caminho opcional do banco (para testes).

    Returns:
        Dicionário com sabor, tamanho, borda e preço, ou ``None`` se não encontrado.
    """
    logger.info(
        "get_pizza_price: sabor='%s', tamanho='%s', borda='%s'",
        sabor, tamanho, borda,
    )

    conn = _get_readonly_connection(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """
            SELECT p.sabor, t.tamanho, b.tipo AS borda, pr.preco
            FROM precos pr
            JOIN pizzas p ON p.id = pr.pizza_id
            JOIN tamanhos t ON t.id = pr.tamanho_id
            JOIN bordas b ON b.id = pr.borda_id
            WHERE p.sabor = ?
              AND t.tamanho = ?
              AND b.tipo = ?
            """,
            (sabor, tamanho, borda),
        ).fetchone()

        if row is None:
            logger.warning(
                "Preço não encontrado: sabor='%s', tamanho='%s', borda='%s'",
                sabor, tamanho, borda,
            )
            return None

        result = dict(row)
        logger.info("Preço encontrado: R$ %.2f", result["preco"])
        return result

    except Exception:
        logger.exception("Erro ao buscar preço")
        raise
    finally:
        conn.close()
