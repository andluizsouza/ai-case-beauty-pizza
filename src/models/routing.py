"""Modelos Pydantic para decisão de roteamento do router_agent."""

from enum import Enum

from pydantic import BaseModel, Field


class TargetAgent(str, Enum):
    """Agentes disponíveis para roteamento."""

    MENU = "menu_agent"
    ORDER = "order_agent"


class RouteDecision(BaseModel):
    """Resultado estruturado da decisão de roteamento.

    O ``router_agent`` retorna este modelo para indicar
    a qual agente especializado a mensagem do usuário deve
    ser delegada.
    """

    target_agent: TargetAgent = Field(
        ...,
        description="Nome do agente que deve processar a mensagem.",
    )
