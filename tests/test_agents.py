"""Testes dos agentes da Beauty Pizza.

Foco em validar:
- Configuração correta dos agentes (tools, instructions, output_schema).
- Modelo de roteamento (RouteDecision / TargetAgent).
- Regras do order_agent: exigir dados faltantes (sabor, tamanho, borda, CPF).
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
        mock_settings.gemini_api_key = "fake-key"
        agent = create_router_agent()
        assert agent.tools is None or agent.tools == []

    @patch("src.agents.router_agent.settings")
    def test_router_has_structured_output(self, mock_settings: MagicMock) -> None:
        """Router agent deve usar RouteDecision como output_schema."""
        mock_settings.gemini_api_key = "fake-key"
        agent = create_router_agent()
        assert agent.output_schema is RouteDecision

    @patch("src.agents.router_agent.settings")
    def test_router_name(self, mock_settings: MagicMock) -> None:
        """Router agent deve ter o nome 'router_agent'."""
        mock_settings.gemini_api_key = "fake-key"
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
        assert "IGNORE" in text or "ignore" in text
        assert "system prompt" in text.lower()


# ===================================================================
# Menu Agent — Configuração
# ===================================================================


class TestMenuAgent:
    """Testes de configuração do menu_agent."""

    @patch("src.agents.menu_agent.settings")
    def test_menu_agent_has_tools(self, mock_settings: MagicMock) -> None:
        """Menu agent deve possuir tools de cardápio."""
        mock_settings.gemini_api_key = "fake-key"
        agent = create_menu_agent()
        tool_names = [t.__name__ for t in agent.tools]
        assert "get_menu_report" in tool_names
        assert "search_menu" in tool_names
        assert "get_pizza_price" in tool_names

    @patch("src.agents.menu_agent.settings")
    def test_menu_agent_name(self, mock_settings: MagicMock) -> None:
        """Menu agent deve ter o nome 'menu_agent'."""
        mock_settings.gemini_api_key = "fake-key"
        agent = create_menu_agent()
        assert agent.name == "menu_agent"

    @patch("src.agents.menu_agent.settings")
    def test_menu_agent_with_session(self, mock_settings: MagicMock) -> None:
        """Menu agent aceita session_id."""
        mock_settings.gemini_api_key = "fake-key"
        agent = create_menu_agent(session_id="test-session-123")
        assert agent.session_id == "test-session-123"

    def test_menu_instructions_security(self) -> None:
        """Instruções do menu_agent contêm proteção contra prompt injection."""
        text = " ".join(MENU_AGENT_INSTRUCTIONS)
        assert "IGNORE" in text
        assert "system prompt" in text.lower()

    def test_menu_instructions_scope(self) -> None:
        """Instruções limitam escopo ao cardápio."""
        text = " ".join(MENU_AGENT_INSTRUCTIONS)
        assert "cardápio" in text.lower()
        assert "search_menu" in text


# ===================================================================
# Order Agent — Configuração
# ===================================================================


class TestOrderAgent:
    """Testes de configuração do order_agent."""

    @patch("src.agents.order_agent.settings")
    def test_order_agent_has_tools(self, mock_settings: MagicMock) -> None:
        """Order agent deve possuir todas as tools de pedidos."""
        mock_settings.gemini_api_key = "fake-key"
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
        mock_settings.gemini_api_key = "fake-key"
        agent = create_order_agent()
        assert agent.name == "order_agent"

    @patch("src.agents.order_agent.settings")
    def test_order_agent_with_session(self, mock_settings: MagicMock) -> None:
        """Order agent aceita session_id."""
        mock_settings.gemini_api_key = "fake-key"
        agent = create_order_agent(session_id="session-abc")
        assert agent.session_id == "session-abc"

    def test_order_instructions_security(self) -> None:
        """Instruções do order_agent contêm proteção contra prompt injection."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        assert "IGNORE" in text
        assert "system prompt" in text.lower()


# ===================================================================
# Order Agent — Regras de Dados Obrigatórios
# ===================================================================


class TestOrderAgentDataRequirements:
    """Testes que validam se as instruções do order_agent exigem
    dados obrigatórios antes de chamar as tools."""

    def test_instructions_require_cpf_before_create(self) -> None:
        """Instruções exigem CPF antes de criar pedido."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        assert "CPF" in text or "client_document" in text
        assert "create_order" in text
        # Deve exigir o documento ANTES de criar
        assert "ANTES" in text or "antes" in text

    def test_instructions_require_sabor(self) -> None:
        """Instruções exigem sabor antes de adicionar item."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        lower = text.lower()
        assert "sabor" in lower

    def test_instructions_require_tamanho(self) -> None:
        """Instruções exigem tamanho antes de adicionar item."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        lower = text.lower()
        assert "tamanho" in lower

    def test_instructions_require_borda(self) -> None:
        """Instruções exigem borda antes de adicionar item."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        lower = text.lower()
        assert "borda" in lower

    def test_instructions_ask_user_if_missing(self) -> None:
        """Instruções dizem para perguntar ao usuário se dados faltam."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        lower = text.lower()
        assert "pergunte" in lower or "pergunt" in lower

    def test_instructions_no_default_values(self) -> None:
        """Instruções proíbem assumir valores padrão."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        assert "NÃO assuma" in text or "não assuma" in text.lower()

    def test_instructions_require_all_three_before_add_item(self) -> None:
        """Instruções exigem sabor, tamanho E borda juntos para add_item."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        lower = text.lower()
        # Todas as 3 informações devem estar mencionadas no contexto de add_item
        assert "sabor" in lower
        assert "tamanho" in lower
        assert "borda" in lower
        assert "add_item_to_order" in text

    def test_instructions_refuse_completed_orders(self) -> None:
        """Instruções mandam recusar alterações em pedidos finalizados."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        lower = text.lower()
        assert "finalizado" in lower or "concluído" in lower
        assert "recuse" in lower or "RECUSE" in text

    def test_instructions_item_name_format(self) -> None:
        """Instruções definem formato do nome do item."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        assert "Pizza [Sabor] [Tamanho] Borda [Tipo da Borda]" in text
