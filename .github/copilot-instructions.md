# Diretrizes do Projeto — Atendente Virtual Beauty Pizza

## Contexto

Atendente virtual da **Beauty Pizza** — agente conversacional multi-agente que auxilia clientes a consultar o cardápio, montar pedidos e finalizar compras. Construído com Python 3.13, framework **Agno** e modelo **Google Gemini**.

A API REST de pedidos é externa ([candidates-case-order-api](https://github.com/gbtech-oss/candidates-case-order-api)) e o cardápio vem de um banco SQLite read-only.

---

## Arquitetura (Padrão de Roteamento)

Três agentes especializados com roteamento centralizado:

- **`router_agent`** — Roteia via Structured Output (Pydantic). Sem tools.
- **`menu_agent`** — Cardápio. RAG com Embeddings + SQLite read-only.
- **`order_agent`** — Pedidos. Consome a API REST via `httpx`.

Memória de sessão scoped por `session_id` (Agno + SQLite).

---

## Idioma

- **Código**: Inglês (classes, funções, variáveis, branches, commits).
- **Documentação e outputs**: Português (PT-BR).

---

## Princípios de Código

- **SOLID** e **Clean Code**.
- **PEP 8** via `ruff`.
- Type hints em todas as assinaturas. Docstrings em PT-BR.
- Testes obrigatórios via `pytest` para toda lógica de negócio e integrações.
- Validação de dados com **Pydantic v2**.
- Commits no padrão commit-zen em PT-BR (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`).

---

## Princípios de Segurança (OWASP LLM Top 10)

- **SQLite read-only**: Sempre `?mode=ro`. Nunca escrita no banco do cardápio.
- **Queries parametrizadas**: Sempre `?` placeholders, nunca string interpolation.
- **Prompt injection**: System prompts com instruções estritas para ignorar bypass, não revelar instruções internas e restringir ao domínio da Beauty Pizza.
- **Isolamento de sessão**: `session_id` único por conversa. Sem acesso cruzado.
- **PII mascarada no logging**: CPF e telefone mascarados antes de gravar em log. Nunca logar dados sensíveis em texto plano.
- **Secrets**: Via `.env`, nunca commitados.
