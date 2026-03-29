"""Tools de integração com a API REST de pedidos.

Todas as chamadas HTTP usam ``httpx`` com timeout de 5 segundos,
logging de cada operação e tratamento de erros padronizado.
"""

import logging
from datetime import date

import httpx

from src.config import settings

logger = logging.getLogger("beauty_pizza")

_TIMEOUT = 5.0


def _api_url(path: str) -> str:
    """Monta a URL completa da API a partir do path relativo."""
    base = settings.order_api_base_url.rstrip("/")
    return f"{base}/{path.lstrip('/')}"


# ---------------------------------------------------------------------------
# Pedidos
# ---------------------------------------------------------------------------


def create_order(
    client_name: str,
    client_document: str,
    delivery_date: str | None = None,
) -> dict:
    """Cria um novo pedido na API.

    Args:
        client_name: Nome do cliente (até 300 caracteres).
        client_document: CPF do cliente (apenas números, 11 dígitos).
        delivery_date: Data de entrega (YYYY-MM-DD). Se omitido, usa hoje.

    Returns:
        Dicionário com os dados do pedido criado (inclui ``id``).

    Raises:
        httpx.TimeoutException: Se a API não responder em 5s.
        httpx.HTTPStatusError: Se a API retornar erro (4xx/5xx).
    """
    logger.info(
        "create_order: client_document='%s', delivery_date='%s'",
        client_document,
        delivery_date,
    )

    payload = {
        "client_name": client_name,
        "client_document": client_document,
        "delivery_date": delivery_date or date.today().isoformat(),
    }

    try:
        response = httpx.post(
            _api_url("/orders/"),
            json=payload,
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        logger.info("Pedido criado com id=%s", data.get("id"))
        return data

    except httpx.TimeoutException:
        logger.error("Timeout ao criar pedido")
        return {"error": "Timeout ao criar pedido. Tente novamente."}
    except httpx.HTTPStatusError as exc:
        logger.error("Erro HTTP %s ao criar pedido: %s", exc.response.status_code, exc.response.text)
        return {"error": f"Erro ao criar pedido: {exc.response.text}"}
    except Exception:
        logger.exception("Erro inesperado ao criar pedido")
        return {"error": "Erro inesperado ao criar pedido."}


# ---------------------------------------------------------------------------
# Itens
# ---------------------------------------------------------------------------


def add_item_to_order(
    order_id: int,
    item_name: str,
    quantity: int,
    unit_price: float,
) -> dict:
    """Adiciona um item a um pedido existente.

    O ``item_name`` deve conter o nome completo da pizza com tamanho e borda
    (ex: "Pizza Margherita Grande Borda Recheada com Cheddar").
    O ``unit_price`` deve ser obtido previamente via ``get_pizza_price``.

    Args:
        order_id: ID do pedido na API.
        item_name: Nome completo do item (sabor + tamanho + borda).
        quantity: Quantidade (positivo).
        unit_price: Preço unitário (obtido do cardápio).

    Returns:
        Dicionário com resposta da API.
    """
    logger.info(
        "add_item_to_order: order_id=%s, item='%s', qty=%d, price=%.2f",
        order_id, item_name, quantity, unit_price,
    )

    payload = {
        "items": [
            {
                "name": item_name,
                "quantity": quantity,
                "unit_price": unit_price,
            }
        ]
    }

    try:
        response = httpx.patch(
            _api_url(f"/orders/{order_id}/add-items/"),
            json=payload,
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        logger.info("Item adicionado ao pedido %s", order_id)
        return data

    except httpx.TimeoutException:
        logger.error("Timeout ao adicionar item ao pedido %s", order_id)
        return {"error": "Timeout ao adicionar item. Tente novamente."}
    except httpx.HTTPStatusError as exc:
        logger.error("Erro HTTP %s ao adicionar item: %s", exc.response.status_code, exc.response.text)
        return {"error": f"Erro ao adicionar item: {exc.response.text}"}
    except Exception:
        logger.exception("Erro inesperado ao adicionar item")
        return {"error": "Erro inesperado ao adicionar item."}


def remove_item_from_order(order_id: int, item_id: int) -> dict:
    """Remove um item de um pedido.

    Args:
        order_id: ID do pedido na API.
        item_id: ID do item a remover.

    Returns:
        Dicionário com resposta da API.
    """
    logger.info(
        "remove_item_from_order: order_id=%s, item_id=%s",
        order_id, item_id,
    )

    try:
        response = httpx.delete(
            _api_url(f"/orders/{order_id}/items/{item_id}/"),
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        logger.info("Item %s removido do pedido %s", item_id, order_id)
        return {"detail": "Item removido com sucesso."}

    except httpx.TimeoutException:
        logger.error("Timeout ao remover item %s do pedido %s", item_id, order_id)
        return {"error": "Timeout ao remover item. Tente novamente."}
    except httpx.HTTPStatusError as exc:
        logger.error("Erro HTTP %s ao remover item: %s", exc.response.status_code, exc.response.text)
        return {"error": f"Erro ao remover item: {exc.response.text}"}
    except Exception:
        logger.exception("Erro inesperado ao remover item")
        return {"error": "Erro inesperado ao remover item."}


# ---------------------------------------------------------------------------
# Endereço
# ---------------------------------------------------------------------------


def update_delivery_address(
    order_id: int,
    street_name: str,
    number: str,
    complement: str = "",
    reference_point: str = "",
) -> dict:
    """Atualiza o endereço de entrega de um pedido.

    Args:
        order_id: ID do pedido na API.
        street_name: Nome da rua (até 255 caracteres).
        number: Número do endereço (até 20 caracteres).
        complement: Complemento (opcional).
        reference_point: Ponto de referência (opcional).

    Returns:
        Dicionário com resposta da API.
    """
    logger.info("update_delivery_address: order_id=%s", order_id)

    payload: dict = {
        "delivery_address": {
            "street_name": street_name,
            "number": number,
        }
    }
    if complement:
        payload["delivery_address"]["complement"] = complement
    if reference_point:
        payload["delivery_address"]["reference_point"] = reference_point

    try:
        response = httpx.patch(
            _api_url(f"/orders/{order_id}/update-address/"),
            json=payload,
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        logger.info("Endereço atualizado para pedido %s", order_id)
        return data

    except httpx.TimeoutException:
        logger.error("Timeout ao atualizar endereço do pedido %s", order_id)
        return {"error": "Timeout ao atualizar endereço. Tente novamente."}
    except httpx.HTTPStatusError as exc:
        logger.error("Erro HTTP %s ao atualizar endereço: %s", exc.response.status_code, exc.response.text)
        return {"error": f"Erro ao atualizar endereço: {exc.response.text}"}
    except Exception:
        logger.exception("Erro inesperado ao atualizar endereço")
        return {"error": "Erro inesperado ao atualizar endereço."}


# ---------------------------------------------------------------------------
# Consulta
# ---------------------------------------------------------------------------


def get_order_details(order_id: int) -> dict:
    """Busca os detalhes completos de um pedido.

    Args:
        order_id: ID do pedido na API.

    Returns:
        Dicionário com dados completos do pedido (inclui ``total_price``).
    """
    logger.info("get_order_details: order_id=%s", order_id)

    try:
        response = httpx.get(
            _api_url(f"/orders/{order_id}/"),
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        logger.info("Detalhes do pedido %s obtidos com sucesso", order_id)
        return data

    except httpx.TimeoutException:
        logger.error("Timeout ao buscar detalhes do pedido %s", order_id)
        return {"error": "Timeout ao buscar detalhes do pedido. Tente novamente."}
    except httpx.HTTPStatusError as exc:
        logger.error("Erro HTTP %s ao buscar pedido: %s", exc.response.status_code, exc.response.text)
        return {"error": f"Erro ao buscar pedido: {exc.response.text}"}
    except Exception:
        logger.exception("Erro inesperado ao buscar detalhes do pedido")
        return {"error": "Erro inesperado ao buscar detalhes do pedido."}


def filter_orders(client_document: str, delivery_date: str | None = None) -> dict:
    """Busca pedidos por documento do cliente e/ou data de entrega.

    Args:
        client_document: CPF do cliente (apenas números).
        delivery_date: Data de entrega (YYYY-MM-DD, opcional).

    Returns:
        Lista de pedidos encontrados ou dicionário com erro.
    """
    logger.info(
        "filter_orders: document='%s', date='%s'",
        client_document, delivery_date,
    )

    params: dict[str, str] = {"client_document": client_document}
    if delivery_date:
        params["delivery_date"] = delivery_date

    try:
        response = httpx.get(
            _api_url("/orders/filter/"),
            params=params,
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        logger.info("filter_orders retornou %d pedidos", len(data) if isinstance(data, list) else 0)
        return data

    except httpx.TimeoutException:
        logger.error("Timeout ao filtrar pedidos")
        return {"error": "Timeout ao filtrar pedidos. Tente novamente."}
    except httpx.HTTPStatusError as exc:
        logger.error("Erro HTTP %s ao filtrar pedidos: %s", exc.response.status_code, exc.response.text)
        return {"error": f"Erro ao filtrar pedidos: {exc.response.text}"}
    except Exception:
        logger.exception("Erro inesperado ao filtrar pedidos")
        return {"error": "Erro inesperado ao filtrar pedidos."}
