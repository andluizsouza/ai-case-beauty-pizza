"""Modelos Pydantic para a API REST de pedidos (``candidates-case-order-api``).

Contratos de dados das entidades ``Order``, ``Item`` e ``DeliveryAddress``
conforme a API Django em https://github.com/gbtech-oss/candidates-case-order-api.

Ref: order/models.py e order/serializers.py do repositório da API.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# DeliveryAddress
# ---------------------------------------------------------------------------


class DeliveryAddressCreate(BaseModel):
    """Payload para criação/atualização de endereço de entrega.

    Campos obrigatórios: ``street_name``, ``number``.
    """

    street_name: str = Field(
        ..., max_length=255, description="Nome da rua (até 255 caracteres)."
    )
    number: str = Field(
        ..., max_length=20, description="Número do endereço (até 20 caracteres)."
    )
    complement: str = Field(
        default="",
        max_length=255,
        description="Complemento (opcional, até 255 caracteres).",
    )
    reference_point: str = Field(
        default="",
        max_length=255,
        description="Ponto de referência (opcional, até 255 caracteres).",
    )


class DeliveryAddressResponse(BaseModel):
    """Endereço de entrega retornado pela API."""

    street_name: str = Field(description="Nome da rua.")
    number: str = Field(description="Número do endereço.")
    complement: str | None = Field(default=None, description="Complemento.")
    reference_point: str | None = Field(
        default=None, description="Ponto de referência."
    )


# ---------------------------------------------------------------------------
# Item
# ---------------------------------------------------------------------------


class ItemCreate(BaseModel):
    """Payload para criação de um item de pedido.

    O ``name`` deve conter o nome completo da pizza
    (ex: 'Pizza Margherita Grande Borda Recheada com Cheddar').
    """

    name: str = Field(
        ..., max_length=255, description="Nome do item (até 255 caracteres)."
    )
    quantity: int = Field(
        ..., ge=0, description="Quantidade (inteiro positivo, >= 0)."
    )
    unit_price: Decimal = Field(
        ...,
        ge=0,
        max_digits=10,
        decimal_places=2,
        description="Preço unitário (decimal, >= 0).",
    )


class ItemResponse(BaseModel):
    """Item de pedido retornado pela API."""

    id: int = Field(description="ID do item (gerado pela API).")
    name: str = Field(description="Nome do item.")
    quantity: int = Field(description="Quantidade.")
    unit_price: Decimal = Field(description="Preço unitário.")


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


class OrderCreate(BaseModel):
    """Payload para criação de pedido (``POST /api/orders/``).

    Constraint da API: ``unique_together = ('client_name', 'client_document', 'delivery_date')``.
    """

    client_name: str = Field(
        ...,
        max_length=300,
        description="Nome do cliente (obrigatório, até 300 caracteres).",
    )
    client_document: str = Field(
        ..., description="CPF do cliente (obrigatório, apenas números)."
    )
    delivery_date: str = Field(
        default_factory=lambda: date.today().isoformat(),
        description="Data de entrega no formato YYYY-MM-DD.",
    )
    delivery_address: DeliveryAddressCreate | None = Field(
        default=None, description="Endereço de entrega (opcional na criação)."
    )
    items: list[ItemCreate] = Field(
        default_factory=list,
        description="Lista de itens (opcional na criação).",
    )


class OrderResponse(BaseModel):
    """Pedido completo retornado pela API (``GET /api/orders/<id>/``).

    ``total_price`` é calculado automaticamente pela API como
    ``sum(item.quantity * item.unit_price)``.
    """

    id: int = Field(description="ID do pedido (gerado pela API).")
    client_name: str = Field(description="Nome do cliente.")
    client_document: str = Field(description="CPF do cliente.")
    delivery_date: str = Field(description="Data de entrega (YYYY-MM-DD).")
    delivery_address: DeliveryAddressResponse | None = Field(
        default=None, description="Endereço de entrega."
    )
    items: list[ItemResponse] = Field(
        default_factory=list, description="Itens do pedido."
    )
    total_price: Decimal = Field(
        description="Preço total (read-only, calculado pela API)."
    )
    created_at: datetime | None = Field(
        default=None, description="Data/hora de criação (read-only)."
    )
    updated_at: datetime | None = Field(
        default=None, description="Data/hora da última atualização (read-only)."
    )


# ---------------------------------------------------------------------------
# Payloads auxiliares para endpoints específicos
# ---------------------------------------------------------------------------


class AddItemsPayload(BaseModel):
    """Payload para ``PATCH /api/orders/<id>/add-items/``."""

    items: list[ItemCreate] = Field(
        ..., min_length=1, description="Lista de itens a adicionar."
    )


class UpdateAddressPayload(BaseModel):
    """Payload para ``PATCH /api/orders/<id>/update-address/``."""

    delivery_address: DeliveryAddressCreate = Field(
        ..., description="Novo endereço de entrega."
    )


class OrderFilterParams(BaseModel):
    """Parâmetros de query para ``GET /api/orders/filter/``."""

    client_document: str = Field(
        ..., description="CPF do cliente (obrigatório)."
    )
    delivery_date: str | None = Field(
        default=None,
        description="Data de entrega (YYYY-MM-DD, opcional).",
    )
