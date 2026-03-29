"""Modelos Pydantic do projeto Beauty Pizza.

Concentra schemas do banco de dados do cardápio (SQLite),
contratos da API de pedidos e modelos de roteamento.
"""

from src.models.menu import (
    Borda,
    MenuItem,
    MenuSearchResult,
    Pizza,
    Preco,
    Tamanho,
)
from src.models.order import (
    AddItemsPayload,
    DeliveryAddressCreate,
    DeliveryAddressResponse,
    ItemCreate,
    ItemResponse,
    OrderCreate,
    OrderFilterParams,
    OrderResponse,
    UpdateAddressPayload,
)
from src.models.routing import RouteDecision, TargetAgent

__all__ = [
    # Menu (cardápio)
    "Borda",
    "MenuItem",
    "MenuSearchResult",
    "Pizza",
    "Preco",
    "Tamanho",
    # Order (API de pedidos)
    "AddItemsPayload",
    "DeliveryAddressCreate",
    "DeliveryAddressResponse",
    "ItemCreate",
    "ItemResponse",
    "OrderCreate",
    "OrderFilterParams",
    "OrderResponse",
    "UpdateAddressPayload",
    # Routing
    "RouteDecision",
    "TargetAgent",
]
