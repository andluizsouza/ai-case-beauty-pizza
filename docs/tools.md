# Tools — Documentação Técnica

Documentação das tools do Atendente Virtual Beauty Pizza: consulta ao cardápio e integração com a API de pedidos.

---

## Visão Geral

As tools são funções Python invocadas pelos agentes para executar ações concretas. Seguem princípios de segurança:

- **SQLite read-only** (`?mode=ro`) para o cardápio — impede qualquer operação de escrita.
- **Timeout de 5s** em todas as chamadas HTTP — evita travamentos.
- **Logging** de todas as chamadas com PII mascarado via `PIIMaskingFilter`.
- **Queries parametrizadas** (`?` placeholders) — previne SQL injection.

---

## `menu_tools.py` — Cardápio (Read-Only)

### `search_menu(query, db_path?, top_k?) -> list[dict]`

Busca semântica no cardápio usando RAG com embeddings Gemini.

1. Carrega todos os itens do cardápio (JOIN de pizzas + tamanhos + bordas + precos).
2. Gera embedding para a query do usuário via `text-embedding-004`.
3. Gera embedding para cada item (texto: sabor + descrição + ingredientes + tamanho + borda).
4. Calcula similaridade de cosseno e retorna os `top_k` mais similares.

```python
results = search_menu("pizza com queijo", top_k=3)
# [{"sabor": "Quatro Queijos", "tamanho": "Grande", ..., "score": 0.92}, ...]
```

### `get_pizza_price(sabor, tamanho, borda, db_path?) -> dict | None`

Busca exata do preço de uma combinação sabor + tamanho + borda.

```python
price = get_pizza_price("Margherita", "Grande", "Tradicional")
# {"sabor": "Margherita", "tamanho": "Grande", "borda": "Tradicional", "preco": 45.0}
```

Retorna `None` se a combinação não existir (ex: pizza doce com borda recheada).

### Segurança

- Conexão via `sqlite3.connect("file:...?mode=ro", uri=True)`.
- Todas as queries usam `?` placeholders (parametrized queries).
- Tentativas de `INSERT`, `UPDATE`, `DELETE`, `DROP` levantam `sqlite3.OperationalError`.

---

## `order_tools.py` — API de Pedidos (REST)

Todas as funções seguem o padrão:
- **Timeout**: 5 segundos (`httpx`, síncrono).
- **Retorno de erro**: Dicionário `{"error": "mensagem"}` em vez de exceção (para o agente tratar).
- **Logging**: Cada chamada logada com nível INFO (sucesso) ou ERROR (falha).

### `create_order(client_name, client_document, delivery_date?) -> dict`

Cria um novo pedido na API.

```python
order = create_order("João Silva", "12345678901", "2026-03-29")
# {"id": 1, "client_name": "João Silva", ...}
```

### `add_item_to_order(order_id, item_name, quantity, unit_price) -> dict`

Adiciona um item ao pedido. O `item_name` deve conter o nome completo (ex: "Pizza Margherita Grande Borda Recheada com Cheddar") e o `unit_price` deve vir do `get_pizza_price`.

```python
add_item_to_order(1, "Pizza Margherita Grande Borda Tradicional", 1, 45.0)
```

### `remove_item_from_order(order_id, item_id) -> dict`

Remove um item pelo `item_id` (obtido via `get_order_details`).

### `update_delivery_address(order_id, street_name, number, complement?, reference_point?) -> dict`

Atualiza ou cria o endereço de entrega do pedido.

### `get_order_details(order_id) -> dict`

Retorna os detalhes completos do pedido, incluindo `total_price` calculado.

### `filter_orders(client_document, delivery_date?) -> list | dict`

Busca pedidos pelo CPF do cliente e opcionalmente pela data de entrega.

---

## Tratamento de Erros

| Cenário | Comportamento |
|---|---|
| Timeout (5s) | Retorna `{"error": "Timeout ao ..."}` |
| Erro HTTP (4xx/5xx) | Retorna `{"error": "Erro ao ...: <body>"}` |
| Exceção inesperada | Retorna `{"error": "Erro inesperado ao ..."}` |
| Combinação inexistente no cardápio | Retorna `None` |

---

## Testes

```bash
pytest tests/test_tools.py -v
```

### Testes obrigatórios

| Teste | O que valida |
|---|---|
| `test_api_timeout_handled_gracefully` | Timeout da API retorna erro sem exceção |
| `test_sqlite_readonly_blocks_writes` | INSERT em modo `?mode=ro` levanta `OperationalError` |
| `test_sqlite_readonly_blocks_delete` | DELETE bloqueado |
| `test_sqlite_readonly_blocks_drop` | DROP TABLE bloqueado |
| `test_known_price` | Preço exato da Margherita Pequena Tradicional = R$ 25,00 |
| `test_sweet_pizza_only_traditional_crust` | Pizza doce + borda recheada = None |
