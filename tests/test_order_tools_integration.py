"""Testes de integração das order_tools contra a API real.

Requer a API de pedidos rodando em http://localhost:8000/api/.

Executar:
    pytest tests/test_order_tools_integration.py -v

Pular quando a API estiver fora:
    Os testes são ignorados automaticamente se a API não responder.
"""

import time
import uuid

import httpx
import pytest

from src.tools.order_tools import (
    add_item_to_order,
    create_order,
    filter_orders,
    get_order_details,
    remove_item_from_order,
    update_delivery_address,
)

# Gera CPF único por execução para evitar conflito unique_together
_RUN_ID = str(int(time.time()))[-9:].zfill(11)
_TODAY = "2026-03-29"


def _api_available() -> bool:
    """Verifica se a API está acessível."""
    try:
        httpx.get("http://localhost:8000/api/orders/filter/?client_document=0", timeout=3)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _api_available(),
    reason="API de pedidos não está rodando em localhost:8000",
)


# ===================================================================
# Criação de pedido
# ===================================================================


class TestCreateOrderIntegration:
    """Testes de criação de pedido contra a API real."""

    def test_create_order_returns_id_and_fields(self) -> None:
        """Pedido criado retorna todos os campos esperados."""
        result = create_order("Teste Integração", _RUN_ID, _TODAY)
        assert "error" not in result
        assert isinstance(result["id"], int)
        assert result["client_name"] == "Teste Integração"
        assert result["client_document"] == _RUN_ID
        assert result["delivery_date"] == _TODAY
        assert result["items"] == []
        assert result["total_price"] == 0
        assert "created_at" in result
        assert "updated_at" in result

    def test_create_order_without_delivery_date(self) -> None:
        """Pedido sem data usa a data de hoje."""
        cpf = str(int(_RUN_ID) + 1).zfill(11)
        result = create_order("Teste Sem Data", cpf)
        assert "error" not in result
        assert "delivery_date" in result

    def test_create_duplicate_order_returns_error(self) -> None:
        """unique_together (name + cpf + date) retorna erro."""
        cpf = str(int(_RUN_ID) + 2).zfill(11)
        create_order("Teste Duplicado", cpf, _TODAY)
        result = create_order("Teste Duplicado", cpf, _TODAY)
        assert "error" in result

    def test_create_order_missing_name_returns_error(self) -> None:
        """API rejeita pedido sem nome."""
        result = create_order("", str(int(_RUN_ID) + 3).zfill(11), _TODAY)
        assert "error" in result

    def test_create_order_missing_document_returns_error(self) -> None:
        """API rejeita pedido sem documento."""
        result = create_order("Teste Sem CPF", "", _TODAY)
        assert "error" in result


# ===================================================================
# Jornada completa
# ===================================================================


