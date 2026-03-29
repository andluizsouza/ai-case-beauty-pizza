"""Testes dos agentes da Beauty Pizza.

Foco em validar:
- Configuração correta dos agentes (tools, instructions, output_schema).
- Modelo de roteamento (RouteDecision / TargetAgent).
- Fluxo: menu_agent como gateway de validação, order_agent para gestão.
- Proteção contra prompt injection nos prompts dos agentes.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.agents.menu_agent import MENU_AGENT_INSTRUCTIONS, create_menu_agent
from src.agents.order_agent import ORDER_AGENT_INSTRUCTIONS, create_order_agent
from src.agents.router_agent import ROUTER_AGENT_INSTRUCTIONS, create_router_agent
from src.models.routing import RouteDecision, TargetAgent


# ===================================================================
# RouteDecision — Modelo Pydantic
# ===================================================================


class TestRouteDecision:
    """Testes do modelo de decisão de roteamento."""

    def test_valid_menu_agent(self) -> None:
        """Roteamento válido para menu_agent."""
        decision = RouteDecision(target_agent=TargetAgent.MENU)
        assert decision.target_agent == TargetAgent.MENU
        assert decision.target_agent.value == "menu_agent"

    def test_valid_order_agent(self) -> None:
        """Roteamento válido para order_agent."""
        decision = RouteDecision(target_agent=TargetAgent.ORDER)
        assert decision.target_agent == TargetAgent.ORDER
        assert decision.target_agent.value == "order_agent"

    def test_from_string_value(self) -> None:
        """Cria RouteDecision a partir de string (simulando output do LLM)."""
        decision = RouteDecision(target_agent="menu_agent")
        assert decision.target_agent == TargetAgent.MENU

    def test_invalid_agent_name_rejected(self) -> None:
        """Rejeita nome de agente inválido."""
        with pytest.raises(ValueError):
            RouteDecision(target_agent="unknown_agent")

    def test_json_serialization(self) -> None:
        """Serialização JSON contém target_agent correto."""
        decision = RouteDecision(target_agent=TargetAgent.ORDER)
        data = decision.model_dump()
        assert data == {"target_agent": "order_agent"}

    def test_json_deserialization(self) -> None:
        """Deserialização JSON reconstrói RouteDecision."""
        data = {"target_agent": "menu_agent"}
        decision = RouteDecision.model_validate(data)
        assert decision.target_agent == TargetAgent.MENU


# ===================================================================
# Router Agent — Configuração
# ===================================================================


class TestRouterAgent:
    """Testes de configuração do router_agent."""

    @patch("src.agents.router_agent.settings")
    def test_router_has_no_tools(self, mock_settings: MagicMock) -> None:
        """Router agent não deve possuir tools."""
        mock_settings.google_api_key = "fake-key"
        agent = create_router_agent()
        assert agent.tools is None or agent.tools == []

    @patch("src.agents.router_agent.settings")
    def test_router_has_structured_output(self, mock_settings: MagicMock) -> None:
        """Router agent deve usar RouteDecision como output_schema."""
        mock_settings.google_api_key = "fake-key"
        agent = create_router_agent()
        assert agent.output_schema is RouteDecision

    @patch("src.agents.router_agent.settings")
    def test_router_name(self, mock_settings: MagicMock) -> None:
        """Router agent deve ter o nome 'router_agent'."""
        mock_settings.google_api_key = "fake-key"
        agent = create_router_agent()
        assert agent.name == "router_agent"

    def test_router_instructions_contain_agents(self) -> None:
        """Instruções do router mencionam os dois agentes disponíveis."""
        text = " ".join(ROUTER_AGENT_INSTRUCTIONS)
        assert "menu_agent" in text
        assert "order_agent" in text

    def test_router_instructions_security(self) -> None:
        """Instruções do router contêm proteção contra prompt injection."""
        text = " ".join(ROUTER_AGENT_INSTRUCTIONS)
        assert "IGNORE" in text
        assert "system prompt" in text.lower()

    def test_router_sends_greetings_to_menu(self) -> None:
        """Saudações devem ir para menu_agent (primeiro contato)."""
        text = " ".join(ROUTER_AGENT_INSTRUCTIONS)
        lower = text.lower()
        assert "saudaç" in lower or "olá" in lower or "oi" in lower
        assert "menu_agent" in text

    def test_router_sends_flavors_to_menu(self) -> None:
        """Menção a sabores, preços ou cardápio deve ir para menu_agent."""
        text = " ".join(ROUTER_AGENT_INSTRUCTIONS)
        lower = text.lower()
        assert "sabor" in lower
        assert "menu_agent" in text

    def test_router_sends_confirmation_to_order(self) -> None:
        """Confirmação de item validado deve ir para order_agent."""
        text = " ".join(ROUTER_AGENT_INSTRUCTIONS)
        lower = text.lower()
        assert "confirma" in lower
        assert "order_agent" in text

    def test_router_keeps_order_agent_during_flow(self) -> None:
        """Router mantém order_agent durante coleta de dados (nome, CPF, endereço)."""
        text = " ".join(ROUTER_AGENT_INSTRUCTIONS)
        lower = text.lower()
        assert "mantenha em order_agent" in lower or "mantenha" in lower
        assert "nome" in lower or "cpf" in lower or "endereço" in lower


# ===================================================================
# Menu Agent — Configuração
# ===================================================================


class TestMenuAgent:
    """Testes de configuração do menu_agent."""

    @patch("src.agents.menu_agent.settings")
    def test_menu_agent_has_tools(self, mock_settings: MagicMock) -> None:
        """Menu agent deve possuir tools de cardápio."""
        mock_settings.google_api_key = "fake-key"
        agent = create_menu_agent()
        tool_names = [t.__name__ for t in agent.tools]
        assert "get_menu_report" in tool_names
        assert "search_menu" in tool_names
        assert "get_pizza_price" in tool_names

    @patch("src.agents.menu_agent.settings")
    def test_menu_agent_name(self, mock_settings: MagicMock) -> None:
        """Menu agent deve ter o nome 'menu_agent'."""
        mock_settings.google_api_key = "fake-key"
        agent = create_menu_agent()
        assert agent.name == "menu_agent"

    @patch("src.agents.menu_agent.settings")
    def test_menu_agent_with_session(self, mock_settings: MagicMock) -> None:
        """Menu agent aceita session_id."""
        mock_settings.google_api_key = "fake-key"
        agent = create_menu_agent(session_id="test-session-123")
        assert agent.session_id == "test-session-123"

    def test_menu_instructions_security(self) -> None:
        """Instruções do menu_agent contêm proteção contra prompt injection."""
        text = " ".join(MENU_AGENT_INSTRUCTIONS)
        assert "IGNORE" in text
        assert "prompt" in text.lower()

    def test_menu_is_first_contact(self) -> None:
        """Menu agent é o primeiro contato do cliente."""
        text = " ".join(MENU_AGENT_INSTRUCTIONS)
        lower = text.lower()
        assert "primeiro contato" in lower

    def test_menu_validates_before_order(self) -> None:
        """Menu agent valida item antes de encaminhar para pedido."""
        text = " ".join(MENU_AGENT_INSTRUCTIONS)
        lower = text.lower()
        assert "validar" in lower
        assert "get_pizza_price" in text

    def test_menu_suggests_alternatives(self) -> None:
        """Menu agent sugere alternativas quando item não existe."""
        text = " ".join(MENU_AGENT_INSTRUCTIONS)
        lower = text.lower()
        assert "alternativas" in lower or "sugi" in lower

    def test_menu_presents_summary(self) -> None:
        """Menu agent apresenta resumo com preço antes de confirmar."""
        text = " ".join(MENU_AGENT_INSTRUCTIONS)
        assert "Pizza [Sabor] [Tamanho] Borda [Borda]" in text
        assert "R$" in text


# ===================================================================
# Order Agent — Configuração
# ===================================================================


class TestOrderAgent:
    """Testes de configuração do order_agent."""

    @patch("src.agents.order_agent.settings")
    def test_order_agent_has_tools(self, mock_settings: MagicMock) -> None:
        """Order agent deve possuir todas as tools de pedidos."""
        mock_settings.google_api_key = "fake-key"
        agent = create_order_agent()
        tool_names = [t.__name__ for t in agent.tools]
        assert "get_menu_report" not in tool_names
        assert "get_pizza_price" in tool_names
        assert "create_order" in tool_names
        assert "add_item_to_order" in tool_names
        assert "remove_item_from_order" in tool_names
        assert "update_delivery_address" in tool_names
        assert "get_order_details" in tool_names
        assert "filter_orders" in tool_names

    @patch("src.agents.order_agent.settings")
    def test_order_agent_name(self, mock_settings: MagicMock) -> None:
        """Order agent deve ter o nome 'order_agent'."""
        mock_settings.google_api_key = "fake-key"
        agent = create_order_agent()
        assert agent.name == "order_agent"

    @patch("src.agents.order_agent.settings")
    def test_order_agent_with_session(self, mock_settings: MagicMock) -> None:
        """Order agent aceita session_id."""
        mock_settings.google_api_key = "fake-key"
        agent = create_order_agent(session_id="session-abc")
        assert agent.session_id == "session-abc"

    def test_order_instructions_security(self) -> None:
        """Instruções do order_agent contêm proteção contra prompt injection."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        assert "IGNORE" in text
        assert "prompt" in text.lower()

    def test_order_never_exposes_internal_separation(self) -> None:
        """Order agent nunca expõe a separação interna de agentes."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        lower = text.lower()
        assert "nunca exponha" in lower or "nunca" in lower
        assert "atendente contínuo" in lower

    def test_order_requires_cpf_before_create(self) -> None:
        """Instruções exigem CPF antes de criar pedido."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        assert "CPF" in text
        assert "create_order" in text

    def test_order_enforces_lifecycle(self) -> None:
        """Pedido só existe após create_order retornar ID."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        lower = text.lower()
        assert "create_order" in text
        assert "order_id" in lower or "id" in lower
        assert "nunca diga" in lower or "não está feito" in lower

    def test_order_requires_address_before_finalize(self) -> None:
        """Deve pedir endereço antes de finalizar o pedido."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        lower = text.lower()
        assert "endereço de entrega" in lower
        assert "update_delivery_address" in text

    def test_order_shows_summary_with_get_order_details(self) -> None:
        """Deve usar get_order_details para resumo final."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        assert "get_order_details" in text

    def test_order_uses_menu_context(self) -> None:
        """Order agent utiliza contexto do cardápio para adicionar itens."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        assert "Contexto do cardápio" in text

    def test_order_item_name_format(self) -> None:
        """Instruções definem formato do nome do item."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        assert "Pizza [Sabor] [Tamanho] Borda [Tipo da Borda]" in text

    def test_order_refuses_completed_orders(self) -> None:
        """Instruções mandam recusar alterações em pedidos finalizados."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        assert "RECUSE" in text or "finalizado" in text.lower()

    def test_order_no_default_values(self) -> None:
        """Instruções proíbem assumir valores padrão."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        assert "NÃO assuma" in text

