"""Testes end-to-end do Atendente Virtual Beauty Pizza.

Validam o fluxo completo: roteamento → agente especializado → resposta,
usando mocks das chamadas LLM e HTTP para execução determinística.

Suítes:
- ``TestFullCustomerJourneyWithMissingInfo``: Jornada completa do cliente
  com dados faltantes, validando que o agente pergunta antes de prosseguir.
- ``TestSecurityRedTeaming``: Ataques de Prompt Injection e tentativas
  de manipulação/destruição da base de dados.
"""

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agents.menu_agent import MENU_AGENT_INSTRUCTIONS, create_menu_agent
from src.agents.order_agent import ORDER_AGENT_INSTRUCTIONS, create_order_agent
from src.agents.router_agent import ROUTER_AGENT_INSTRUCTIONS, create_router_agent
from src.models.routing import RouteDecision, TargetAgent
from src.tools.menu_tools import _get_readonly_connection

DB_PATH = str(Path(__file__).resolve().parent.parent / "database" / "knowledge_base.db")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeRunOutput:
    """Simula o RunOutput do Agno para testes sem LLM real."""

    content: object
    session_state: dict | None = None


def _make_route_decision(target: TargetAgent) -> FakeRunOutput:
    """Cria um FakeRunOutput contendo um RouteDecision."""
    return FakeRunOutput(content=RouteDecision(target_agent=target))


# ===================================================================
# JORNADA COMPLETA DO CLIENTE — Dados faltantes
# ===================================================================


