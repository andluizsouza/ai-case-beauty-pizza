# Testes — Beauty Pizza

Suíte com testes automatizados via `pytest`, cobrindo agentes, tools, segurança e PII.

```bash
# Executar todos
python -m pytest tests/ -v

# Executar módulo específico
python -m pytest tests/test_e2e.py -v
```

---

## Resumo por Arquivo

| Arquivo | Testes | Cobertura |
|---|---|---|
| `test_agents.py` | 29 | Configuração dos agentes, routing, instruções, segurança |
| `test_e2e.py` | 42 | Jornada completa do cliente + red teaming de segurança |
| `test_tools.py` | 26 | Tools de cardápio (SQLite) e pedidos (API REST) |
| `test_pii_filter.py` | 12 | Mascaramento de CPF, telefone, falsos positivos |

---

## test_agents.py (29 testes)

### TestRouteDecision (6)

Valida o modelo Pydantic de roteamento (`RouteDecision` + `TargetAgent` Enum).

| Teste | Verifica |
|---|---|
| `test_valid_menu_agent` | Criação com `TargetAgent.MENU` |
| `test_valid_order_agent` | Criação com `TargetAgent.ORDER` |
| `test_from_string_value` | Construção a partir de string |
| `test_invalid_agent_name_rejected` | Rejeição de valor inválido |
| `test_json_serialization` | Serialização para JSON |
| `test_json_deserialization` | Deserialização de JSON |

### TestRouterAgent (5)

Verifica configuração do `router_agent` (sem tools, structured output).

| Teste | Verifica |
|---|---|
| `test_router_has_no_tools` | Nenhuma tool registrada |
| `test_router_has_structured_output` | `output_schema=RouteDecision` |
| `test_router_name` | Nome correto |
| `test_router_instructions_contain_agents` | Instruções mencionam agentes alvo |
| `test_router_instructions_security` | Instruções contêm regras anti-injection |

### TestMenuAgent (5)

Configuração do `menu_agent` (tools, sessão, instruções).

| Teste | Verifica |
|---|---|
| `test_menu_agent_has_tools` | Tools registradas corretamente |
| `test_menu_agent_name` | Nome correto |
| `test_menu_agent_with_session` | Suporte a `session_id` |
| `test_menu_instructions_security` | Regras anti-injection |
| `test_menu_instructions_scope` | Escopo restrito ao cardápio |

### TestOrderAgent (4)

Configuração do `order_agent` (tools, sessão, instruções).

| Teste | Verifica |
|---|---|
| `test_order_agent_has_tools` | Tools registradas (7 esperadas, sem `get_menu_report`) |
| `test_order_agent_name` | Nome correto |
| `test_order_agent_with_session` | Suporte a `session_id` |
| `test_order_instructions_security` | Regras anti-injection |

### TestOrderAgentDataRequirements (9)

Valida que as instruções do `order_agent` exigem dados completos antes de cada operação.

| Teste | Verifica |
|---|---|
| `test_instructions_require_cpf_before_create` | CPF obrigatório antes de criar pedido |
| `test_instructions_require_sabor` | Sabor obrigatório |
| `test_instructions_require_tamanho` | Tamanho obrigatório |
| `test_instructions_require_borda` | Borda obrigatória |
| `test_instructions_ask_user_if_missing` | Agente pergunta dados faltantes |
| `test_instructions_no_default_values` | Nenhum valor default assumido |
| `test_instructions_require_all_three_before_add_item` | Sabor + tamanho + borda antes de adicionar item |
| `test_instructions_refuse_completed_orders` | Recusa alterações em pedidos finalizados |
| `test_instructions_item_name_format` | Formato do nome: "Pizza {Sabor} {Tamanho} Borda {Borda}" |

---

## test_e2e.py (42 testes)

### TestFullCustomerJourneyWithMissingInfo (18)

Cenários de jornada do cliente: criação de pedido, adição/remoção de itens, endereço, consultas, roteamento.

