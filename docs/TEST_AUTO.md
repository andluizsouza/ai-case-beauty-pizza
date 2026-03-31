# Testes Automatizados — Beauty Pizza

Suíte com testes automatizados via `pytest`, cobrindo agentes, tools, segurança, PII e integração com a API de pedidos.

```bash
# Executar todos
python -m pytest tests/ -v

# Executar módulo específico
python -m pytest tests/test_agents.py -v
```

---

## Resumo por Arquivo

| Arquivo | Testes | Cobertura |
|---|---|---|
| `test_agents.py` | 27 | Configuração dos agentes, routing, instruções, segurança anti-injection |
| `test_tools.py` | 23 | Tools de cardápio (SQLite read-only) e pedidos (API mockada) |
| `test_pii_filter.py` | 10 | Mascaramento de CPF, telefone, falsos positivos |
| `test_order_tools_integration.py` | 14 | Integração real com a API de pedidos (requer API rodando) |

---

## test_agents.py (27 testes)

### TestRouteDecision (3)

Valida o modelo Pydantic de roteamento (`RouteDecision` + `TargetAgent` Enum).

| Teste | Verifica |
|---|---|
| `test_valid_menu_agent` | Criação com `TargetAgent.MENU` |
| `test_valid_order_agent` | Criação com `TargetAgent.ORDER` |
| `test_invalid_agent_name_rejected` | Rejeição de valor inválido |

### TestRouterAgent (5)

Verifica configuração e comportamento de roteamento do `router_agent`.

| Teste | Verifica |
|---|---|
| `test_router_has_no_tools` | Nenhuma tool registrada |
| `test_router_has_structured_output` | `output_schema=RouteDecision` |
| `test_router_name` | Nome correto |
| `test_router_instructions_routing_rules` | Instruções mencionam agentes e regras de roteamento |
| `test_router_instructions_security` | Anti-injection, system prompt e formato JSON |

### TestMenuAgent (5)

Configuração e instruções do `menu_agent`.

| Teste | Verifica |
|---|---|
| `test_menu_agent_has_tools` | Tools registradas corretamente |
| `test_menu_agent_name` | Nome correto |
| `test_menu_agent_with_session` | Suporte a `session_id` |
| `test_menu_instructions_business_rules` | Primeiro contato, validação, alternativas, resumo com preço |
| `test_menu_instructions_security` | Anti-injection, system prompt, escopo restrito |

### TestOrderAgent (7)

Configuração do `order_agent` e validação de instruções de dados e ciclo de vida.

| Teste | Verifica |
|---|---|
| `test_order_agent_has_tools` | Tools registradas (sem `get_menu_report`) |
| `test_order_agent_name` | Nome correto |
| `test_order_agent_with_session` | Suporte a `session_id` |
| `test_order_instructions_data_requirements` | CPF, nome, sabor, tamanho, borda obrigatórios |
| `test_order_instructions_lifecycle` | Ciclo create → address → details → finalizado |
| `test_order_instructions_item_format` | Formato "Pizza [Sabor] [Tamanho] Borda [Tipo da Borda]" |
| `test_order_instructions_security` | Anti-injection, system prompt, ocultação da separação interna |

### TestAgentSecurityInstructions (7)

Proteções contra prompt injection aplicadas a todos os agentes (parametrizados).

| Teste | Verifica |
|---|---|
| `test_blocks_role_switching[menu_agent]` | Bloqueia troca de papel |
| `test_blocks_role_switching[order_agent]` | Bloqueia troca de papel |
| `test_blocks_developer_mode[menu_agent]` | Bloqueia "modo desenvolvedor" |
| `test_blocks_developer_mode[order_agent]` | Bloqueia "modo desenvolvedor" |
| `test_restricts_scope[menu_agent]` | Bloqueia execução de código |
| `test_restricts_scope[order_agent]` | Bloqueia execução de código |
| `test_session_isolation` | Sessions diferentes não compartilham estado |

---

## test_tools.py (23 testes)

### TestSQLiteReadOnly (2)

Valida que a conexão SQLite é estritamente read-only.