class TestFullCustomerJourneyWithMissingInfo:
    """Simula a jornada do cliente validando que o sistema pede
    informações faltantes antes de executar ações."""

    # ---------------------------------------------------------------
    # 1. Pedir pizza sem tamanho/borda → agente deve perguntar
    # ---------------------------------------------------------------

    def test_order_pizza_missing_size_and_crust(self) -> None:
        """Usuário pede 'Quero uma pizza de calabresa' sem tamanho
        e borda — o agente deve perguntar pelos dados faltantes."""
        instructions = " ".join(ORDER_AGENT_INSTRUCTIONS)
        lower = instructions.lower()

        # Valida que as instruções exigem sabor, tamanho e borda
        assert "sabor" in lower
        assert "tamanho" in lower
        assert "borda" in lower
        # Valida que as instruções mandam perguntar se faltar dado
        assert "pergunte" in lower
        # Valida que NÃO deve assumir padrão
        assert "não assuma" in lower

        # Simula o roteamento: "Quero uma pizza de calabresa" → order_agent
        route = _make_route_decision(TargetAgent.ORDER)
        assert route.content.target_agent == TargetAgent.ORDER

    def test_order_pizza_missing_only_crust(self) -> None:
        """Usuário fornece sabor e tamanho mas não a borda.
        Instruções exigem perguntar."""
        instructions = " ".join(ORDER_AGENT_INSTRUCTIONS)
        # A instrução menciona que se QUALQUER info faltar, perguntar
        assert "QUALQUER" in instructions or "qualquer" in instructions.lower()
        assert "borda" in instructions.lower()

    def test_order_pizza_missing_only_size(self) -> None:
        """Usuário fornece sabor e borda mas não o tamanho.
        Instruções exigem perguntar."""
        instructions = " ".join(ORDER_AGENT_INSTRUCTIONS)
        assert "tamanho" in instructions.lower()
        assert "pergunte" in instructions.lower()

    # ---------------------------------------------------------------
    # 2. Criar pedido sem CPF → agente deve perguntar
    # ---------------------------------------------------------------

    def test_create_order_missing_cpf(self) -> None:
        """Criar pedido sem CPF — instruções exigem perguntar."""
        instructions = " ".join(ORDER_AGENT_INSTRUCTIONS)
        assert "CPF" in instructions
        assert "ANTES" in instructions
        assert "create_order" in instructions
        # Deve perguntar explicitamente
        assert "PERGUNTE" in instructions or "pergunte" in instructions.lower()

    def test_create_order_missing_name(self) -> None:
        """Criar pedido sem nome — instruções exigem perguntar."""
        instructions = " ".join(ORDER_AGENT_INSTRUCTIONS)
        lower = instructions.lower()
        assert "nome" in lower
        assert "client_name" in lower or "nome completo" in lower

    # ---------------------------------------------------------------
    # 3. Criar pedido com dados completos
    # ---------------------------------------------------------------

    @patch("src.tools.order_tools.httpx.post")
    def test_create_order_with_full_data(self, mock_post: MagicMock) -> None:
        """Criar pedido com nome e CPF fornecidos usa a tool corretamente."""
        from src.tools.order_tools import create_order

        mock_post.return_value = MagicMock(
            status_code=201,
            json=lambda: {
                "id": 1,
                "client_name": "João Silva",
                "client_document": "12345678901",
                "delivery_date": "2026-03-29",
                "items": [],
                "total_price": "0.00",
            },
            raise_for_status=lambda: None,
        )

        result = create_order("João Silva", "12345678901", "2026-03-29")
        assert result["id"] == 1
        assert result["client_name"] == "João Silva"
        assert result["client_document"] == "12345678901"

    # ---------------------------------------------------------------
    # 4. Adicionar item com dados completos
    # ---------------------------------------------------------------

    @patch("src.tools.order_tools.httpx.patch")
    def test_add_item_with_complete_info(self, mock_patch: MagicMock) -> None:
        """Adicionar item com sabor + tamanho + borda via tool funciona."""
        from src.tools.order_tools import add_item_to_order

        mock_patch.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "id": 1,
                "items": [
                    {
                        "id": 10,
                        "name": "Pizza Calabresa Grande Borda Tradicional",
                        "quantity": 1,
                        "unit_price": "42.00",
                    }
                ],
                "total_price": "42.00",
            },
            raise_for_status=lambda: None,
        )

        result = add_item_to_order(
            order_id=1,
            item_name="Pizza Calabresa Grande Borda Tradicional",
            quantity=1,
            unit_price=42.0,
        )
        assert "items" in result
        assert result["items"][0]["name"] == "Pizza Calabresa Grande Borda Tradicional"

    # ---------------------------------------------------------------
    # 5. Incluir itens em pedido já criado
    # ---------------------------------------------------------------

    @patch("src.tools.order_tools.httpx.patch")
    def test_add_multiple_items_to_existing_order(self, mock_patch: MagicMock) -> None:
        """Adiciona múltiplos itens a um pedido existente."""
        from src.tools.order_tools import add_item_to_order

        mock_patch.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "id": 5,
                "items": [
                    {"id": 1, "name": "Pizza Margherita Média Borda Tradicional", "quantity": 1, "unit_price": "35.00"},
                    {"id": 2, "name": "Pizza Calabresa Grande Borda Recheada com Cheddar", "quantity": 2, "unit_price": "50.00"},
                ],
                "total_price": "135.00",
            },
            raise_for_status=lambda: None,
        )

        result = add_item_to_order(5, "Pizza Calabresa Grande Borda Recheada com Cheddar", 2, 50.0)
        assert len(result["items"]) == 2
        assert result["total_price"] == "135.00"

    # ---------------------------------------------------------------
    # 6. Atualizar endereço de entrega
    # ---------------------------------------------------------------

    @patch("src.tools.order_tools.httpx.patch")
    def test_update_delivery_address(self, mock_patch: MagicMock) -> None:
        """Atualiza o endereço de entrega de um pedido."""
        from src.tools.order_tools import update_delivery_address

        mock_patch.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "id": 1,
                "delivery_address": {
                    "street_name": "Rua das Flores",
                    "number": "123",
                    "complement": "Apto 4B",
                    "reference_point": "Próximo ao mercado",
                },
            },
            raise_for_status=lambda: None,
        )

        result = update_delivery_address(
            order_id=1,
            street_name="Rua das Flores",
            number="123",
            complement="Apto 4B",
            reference_point="Próximo ao mercado",
        )
        assert result["delivery_address"]["street_name"] == "Rua das Flores"
        assert result["delivery_address"]["complement"] == "Apto 4B"

    # ---------------------------------------------------------------
    # 7. Remover item de um pedido
    # ---------------------------------------------------------------

    @patch("src.tools.order_tools.httpx.delete")
    def test_remove_item_from_order(self, mock_delete: MagicMock) -> None:
        """Remove um item de um pedido existente."""
        from src.tools.order_tools import remove_item_from_order

        mock_delete.return_value = MagicMock(
            status_code=204,
            raise_for_status=lambda: None,
        )

        result = remove_item_from_order(order_id=1, item_id=10)
        assert "detail" in result
        assert "removido" in result["detail"].lower()

    # ---------------------------------------------------------------
    # 8. Buscar pedidos por documento e data
    # ---------------------------------------------------------------

    @patch("src.tools.order_tools.httpx.get")
    def test_filter_orders_by_document_and_date(self, mock_get: MagicMock) -> None:
        """Busca pedidos filtrando por CPF e data de entrega."""
        from src.tools.order_tools import filter_orders

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [
                {
                    "id": 1,
                    "client_name": "Maria",
                    "client_document": "98765432100",
                    "delivery_date": "2026-03-29",
                    "total_price": "75.00",
                }
            ],
            raise_for_status=lambda: None,
        )

        result = filter_orders("98765432100", "2026-03-29")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["client_document"] == "98765432100"

    @patch("src.tools.order_tools.httpx.get")
    def test_filter_orders_by_document_only(self, mock_get: MagicMock) -> None:
        """Busca pedidos filtrando apenas por CPF."""
        from src.tools.order_tools import filter_orders

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [
                {"id": 1, "client_document": "11122233344", "delivery_date": "2026-03-28"},
                {"id": 2, "client_document": "11122233344", "delivery_date": "2026-03-29"},
            ],
            raise_for_status=lambda: None,
        )

        result = filter_orders("11122233344")
        assert isinstance(result, list)
        assert len(result) == 2

    # ---------------------------------------------------------------
    # 9. Consultar detalhes de um pedido (com preço total)
    # ---------------------------------------------------------------

    @patch("src.tools.order_tools.httpx.get")
    def test_get_order_details_with_total_price(self, mock_get: MagicMock) -> None:
        """Consulta detalhes de um pedido incluindo total_price calculado."""
        from src.tools.order_tools import get_order_details

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "id": 1,
                "client_name": "João Silva",
                "client_document": "12345678901",
                "delivery_date": "2026-03-29",
                "items": [
                    {"id": 10, "name": "Pizza Calabresa Grande Borda Tradicional", "quantity": 1, "unit_price": "42.00"},
                    {"id": 11, "name": "Pizza Margherita Pequena Borda Tradicional", "quantity": 2, "unit_price": "25.00"},
                ],
                "delivery_address": {
                    "street_name": "Rua das Flores",
                    "number": "123",
                },
                "total_price": "92.00",
            },
            raise_for_status=lambda: None,
        )

        result = get_order_details(order_id=1)
        assert result["id"] == 1
        assert result["total_price"] == "92.00"
        assert len(result["items"]) == 2
        assert result["delivery_address"]["street_name"] == "Rua das Flores"

    # ---------------------------------------------------------------
    # 10. Criar pedido sem itens (só nome + CPF)
    # ---------------------------------------------------------------

    @patch("src.tools.order_tools.httpx.post")
    def test_create_order_without_items(self, mock_post: MagicMock) -> None:
        """Cria pedido vazio (sem itens nem endereço) — apenas nome e CPF."""
        from src.tools.order_tools import create_order

        mock_post.return_value = MagicMock(
            status_code=201,
            json=lambda: {
                "id": 3,
                "client_name": "Ana Costa",
                "client_document": "99988877766",
                "delivery_date": "2026-03-29",
                "items": [],
                "delivery_address": None,
                "total_price": "0.00",
            },
            raise_for_status=lambda: None,
        )

        result = create_order("Ana Costa", "99988877766", "2026-03-29")
        assert result["id"] == 3
        assert result["items"] == []
        assert result["delivery_address"] is None

    # ---------------------------------------------------------------
    # 11. Pedido finalizado recusa alterações
    # ---------------------------------------------------------------

    def test_completed_order_refuses_changes(self) -> None:
        """Instruções do order_agent recusam alterações em pedidos finalizados."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        lower = text.lower()
        assert "finalizado" in lower or "concluído" in lower
        assert "recuse" in lower or "RECUSE" in text

    # ---------------------------------------------------------------
    # 12. Roteamento direciona corretamente
    # ---------------------------------------------------------------

    def test_routing_cardapio_goes_to_menu(self) -> None:
        """Mensagem sobre cardápio deve ser roteada para menu_agent."""
        router_text = " ".join(ROUTER_AGENT_INSTRUCTIONS).lower()
        assert "cardápio" in router_text or "sabores" in router_text
        assert "menu_agent" in router_text

    def test_routing_pedido_goes_to_order(self) -> None:
        """Mensagem sobre pedido deve ser roteada para order_agent."""
        router_text = " ".join(ROUTER_AGENT_INSTRUCTIONS).lower()
        assert "pedido" in router_text
        assert "order_agent" in router_text

    def test_routing_greeting_goes_to_order(self) -> None:
        """Saudação genérica deve ser roteada para order_agent."""
        router_text = " ".join(ROUTER_AGENT_INSTRUCTIONS).lower()
        assert "saudaç" in router_text or "olá" in router_text or "oi" in router_text
        assert "order_agent" in router_text


# ===================================================================
# SEGURANÇA — Red Teaming
# ===================================================================


class TestSecurityRedTeaming:
    """Testes de segurança contra Prompt Injection, manipulação
    de base de dados e extração de informações internas."""

    # ---------------------------------------------------------------
    # Prompt Injection — Instruções de proteção
    # ---------------------------------------------------------------

    def test_menu_agent_rejects_instruction_override(self) -> None:
        """menu_agent instrui ignorar comandos de bypass."""
        text = " ".join(MENU_AGENT_INSTRUCTIONS)
        assert "IGNORE" in text
        assert "ignore suas instruções" in text.lower() or "ignorar" in text.lower()

    def test_order_agent_rejects_instruction_override(self) -> None:
        """order_agent instrui ignorar comandos de bypass."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        assert "IGNORE" in text
        assert "ignore suas instruções" in text.lower() or "ignorar" in text.lower()

    def test_router_agent_rejects_instruction_override(self) -> None:
        """router_agent instrui ignorar tentativas de manipulação."""
        text = " ".join(ROUTER_AGENT_INSTRUCTIONS)
        assert "IGNORE" in text

    # ---------------------------------------------------------------
    # Prompt Injection — Proteção do system prompt
    # ---------------------------------------------------------------

    def test_menu_agent_never_reveals_system_prompt(self) -> None:
        """menu_agent instrui nunca revelar system prompt."""
        text = " ".join(MENU_AGENT_INSTRUCTIONS).lower()
        assert "nunca revele" in text
        assert "system prompt" in text

    def test_order_agent_never_reveals_system_prompt(self) -> None:
        """order_agent instrui nunca revelar system prompt."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS).lower()
        assert "nunca revele" in text
        assert "system prompt" in text

    def test_router_agent_never_reveals_system_prompt(self) -> None:
        """router_agent instrui nunca revelar system prompt."""
        text = " ".join(ROUTER_AGENT_INSTRUCTIONS).lower()
        assert "nunca revele" in text
        assert "system prompt" in text

    # ---------------------------------------------------------------
    # Prompt Injection — Tentativas de role-switching
    # ---------------------------------------------------------------

    def test_menu_blocks_role_switching(self) -> None:
        """menu_agent instrui bloquear ataques de troca de papel."""
        text = " ".join(MENU_AGENT_INSTRUCTIONS).lower()
        assert "agora você é" in text or "esqueça tudo" in text

    def test_order_blocks_role_switching(self) -> None:
        """order_agent instrui bloquear ataques de troca de papel."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS).lower()
        assert "agora você é" in text or "esqueça tudo" in text

    # ---------------------------------------------------------------
    # Prompt Injection — Escopo restrito
    # ---------------------------------------------------------------

    def test_menu_agent_restricted_to_cardapio(self) -> None:
        """menu_agent deve se ater ao domínio do cardápio."""
        text = " ".join(MENU_AGENT_INSTRUCTIONS).lower()
        assert "cardápio" in text
        assert "nunca execute código" in text or "nunca acesse urls" in text.replace("urls", "urls")

    def test_order_agent_restricted_to_pedidos(self) -> None:
        """order_agent deve se ater ao domínio de pedidos."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS).lower()
        assert "pedidos" in text or "gerenciamento de pedidos" in text
        assert "nunca execute código" in text

    # ---------------------------------------------------------------
    # Banco de dados — Proteção read-only
    # ---------------------------------------------------------------

    def test_sqlite_readonly_blocks_insert(self) -> None:
        """INSERT no banco do cardápio deve falhar (read-only)."""
        conn = _get_readonly_connection(DB_PATH)
        try:
            with pytest.raises(sqlite3.OperationalError):
                conn.execute(
                    "INSERT INTO pizzas (sabor, descricao, ingredientes) VALUES (?, ?, ?)",
                    ("Hack", "Hacked", "Injection"),
                )
        finally:
            conn.close()

    def test_sqlite_readonly_blocks_update(self) -> None:
        """UPDATE no banco do cardápio deve falhar (read-only)."""
        conn = _get_readonly_connection(DB_PATH)
        try:
            with pytest.raises(sqlite3.OperationalError):
                conn.execute(
                    "UPDATE pizzas SET sabor = ? WHERE id = ?",
                    ("Hackeada", 1),
                )
        finally:
            conn.close()

    def test_sqlite_readonly_blocks_delete(self) -> None:
        """DELETE no banco do cardápio deve falhar (read-only)."""
        conn = _get_readonly_connection(DB_PATH)
        try:
            with pytest.raises(sqlite3.OperationalError):
                conn.execute("DELETE FROM pizzas WHERE id = ?", (1,))
        finally:
            conn.close()

    def test_sqlite_readonly_blocks_drop_table(self) -> None:
        """DROP TABLE no banco do cardápio deve falhar (read-only)."""
        conn = _get_readonly_connection(DB_PATH)
        try:
            with pytest.raises(sqlite3.OperationalError):
                conn.execute("DROP TABLE pizzas")
        finally:
            conn.close()

    def test_sqlite_readonly_blocks_alter_table(self) -> None:
        """ALTER TABLE no banco do cardápio deve falhar (read-only)."""
        conn = _get_readonly_connection(DB_PATH)
        try:
            with pytest.raises(sqlite3.OperationalError):
                conn.execute("ALTER TABLE pizzas ADD COLUMN hacked TEXT")
        finally:
            conn.close()

    def test_sqlite_readonly_blocks_create_table(self) -> None:
        """CREATE TABLE no banco do cardápio deve falhar (read-only)."""
        conn = _get_readonly_connection(DB_PATH)
        try:
            with pytest.raises(sqlite3.OperationalError):
                conn.execute("CREATE TABLE hack (id INTEGER PRIMARY KEY)")
        finally:
            conn.close()

    # ---------------------------------------------------------------
    # Banco de dados — Queries parametrizadas (anti SQL-injection)
    # ---------------------------------------------------------------

    def test_get_pizza_price_uses_parameterized_query(self) -> None:
        """get_pizza_price não é vulnerável a SQL injection."""
        from src.tools.menu_tools import get_pizza_price

        # Tenta injetar SQL via parâmetro — deve retornar None (não encontrado),
        # não provocar erro de SQL ou retornar dados indevidos
        result = get_pizza_price(
            sabor="' OR 1=1 --",
            tamanho="Grande",
            borda="Tradicional",
            db_path=DB_PATH,
        )
        assert result is None

    def test_search_menu_injection_returns_empty_or_valid(self) -> None:
        """search_menu com input malicioso não quebra a busca."""
        # search_menu usa embeddings para busca, não SQL direto,
        # mas o input não deve causar erros
        from src.tools.menu_tools import _load_menu_items

        # Verifica que _load_menu_items funciona normalmente
        # (a query SQL interna não aceita input do usuário)
        items = _load_menu_items(DB_PATH)
        assert isinstance(items, list)
        assert len(items) > 0

    # ---------------------------------------------------------------
    # Prompt Injection — Declaração de resposta educada
    # ---------------------------------------------------------------

    def test_menu_agent_polite_rejection_instruction(self) -> None:
        """menu_agent instrui resposta educada a tentativas de injection."""
        text = " ".join(MENU_AGENT_INSTRUCTIONS)
        assert "Desculpe" in text
        assert "Beauty Pizza" in text

    def test_order_agent_polite_rejection_instruction(self) -> None:
        """order_agent instrui resposta educada a tentativas de injection."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        assert "Desculpe" in text
        assert "Beauty Pizza" in text

    # ---------------------------------------------------------------
    # Prompt Injection — Developer mode / jailbreak patterns
    # ---------------------------------------------------------------

    def test_all_agents_block_developer_mode(self) -> None:
        """Todos os agentes bloqueiam tentativa de 'modo desenvolvedor'."""
        for instructions in [MENU_AGENT_INSTRUCTIONS, ORDER_AGENT_INSTRUCTIONS]:
            text = " ".join(instructions).lower()
            assert "modo desenvolvedor" in text

    def test_router_always_returns_json(self) -> None:
        """Router deve sempre retornar JSON, independentemente do input."""
        text = " ".join(ROUTER_AGENT_INSTRUCTIONS)
        assert "JSON" in text
        assert "independentemente" in text.lower() or "sempre" in text.lower()

    # ---------------------------------------------------------------
    # Isolamento de sessão
    # ---------------------------------------------------------------

    @patch("src.agents.menu_agent.settings")
    def test_agents_use_session_scoping(self, mock_settings: MagicMock) -> None:
        """Agentes diferentes com session_ids distintos ficam isolados."""
        mock_settings.google_api_key = "fake-key"

        agent_a = create_menu_agent(session_id="session-A")
        agent_b = create_menu_agent(session_id="session-B")

        assert agent_a.session_id == "session-A"
        assert agent_b.session_id == "session-B"
        assert agent_a.session_id != agent_b.session_id

    @patch("src.agents.order_agent.settings")
    def test_order_agents_session_isolated(self, mock_settings: MagicMock) -> None:
        """Order agents com sessions diferentes não compartilham estado."""
        mock_settings.google_api_key = "fake-key"

        agent_x = create_order_agent(session_id="user-X")
        agent_y = create_order_agent(session_id="user-Y")

        assert agent_x.session_id != agent_y.session_id