| Teste | Verifica |
|---|---|
| `test_order_pizza_missing_size_and_crust` | Pedido sem tamanho e borda → agente pergunta |
| `test_order_pizza_missing_only_crust` | Pedido sem borda → agente pergunta |
| `test_order_pizza_missing_only_size` | Pedido sem tamanho → agente pergunta |
| `test_create_order_missing_cpf` | Criação sem CPF → agente solicita |
| `test_create_order_missing_name` | Criação sem nome → agente solicita |
| `test_create_order_with_full_data` | Criação com todos os dados → sucesso |
| `test_add_item_with_complete_info` | Adição de item com sabor+tamanho+borda |
| `test_add_multiple_items_to_existing_order` | Múltiplos itens ao mesmo pedido |
| `test_update_delivery_address` | Atualização de endereço de entrega |
| `test_remove_item_from_order` | Remoção de item |
| `test_filter_orders_by_document_and_date` | Filtro por CPF + data |
| `test_filter_orders_by_document_only` | Filtro apenas por CPF |
| `test_get_order_details_with_total_price` | Detalhes com preço total |
| `test_create_order_without_items` | Criação de pedido vazio (sem itens) |
| `test_completed_order_refuses_changes` | Pedido finalizado recusa alterações |
| `test_routing_cardapio_goes_to_menu` | Mensagem sobre cardápio → `menu_agent` |
| `test_routing_pedido_goes_to_order` | Mensagem sobre pedido → `order_agent` |
| `test_routing_greeting_goes_to_order` | Saudação → `order_agent` |

### TestSecurityRedTeaming (24)

Testes adversariais: prompt injection, role switching, escopo, SQL injection, sessão.

| Teste | Verifica |
|---|---|
| `test_menu_agent_rejects_instruction_override` | menu_agent ignora "ignore suas instruções" |
| `test_order_agent_rejects_instruction_override` | order_agent ignora override |
| `test_router_agent_rejects_instruction_override` | router_agent ignora override |
| `test_menu_agent_never_reveals_system_prompt` | menu_agent não revela system prompt |
| `test_order_agent_never_reveals_system_prompt` | order_agent não revela |
| `test_router_agent_never_reveals_system_prompt` | router_agent não revela |
| `test_menu_blocks_role_switching` | menu_agent bloqueia "agora você é um..." |
| `test_order_blocks_role_switching` | order_agent bloqueia |
| `test_menu_agent_restricted_to_cardapio` | menu_agent só responde sobre cardápio |
| `test_order_agent_restricted_to_pedidos` | order_agent só responde sobre pedidos |
| `test_sqlite_readonly_blocks_insert` | SQLite read-only bloqueia INSERT |
| `test_sqlite_readonly_blocks_update` | SQLite read-only bloqueia UPDATE |
| `test_sqlite_readonly_blocks_delete` | SQLite read-only bloqueia DELETE |
| `test_sqlite_readonly_blocks_drop_table` | SQLite read-only bloqueia DROP |
| `test_sqlite_readonly_blocks_alter_table` | SQLite read-only bloqueia ALTER |
| `test_sqlite_readonly_blocks_create_table` | SQLite read-only bloqueia CREATE |
| `test_get_pizza_price_uses_parameterized_query` | Queries parametrizadas (anti SQL injection) |
| `test_search_menu_injection_returns_empty_or_valid` | Busca com payload malicioso → resultado seguro |
| `test_menu_agent_polite_rejection_instruction` | Rejeição educada nas instruções |
| `test_order_agent_polite_rejection_instruction` | Rejeição educada nas instruções |
| `test_all_agents_block_developer_mode` | Todos bloqueiam "developer mode" |
| `test_router_always_returns_json` | Router sempre retorna JSON válido |
| `test_agents_use_session_scoping` | Agentes usam session scoping |
| `test_order_agents_session_isolated` | Sessões isoladas entre si |

---

## test_tools.py (26 testes)