| Teste | Verifica |
|---|---|
| `test_readonly_blocks_all_writes` | INSERT, UPDATE, DELETE, DROP, ALTER e CREATE bloqueados |
| `test_readonly_allows_select` | SELECT permitido |

### TestLoadMenuItems (2)

Carregamento de itens do cardápio para embeddings.

| Teste | Verifica |
|---|---|
| `test_load_all_items` | Todos os itens carregados com campos esperados |
| `test_items_have_valid_prices` | Preços válidos (> 0) |

### TestGetPizzaPrice (4)

Consulta de preço por sabor+tamanho+borda e proteção contra SQL injection.

| Teste | Verifica |
|---|---|
| `test_known_price` | Preço conhecido retornado |
| `test_unknown_combination_returns_none` | Combinação inexistente → `None` |
| `test_sweet_pizza_only_traditional_crust` | Pizza doce só aceita borda Tradicional |
| `test_sql_injection_returns_none` | Payload de SQL injection não quebra a query |

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

## test_pii_filter.py (10 testes)

### TestCPFMasking (3)

| Teste | Verifica |
|---|---|
| `test_mask_cpf_formatted` | `987.654.321-10` → `***.***.***-10` |
| `test_mask_cpf_raw` | `12345678900` → `*********00` |
| `test_cpf_in_args` | CPF em args do log mascarado |

### TestPhoneMasking (3)

| Teste | Verifica |
|---|---|
| `test_mask_phone_with_space` | `(11) 99999-8888` → `(11) *****-8888` |
| `test_mask_phone_without_space` | `(11)99999-8888` → mascarado |
| `test_mask_phone_8_digits` | Telefone de 8 dígitos mascarado |

### TestMultiplePatterns (1)

| Teste | Verifica |
|---|---|
| `test_mask_cpf_and_phone_together` | CPF + telefone na mesma mensagem |

### TestNoFalsePositives (3)

| Teste | Verifica |
|---|---|
| `test_short_numbers_not_masked` | Números curtos não mascarados |
| `test_regular_text_not_masked` | Texto comum não alterado |
| `test_price_not_masked` | Preços (R$ 45,00) não mascarados |

---

## test_order_tools_integration.py (14 testes)

> Requer a API de pedidos rodando em `localhost:8000`. Os testes são ignorados automaticamente (`skipif`) se a API estiver fora.

### TestCreateOrderIntegration (3)

Criação de pedido contra a API real: campos de resposta e validações.

| Teste | Verifica |
|---|---|
| `test_create_order_returns_id_and_fields` | Resposta contém `id`, `client_name`, `items`, `total_price`, `created_at` |
| `test_create_duplicate_order_returns_error` | Duplicata (name+cpf+date) retorna error |
| `test_create_order_missing_required_fields_returns_error` | Nome vazio e CPF vazio rejeitados |

### TestFullOrderJourneyIntegration (9)

Jornada completa: criar → itens → endereço → consultar → remover → filtrar. Cada teste inicia com pedido novo (CPF único via `uuid4`).

| Teste | Verifica |
|---|---|
| `test_add_single_item` | Adiciona item e recebe confirmação |
| `test_add_item_and_verify_total_price` | `total_price` calculado corretamente (qty × unit_price) |
| `test_add_multiple_items` | Múltiplos itens somam no total |
| `test_remove_item` | Adiciona e remove → item desaparece, total zera |
| `test_remove_nonexistent_item_returns_error` | Item id=999999 retorna error |
| `test_update_delivery_address` | Endereço completo (rua, número, complemento, referência) |
| `test_get_order_details_all_fields` | Detalhes contêm todos os campos da entidade Order |
| `test_filter_by_document` | Filtro por CPF retorna o pedido criado |
| `test_filter_nonexistent_document_returns_empty` | CPF sem pedidos retorna `[]` |

### TestNonexistentOrderIntegration (2)

Operações em pedido inexistente (id=999999).

| Teste | Verifica |
|---|---|
| `test_get_details_nonexistent_order` | Detalhes de pedido inexistente → error |
| `test_modify_nonexistent_order_returns_error` | Adicionar item e atualizar endereço → error |
