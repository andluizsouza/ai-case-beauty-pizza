"""Testes das tools do cardápio e pedidos.

Cobre: busca no cardápio (read-only), operações de pedido (API mockada),
tratamento de timeout e bloqueio de escrita no SQLite.
"""

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.tools.menu_tools import (
    _get_readonly_connection,
    _load_menu_items,
    get_pizza_price,
    search_menu,
)
from src.tools.order_tools import (
    add_item_to_order,
    create_order,
    filter_orders,
    get_order_details,
    remove_item_from_order,
    update_delivery_address,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DB_PATH = str(Path(__file__).resolve().parent.parent / "database" / "knowledge_base.db")


# ===================================================================
# MENU TOOLS — SQLite read-only
# ===================================================================


class TestGetReadonlyConnection:
    """Testes da conexão read-only ao banco do cardápio."""

    def test_sqlite_readonly_blocks_writes(self) -> None:
        """Verifica que a conexão read-only impede operações de escrita."""
        conn = _get_readonly_connection(DB_PATH)
        try:
            with pytest.raises(sqlite3.OperationalError):
                conn.execute("INSERT INTO pizzas (sabor, descricao, ingredientes) VALUES ('X', 'Y', 'Z')")
        finally:
            conn.close()

    def test_sqlite_readonly_blocks_delete(self) -> None:
        """Verifica que DELETE é bloqueado em modo read-only."""
        conn = _get_readonly_connection(DB_PATH)
        try:
            with pytest.raises(sqlite3.OperationalError):
                conn.execute("DELETE FROM pizzas WHERE id = 1")
        finally:
            conn.close()

    def test_sqlite_readonly_blocks_drop(self) -> None:
        """Verifica que DROP TABLE é bloqueado em modo read-only."""
        conn = _get_readonly_connection(DB_PATH)
        try:
            with pytest.raises(sqlite3.OperationalError):
                conn.execute("DROP TABLE pizzas")
        finally:
            conn.close()

    def test_sqlite_readonly_allows_select(self) -> None:
        """Verifica que SELECT funciona normalmente."""
        conn = _get_readonly_connection(DB_PATH)
        try:
            rows = conn.execute("SELECT COUNT(*) FROM pizzas").fetchone()
            assert rows[0] > 0
        finally:
            conn.close()


class TestLoadMenuItems:
    """Testes do carregamento do cardápio."""

    def test_load_all_items(self) -> None:
        """Carrega itens com todos os campos esperados."""
        items = _load_menu_items(DB_PATH)
        assert len(items) > 0
        first = items[0]
        assert "sabor" in first
        assert "tamanho" in first
        assert "borda" in first
        assert "preco" in first

    def test_items_have_valid_prices(self) -> None:
        """Todos os preços são positivos."""
        items = _load_menu_items(DB_PATH)
        for item in items:
            assert item["preco"] > 0


class TestGetPizzaPrice:
    """Testes de busca de preço exato."""

    def test_known_price(self) -> None:
        """Busca preço de combinação conhecida."""
        result = get_pizza_price("Margherita", "Pequena", "Tradicional", DB_PATH)
        assert result is not None
        assert result["preco"] == 25.0

    def test_unknown_combination_returns_none(self) -> None:
        """Combinação inexistente retorna None."""
        result = get_pizza_price("Inexistente", "Enorme", "Dupla", DB_PATH)
        assert result is None

    def test_sweet_pizza_only_traditional_crust(self) -> None:
        """Pizza doce só tem borda Tradicional; recheada retorna None."""
        result = get_pizza_price(
            "Doce de Leite com Coco", "Média", "Recheada com Cheddar", DB_PATH
        )
        assert result is None


class TestSearchMenu:
    """Testes de busca semântica (com embedding mockado)."""

    @patch("src.tools.menu_tools._get_embedding")
    def test_search_returns_results(self, mock_embed: MagicMock) -> None:
        """Busca retorna resultados com score."""
        mock_embed.return_value = [1.0] * 768
        results = search_menu("pizza margherita", db_path=DB_PATH, top_k=3)
        assert len(results) > 0
        assert len(results) <= 3
        assert "score" in results[0]
        assert "sabor" in results[0]

    @patch("src.tools.menu_tools._get_embedding")
    def test_search_results_sorted_by_score(self, mock_embed: MagicMock) -> None:
        """Resultados estão ordenados por score decrescente."""
        mock_embed.return_value = [1.0] * 768
        results = search_menu("queijo", db_path=DB_PATH)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)


# ===================================================================
# ORDER TOOLS — API REST (mockada)
# ===================================================================

_FAKE_ORDER = {
    "id": 1,
    "client_name": "João Silva",
    "client_document": "12345678901",
    "delivery_date": "2026-03-29",
    "items": [],
    "total_price": 0,
}


def _mock_response(status_code: int = 200, json_data: dict | None = None) -> httpx.Response:
    """Cria um httpx.Response mockado."""
    response = httpx.Response(
        status_code=status_code,
        json=json_data or {},
        request=httpx.Request("GET", "http://test"),
    )
    return response


