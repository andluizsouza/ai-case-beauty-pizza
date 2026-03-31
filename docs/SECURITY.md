# Segurança

O projeto implementa proteções inspiradas no **OWASP LLM Top 10**:

## Prevenção de Prompt Injection

Todos os agentes possuem instruções estritas que:
- **Ignoram** comandos de bypass ("ignore suas instruções", "modo desenvolvedor").
- **Nunca revelam** system prompts ou configurações internas.
- **Restringem** respostas ao domínio da Beauty Pizza.
- **Respondem educadamente** a tentativas de manipulação.

## Proteção do Banco de Dados

- Conexão SQLite **exclusivamente read-only** (`?mode=ro`) — `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER` e `CREATE` são bloqueados a nível de driver.
- **Queries parametrizadas** (`?` placeholders) em todas as consultas — impede SQL injection.

## Máscara de PII no Logging

O `PIIMaskingFilter` mascara dados sensíveis **antes** da gravação em `database/agent_logs.log`:

| Dado | Exemplo | Mascarado |
|---|---|---|
| CPF formatado | `123.456.789-00` | `***.***.***-00` |
| CPF numérico | `12345678900` | `*********00` |
| Telefone | `(11) 99999-8888` | `(11) *****-8888` |

## Isolamento de Sessão

Cada `session_id` é independente — um usuário não acessa dados de outra sessão. Estado e memória são scoped via Agno + SQLite.