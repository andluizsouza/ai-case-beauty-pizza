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
from src.models.menu import MenuItem, MenuSearchResult

logger = logging.getLogger("beauty_pizza")


def _get_embedding(text: str) -> list[float]:
    """Gera embedding para um texto usando o modelo Gemini."""
    client = genai.Client(api_key=settings.google_api_key)
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


def _load_menu_items(db_path: str | None = None) -> list[MenuItem]:
    """Carrega todos os itens do cardápio com preços.

    Returns:
        Lista de ``MenuItem`` com sabor, descrição, ingredientes,
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
        return [MenuItem(**dict(row)) for row in rows]
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

        scored_items: list[MenuSearchResult] = []
        for item in items:
            text = (
                f"{item.sabor} {item.descricao} "
                f"{item.ingredientes} {item.tamanho} {item.borda}"
            )
            item_embedding = _get_embedding(text)
            score = _cosine_similarity(query_embedding, item_embedding)
            scored_items.append(
                MenuSearchResult(**item.model_dump(), score=round(score, 4))
            )

        scored_items.sort(key=lambda x: x.score, reverse=True)
        results = scored_items[:top_k]

        logger.info(
            "search_menu retornou %d resultados (top score=%.4f)",
            len(results),
            results[0].score if results else 0,
        )
        return [r.model_dump() for r in results]

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
        Dicionário com sabor, tamanho, borda e preço (``MenuItem``),
        ou ``None`` se não encontrado.
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

        item = MenuItem(**dict(row))
        logger.info("Preço encontrado: R$ %.2f", item.preco)
        return item.model_dump()

    except Exception:
        logger.exception("Erro ao buscar preço")
        raise
    finally:
        conn.close()


def get_menu_report(db_path: str | None = None) -> str:
    """Gera relatório descritivo completo do cardápio a partir do banco.

    Consulta todas as tabelas (pizzas, tamanhos, bordas, precos) e produz
    um texto estruturado com sabores disponíveis, descrições, ingredientes,
    combinações válidas de tamanho/borda e faixas de preço. Nenhuma regra
    é hardcoded — tudo é derivado dos dados existentes no banco.

    Args:
        db_path: Caminho opcional do banco (para testes).

    Returns:
        String formatada com o relatório completo do cardápio.
    """
    logger.info("get_menu_report chamado")

    conn = _get_readonly_connection(db_path)
    conn.row_factory = sqlite3.Row
    try:
        # Sabores com descrição e ingredientes
        pizzas = conn.execute(
            "SELECT sabor, descricao, ingredientes FROM pizzas ORDER BY id"
        ).fetchall()

        # Todas as combinações válidas de tamanho/borda com contagem de sabores
        combos = conn.execute(
            """
            SELECT t.tamanho, b.tipo AS borda, COUNT(DISTINCT pr.pizza_id) AS qtd_sabores
            FROM precos pr
            JOIN tamanhos t ON t.id = pr.tamanho_id
            JOIN bordas b ON b.id = pr.borda_id
            GROUP BY t.tamanho, b.tipo
            ORDER BY t.id, b.id
            """
        ).fetchall()

        # Preços por sabor (min/max) para faixa de preço
        price_ranges = conn.execute(
            """
            SELECT p.sabor, t.tamanho, b.tipo AS borda, pr.preco
            FROM precos pr
            JOIN pizzas p ON p.id = pr.pizza_id
            JOIN tamanhos t ON t.id = pr.tamanho_id
            JOIN bordas b ON b.id = pr.borda_id
            ORDER BY p.sabor, t.id, b.id
            """
        ).fetchall()

        # Bordas disponíveis por sabor
        borders_by_flavor = conn.execute(
            """
            SELECT DISTINCT p.sabor, b.tipo AS borda
            FROM precos pr
            JOIN pizzas p ON p.id = pr.pizza_id
            JOIN bordas b ON b.id = pr.borda_id
            ORDER BY p.sabor, b.id
            """
        ).fetchall()

        # --- Montar relatório ---
        lines: list[str] = []
        lines.append("=== RELATÓRIO COMPLETO DO CARDÁPIO ===\n")

        # Sabores
        lines.append("## SABORES DISPONÍVEIS")
        for p in pizzas:
            lines.append(f"- {p['sabor']}: {p['descricao']}")
            lines.append(f"  Ingredientes: {p['ingredientes']}")
        lines.append("")

        # Combinações válidas de tamanho e borda
        lines.append("## COMBINAÇÕES VÁLIDAS DE TAMANHO E BORDA")
        total_flavors = len(pizzas)
        for c in combos:
            note = ""
            if c["qtd_sabores"] < total_flavors:
                note = f" (disponível para {c['qtd_sabores']} de {total_flavors} sabores)"
            lines.append(f"- {c['tamanho']} + {c['borda']}{note}")
        lines.append("")

        # Restrições de borda por sabor
        lines.append("## BORDAS DISPONÍVEIS POR SABOR")
        flavor_borders: dict[str, list[str]] = {}
        for row in borders_by_flavor:
            flavor_borders.setdefault(row["sabor"], []).append(row["borda"])
        all_borders = sorted({row["borda"] for row in borders_by_flavor})
        for sabor, bordas in flavor_borders.items():
            if set(bordas) != set(all_borders):
                lines.append(f"- {sabor}: APENAS {', '.join(bordas)}")
            else:
                lines.append(f"- {sabor}: todas as bordas")
        lines.append("")

        # Tabela de preços
        lines.append("## TABELA DE PREÇOS (R$)")
        current_sabor = ""
        for row in price_ranges:
            if row["sabor"] != current_sabor:
                current_sabor = row["sabor"]
                lines.append(f"\n### {current_sabor}")
            lines.append(
                f"  {row['tamanho']:>8} | {row['borda']:<30} | R$ {row['preco']:.2f}"
            )

        report = "\n".join(lines)
        logger.info("get_menu_report gerado com %d sabores", len(pizzas))
        return report

    except Exception:
        logger.exception("Erro ao gerar relatório do cardápio")
        raise
    finally:
        conn.close()