class TestCreateOrder:
    """Testes de criação de pedido."""

    @patch("src.tools.order_tools.httpx.post")
    def test_create_order_success(self, mock_post: MagicMock) -> None:
        """Cria pedido com sucesso."""
        mock_post.return_value = _mock_response(201, _FAKE_ORDER)
        result = create_order("João Silva", "12345678901", "2026-03-29")
        assert result["id"] == 1
        mock_post.assert_called_once()

    @patch("src.tools.order_tools.httpx.post")
    def test_api_timeout_handled_gracefully(self, mock_post: MagicMock) -> None:
        """Timeout da API retorna erro amigável sem levantar exceção."""
        mock_post.side_effect = httpx.TimeoutException("timeout")
        result = create_order("João Silva", "12345678901")
        assert "error" in result
        assert "Timeout" in result["error"]

    @patch("src.tools.order_tools.httpx.post")
    def test_create_order_http_error(self, mock_post: MagicMock) -> None:
        """Erro HTTP retorna mensagem de erro."""
        mock_post.return_value = _mock_response(400, {"detail": "Bad request"})
        mock_post.return_value.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "error", request=httpx.Request("POST", "http://test"),
                response=_mock_response(400, {"detail": "Bad request"}),
            )
        )
        result = create_order("João Silva", "12345678901")
        assert "error" in result


class TestAddItemToOrder:
    """Testes de adição de item."""

    @patch("src.tools.order_tools.httpx.patch")
    def test_add_item_success(self, mock_patch: MagicMock) -> None:
        """Adiciona item com sucesso."""
        mock_patch.return_value = _mock_response(
            200, {"detail": "1 itens adicionados com sucesso."}
        )
        result = add_item_to_order(
            order_id=1,
            item_name="Pizza Margherita Grande Borda Tradicional",
            quantity=1,
            unit_price=45.0,
        )
        assert "error" not in result

    @patch("src.tools.order_tools.httpx.patch")
    def test_add_item_timeout(self, mock_patch: MagicMock) -> None:
        """Timeout ao adicionar item é tratado."""
        mock_patch.side_effect = httpx.TimeoutException("timeout")
        result = add_item_to_order(1, "Pizza X", 1, 30.0)
        assert "error" in result
        assert "Timeout" in result["error"]


class TestRemoveItemFromOrder:
    """Testes de remoção de item."""

    @patch("src.tools.order_tools.httpx.delete")
    def test_remove_item_success(self, mock_delete: MagicMock) -> None:
        """Remove item com sucesso."""
        mock_delete.return_value = _mock_response(204, {})
        result = remove_item_from_order(order_id=1, item_id=5)
        assert result["detail"] == "Item removido com sucesso."

    @patch("src.tools.order_tools.httpx.delete")
    def test_remove_item_timeout(self, mock_delete: MagicMock) -> None:
        """Timeout ao remover item é tratado."""
        mock_delete.side_effect = httpx.TimeoutException("timeout")
        result = remove_item_from_order(1, 5)
        assert "error" in result


class TestUpdateDeliveryAddress:
    """Testes de atualização de endereço."""

    @patch("src.tools.order_tools.httpx.patch")
    def test_update_address_success(self, mock_patch: MagicMock) -> None:
        """Atualiza endereço com sucesso."""
        mock_patch.return_value = _mock_response(
            200, {"detail": "Endereço atualizado com sucesso."}
        )
        result = update_delivery_address(
            order_id=1,
            street_name="Rua das Flores",
            number="123",
            complement="Apto 45",
        )
        assert "error" not in result

    @patch("src.tools.order_tools.httpx.patch")
    def test_update_address_timeout(self, mock_patch: MagicMock) -> None:
        """Timeout ao atualizar endereço é tratado."""
        mock_patch.side_effect = httpx.TimeoutException("timeout")
        result = update_delivery_address(1, "Rua X", "10")
        assert "error" in result


class TestGetOrderDetails:
    """Testes de consulta de pedido."""

    @patch("src.tools.order_tools.httpx.get")
    def test_get_details_success(self, mock_get: MagicMock) -> None:
        """Busca detalhes com sucesso."""
        mock_get.return_value = _mock_response(200, {**_FAKE_ORDER, "total_price": 45.0})
        result = get_order_details(order_id=1)
        assert result["id"] == 1
        assert result["total_price"] == 45.0

    @patch("src.tools.order_tools.httpx.get")
    def test_get_details_timeout(self, mock_get: MagicMock) -> None:
        """Timeout ao buscar detalhes é tratado."""
        mock_get.side_effect = httpx.TimeoutException("timeout")
        result = get_order_details(1)
        assert "error" in result


class TestFilterOrders:
    """Testes de filtro de pedidos."""

    @patch("src.tools.order_tools.httpx.get")
    def test_filter_success(self, mock_get: MagicMock) -> None:
        """Filtra pedidos com sucesso."""
        mock_get.return_value = _mock_response(200, [_FAKE_ORDER])
        result = filter_orders("12345678901", "2026-03-29")
        assert isinstance(result, list)
        assert len(result) == 1

    @patch("src.tools.order_tools.httpx.get")
    def test_filter_timeout(self, mock_get: MagicMock) -> None:
        """Timeout ao filtrar pedidos é tratado."""
        mock_get.side_effect = httpx.TimeoutException("timeout")
        result = filter_orders("12345678901")
        assert "error" in result