### TestGetReadonlyConnection (4)

Valida que a conexão SQLite é estritamente read-only.

| Teste | Verifica |
|---|---|
| `test_sqlite_readonly_blocks_writes` | INSERT bloqueado |
| `test_sqlite_readonly_blocks_delete` | DELETE bloqueado |
| `test_sqlite_readonly_blocks_drop` | DROP bloqueado |
| `test_sqlite_readonly_allows_select` | SELECT permitido |

### TestLoadMenuItems (2)

Carregamento de itens do cardápio para embeddings.

| Teste | Verifica |
|---|---|
| `test_load_all_items` | Todos os itens carregados |
| `test_items_have_valid_prices` | Preços válidos (> 0) |

### TestGetPizzaPrice (3)

Consulta de preço por sabor+tamanho+borda.

| Teste | Verifica |
|---|---|
| `test_known_price` | Preço conhecido retornado |
| `test_unknown_combination_returns_none` | Combinação inexistente → `None` |
| `test_sweet_pizza_only_traditional_crust` | Pizza doce só aceita borda Tradicional |

### TestSearchMenu (2)

Busca semântica por similaridade de cosseno.

| Teste | Verifica |
|---|---|
| `test_search_returns_results` | Busca retorna resultados |
| `test_search_results_sorted_by_score` | Resultados ordenados por score |

### TestCreateOrder (3)

Criação de pedido via API REST.

| Teste | Verifica |
|---|---|
| `test_create_order_success` | Criação bem-sucedida |
| `test_api_timeout_handled_gracefully` | Timeout tratado gracefully |
| `test_create_order_http_error` | Erro HTTP tratado |

### TestAddItemToOrder (2)

| Teste | Verifica |
|---|---|
| `test_add_item_success` | Adição de item bem-sucedida |
| `test_add_item_timeout` | Timeout tratado |

### TestRemoveItemFromOrder (2)

| Teste | Verifica |
|---|---|
| `test_remove_item_success` | Remoção bem-sucedida |
| `test_remove_item_timeout` | Timeout tratado |

### TestUpdateDeliveryAddress (2)

| Teste | Verifica |
|---|---|
| `test_update_address_success` | Atualização bem-sucedida |
| `test_update_address_timeout` | Timeout tratado |

### TestGetOrderDetails (2)

| Teste | Verifica |
|---|---|
| `test_get_details_success` | Detalhes retornados |
| `test_get_details_timeout` | Timeout tratado |

### TestFilterOrders (2)

| Teste | Verifica |
|---|---|
| `test_filter_success` | Filtro retorna resultados |
| `test_filter_timeout` | Timeout tratado |

---

## test_pii_filter.py (12 testes)

### TestCPFMasking (4)

| Teste | Verifica |
|---|---|
| `test_logger_masks_pii_data` | Logger mascara PII no output |
| `test_mask_cpf_formatted` | `123.456.789-00` → `***.***.***-00` |
| `test_mask_cpf_raw` | `12345678900` → `*********00` |
| `test_cpf_in_args` | CPF em args do log mascarado |

### TestPhoneMasking (3)

| Teste | Verifica |
|---|---|
| `test_mask_phone_with_space` | `(11) 99999-8888` → `(11) *****-8888` |
| `test_mask_phone_without_space` | `(11)99999-8888` → mascarado |
| `test_mask_phone_8_digits` | Telefone de 8 dígitos mascarado |

### TestMultiplePatterns (2)

| Teste | Verifica |
|---|---|
| `test_mask_cpf_and_phone_together` | CPF + telefone na mesma mensagem |
| `test_multiple_cpfs` | Múltiplos CPFs mascarados |

### TestNoFalsePositives (3)

| Teste | Verifica |
|---|---|
| `test_short_numbers_not_masked` | Números curtos não mascarados |
| `test_regular_text_not_masked` | Texto comum não alterado |
| `test_price_not_masked` | Preços (R$ 45,90) não mascarados |