class TestFullOrderJourneyIntegration:
    """Testa jornada completa: criar → itens → endereço → consultar → remover → filtrar."""

    @pytest.fixture(autouse=True)
    def _setup_order(self) -> None:
        """Cria um pedido novo para cada teste da classe."""
        cpf = uuid.uuid4().hex[:11]
        self.cpf = cpf
        result = create_order("Jornada Completa", cpf, _TODAY)
        assert "error" not in result, f"Falha ao criar pedido: {result}"
        self.order_id = result["id"]

    def test_add_single_item(self) -> None:
        """Adiciona um item ao pedido."""
        result = add_item_to_order(
            self.order_id,
            "Pizza Margherita Grande Borda Tradicional",
            1,
            45.00,
        )
        assert "error" not in result
        assert "detail" in result

    def test_add_item_and_verify_total_price(self) -> None:
        """total_price é calculado corretamente após adicionar item."""
        add_item_to_order(
            self.order_id,
            "Pizza Calabresa Média Borda Tradicional",
            2,
            35.00,
        )
        details = get_order_details(self.order_id)
        assert "error" not in details
        assert details["total_price"] == 70.00
        assert len(details["items"]) == 1
        assert details["items"][0]["quantity"] == 2

    def test_add_multiple_items(self) -> None:
        """Adiciona múltiplos itens separadamente e verifica total."""
        add_item_to_order(
            self.order_id,
            "Pizza Margherita Pequena Borda Tradicional",
            1,
            25.00,
        )
        add_item_to_order(
            self.order_id,
            "Pizza Calabresa Grande Borda Recheada com Cheddar",
            1,
            55.00,
        )
        details = get_order_details(self.order_id)
        assert details["total_price"] == 80.00
        assert len(details["items"]) == 2

    def test_remove_item(self) -> None:
        """Adiciona e remove um item, verificando que desaparece."""
        add_item_to_order(
            self.order_id,
            "Pizza Para Remover",
            1,
            30.00,
        )
        details = get_order_details(self.order_id)
        item_id = details["items"][0]["id"]

        result = remove_item_from_order(self.order_id, item_id)
        assert "error" not in result

        details_after = get_order_details(self.order_id)
        assert len(details_after["items"]) == 0
        assert details_after["total_price"] == 0

    def test_remove_nonexistent_item_returns_error(self) -> None:
        """Remover item inexistente retorna erro."""
        result = remove_item_from_order(self.order_id, 999999)
        assert "error" in result

    def test_update_delivery_address(self) -> None:
        """Atualiza endereço e verifica nos detalhes."""
        result = update_delivery_address(
            self.order_id,
            street_name="Av. Paulista",
            number="1000",
            complement="Sala 10",
            reference_point="Próx. ao metrô",
        )
        assert "error" not in result

        details = get_order_details(self.order_id)
        addr = details["delivery_address"]
        assert addr["street_name"] == "Av. Paulista"
        assert addr["number"] == "1000"
        assert addr["complement"] == "Sala 10"
        assert addr["reference_point"] == "Próx. ao metrô"

    def test_update_address_minimal_fields(self) -> None:
        """Atualiza endereço sem campos opcionais."""
        result = update_delivery_address(
            self.order_id,
            street_name="Rua Simples",
            number="1",
        )
        assert "error" not in result

        details = get_order_details(self.order_id)
        addr = details["delivery_address"]
        assert addr["street_name"] == "Rua Simples"
        assert addr["number"] == "1"

    def test_get_order_details_all_fields(self) -> None:
        """Detalhes do pedido contêm todos os campos esperados."""
        details = get_order_details(self.order_id)
        assert "error" not in details
        assert details["id"] == self.order_id
        assert details["client_name"] == "Jornada Completa"
        assert details["client_document"] == self.cpf
        assert details["delivery_date"] == _TODAY
        assert "created_at" in details
        assert "updated_at" in details
        assert "items" in details
        assert "total_price" in details

    def test_filter_by_document(self) -> None:
        """Filtro por CPF retorna o pedido criado."""
        result = filter_orders(self.cpf)
        assert isinstance(result, list)
        assert len(result) >= 1
        ids = [o["id"] for o in result]
        assert self.order_id in ids

    def test_filter_by_document_and_date(self) -> None:
        """Filtro por CPF + data retorna o pedido."""
        result = filter_orders(self.cpf, _TODAY)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_filter_nonexistent_document_returns_empty(self) -> None:
        """CPF sem pedidos retorna lista vazia."""
        result = filter_orders("99999999999")
        assert isinstance(result, list)
        assert len(result) == 0


# ===================================================================
# Pedido inexistente
# ===================================================================


class TestNonexistentOrderIntegration:
    """Testa operações em pedidos que não existem."""

    _FAKE_ID = 999999

    def test_get_details_nonexistent_order(self) -> None:
        """Buscar detalhes de pedido inexistente retorna erro."""
        result = get_order_details(self._FAKE_ID)
        assert "error" in result

    def test_add_item_to_nonexistent_order(self) -> None:
        """Adicionar item a pedido inexistente retorna erro."""
        result = add_item_to_order(self._FAKE_ID, "Pizza X", 1, 30.0)
        assert "error" in result

    def test_remove_item_from_nonexistent_order(self) -> None:
        """Remover item de pedido inexistente retorna erro."""
        result = remove_item_from_order(self._FAKE_ID, 1)
        assert "error" in result

    def test_update_address_nonexistent_order(self) -> None:
        """Atualizar endereço de pedido inexistente retorna erro."""
        result = update_delivery_address(self._FAKE_ID, "Rua X", "1")
        assert "error" in result
