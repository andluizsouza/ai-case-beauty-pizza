"""Testes dos agentes da Beauty Pizza.

Foco em validar:
- Configuração correta dos agentes (tools, instructions, output_schema).
- Modelo de roteamento (RouteDecision / TargetAgent).
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

    def test_invalid_agent_name_rejected(self) -> None:
        """Rejeita nome de agente inválido."""
        with pytest.raises(ValueError):
            RouteDecision(target_agent="unknown_agent")


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

    def test_router_instructions_routing_rules(self) -> None:
        """Instruções do router mencionam agentes e regras de roteamento."""
        text = " ".join(ROUTER_AGENT_INSTRUCTIONS)
        lower = text.lower()
        assert "menu_agent" in text
        assert "order_agent" in text
        assert "sabor" in lower
        assert "confirma" in lower
        assert "mantenha" in lower

    def test_router_instructions_security(self) -> None:
        """Instruções contêm proteção anti-injection e formato JSON obrigatório."""
        text = " ".join(ROUTER_AGENT_INSTRUCTIONS)
        lower = text.lower()
        assert "IGNORE" in text
        assert "nunca revele" in lower
        assert "system prompt" in lower
        assert "JSON" in text


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

    def test_menu_instructions_business_rules(self) -> None:
        """Instruções definem fluxo de atendimento do cardápio."""
        text = " ".join(MENU_AGENT_INSTRUCTIONS)
        lower = text.lower()
        assert "primeiro contato" in lower
        assert "validar" in lower
        assert "get_pizza_price" in text
        assert "alternativas" in lower or "sugi" in lower
        assert "Pizza [Sabor] [Tamanho] Borda [Borda]" in text
        assert "R$" in text

    def test_menu_instructions_security(self) -> None:
        """Instruções contêm proteções anti-injection e escopo restrito."""
        text = " ".join(MENU_AGENT_INSTRUCTIONS)
        lower = text.lower()
        assert "IGNORE" in text
        assert "nunca revele" in lower
        assert "system prompt" in lower
        assert "cardápio" in lower
        assert "Desculpe" in text


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

    def test_order_instructions_data_requirements(self) -> None:
        """Instruções exigem dados completos antes de executar ações."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        lower = text.lower()
        assert "CPF" in text
        assert "ANTES" in text
        assert "create_order" in text
        assert "NÃO assuma" in text
        assert "pergunte" in lower
        assert "sabor" in lower
        assert "tamanho" in lower
        assert "borda" in lower

    def test_order_instructions_lifecycle(self) -> None:
        """Instruções definem ciclo de vida completo do pedido."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        lower = text.lower()
        assert "create_order" in text
        assert "endereço de entrega" in lower
        assert "update_delivery_address" in text
        assert "get_order_details" in text
        assert "finalizado" in lower
        assert "Contexto do cardápio" in text

    def test_order_instructions_item_format(self) -> None:
        """Formato do nome do item segue padrão definido."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        assert "Pizza [Sabor] [Tamanho] Borda [Tipo da Borda]" in text

    def test_order_instructions_security(self) -> None:
        """Instruções contêm proteções anti-injection e ocultam separação interna."""
        text = " ".join(ORDER_AGENT_INSTRUCTIONS)
        lower = text.lower()
        assert "IGNORE" in text
        assert "nunca revele" in lower
        assert "system prompt" in lower
        assert "atendente contínuo" in lower
        assert "Desculpe" in text


# ===================================================================
# Segurança — Instruções anti-injection (todos os agentes)
# ===================================================================


class TestAgentSecurityInstructions:
    """Proteções contra prompt injection presentes em todos os agentes."""

    @pytest.mark.parametrize(
        "instructions",
        [MENU_AGENT_INSTRUCTIONS, ORDER_AGENT_INSTRUCTIONS],
        ids=["menu_agent", "order_agent"],
    )
    def test_blocks_role_switching(self, instructions: list[str]) -> None:
        """Agentes bloqueiam ataques de troca de papel."""
        text = " ".join(instructions).lower()
        assert "agora você é" in text or "esqueça tudo" in text

    @pytest.mark.parametrize(
        "instructions",
        [MENU_AGENT_INSTRUCTIONS, ORDER_AGENT_INSTRUCTIONS],
        ids=["menu_agent", "order_agent"],
    )
    def test_blocks_developer_mode(self, instructions: list[str]) -> None:
        """Agentes bloqueiam tentativa de 'modo desenvolvedor'."""
        text = " ".join(instructions).lower()
        assert "modo desenvolvedor" in text

    @pytest.mark.parametrize(
        "instructions",
        [MENU_AGENT_INSTRUCTIONS, ORDER_AGENT_INSTRUCTIONS],
        ids=["menu_agent", "order_agent"],
    )
    def test_restricts_scope(self, instructions: list[str]) -> None:
        """Agentes restringem escopo e bloqueiam execução de código."""
        text = " ".join(instructions).lower()
        assert "nunca execute código" in text

    @patch("src.agents.menu_agent.settings")
    @patch("src.agents.order_agent.settings")
    def test_session_isolation(
        self, mock_order: MagicMock, mock_menu: MagicMock
    ) -> None:
        """Agentes com sessions diferentes não compartilham estado."""
        mock_order.google_api_key = "fake-key"
        mock_menu.google_api_key = "fake-key"
        agent_a = create_menu_agent(session_id="session-A")
        agent_b = create_order_agent(session_id="session-B")
        assert agent_a.session_id == "session-A"
        assert agent_b.session_id == "session-B"
        assert agent_a.session_id != agent_b.session_id
