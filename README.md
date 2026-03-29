# 🍕 Atendente Virtual — Beauty Pizza

Agente conversacional multi-agente que auxilia clientes da Beauty Pizza a consultar o cardápio, montar pedidos e gerenciar entregas. Construído com **Python 3.13**, framework **Agno** e modelo **Google Gemini**.

---

## Visão Geral

O sistema utiliza três agentes especializados orquestrados por um padrão de **roteamento**:

```mermaid
flowchart LR
    U["👤 Usuário"] <--> R["🤖 router_agent"]
    R --> M["📋 menu_agent"]
    R --> O["🛒 order_agent"]
```

| Agente | Função | Tools |
|---|---|---|
| `router_agent` | Roteia mensagens via Structured Output (Pydantic) | Nenhuma |
| `menu_agent` | Consultas ao cardápio (RAG + Embeddings) | `get_menu_report`, `search_menu`, `get_pizza_price` |
| `order_agent` | Gestão de pedidos via API REST | `get_pizza_price` + 6 tools de pedidos |

### Fontes de Dados

| Fonte | Acesso | Origem |
|---|---|---|
| Cardápio (SQLite) | Read-only (`?mode=ro`) | [candidates-case-order-api](https://github.com/gbtech-oss/candidates-case-order-api) — `knowledge_base/` |
| API de Pedidos (REST) | HTTP via `httpx` | [candidates-case-order-api](https://github.com/gbtech-oss/candidates-case-order-api) — Django server |

---

## Instalação e Execução

### Pré-requisitos

- Python 3.13+
- Chave de API do Google Gemini
- API de pedidos rodando localmente (ver [docs/setup_api_db.md](docs/setup_api_db.md))

### 1. Clonar e instalar

```bash
git clone <repo-url>
cd Case-Beauty-Pizza

python -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate    # Windows

pip install -r requirements.txt
```

### 2. Configurar ambiente

```bash
cp .env.example .env
# Edite .env com sua GEMINI_API_KEY
```

### 3. Preparar o banco do cardápio

Siga o guia completo em [docs/setup_api_db.md](docs/setup_api_db.md) para clonar a API, gerar o `knowledge_base.db` e subir o servidor de pedidos.

### 4. Executar

```bash
python src/main.py
```

---

## Agentic Design Patterns

### 1. `router_agent`

O `router_agent` é o ponto de entrada único. Recebe toda mensagem do usuário e retorna um `RouteDecision` (Pydantic + Enum) indicando o agente alvo — sem ambiguidade, sem tools, sem texto livre. Isso garante uma delegação determinística.

### 2. `menu_agent`

Especialista em cardápio, responde exclusivamente a consultas sobre sabores, tamanhos, bordas e preços. Usa RAG (Relational Augmented Generation) para gerar respostas completas a partir do banco SQLite, sem hardcoding de regras.

O `menu_agent` combina busca semântica com geração de texto:

1. **`get_menu_report`** — Gera relatório descritivo completo do banco (sabores, bordas, tamanhos, combinações válidas, preços). Todas as regras de negócio são **derivadas dos dados** — zero hardcoding.
2. **`search_menu`** — Gera embeddings (Gemini) para a query do usuário e cada item do cardápio, retornando os mais similares por cosseno.
3. **`get_pizza_price`** — Consulta exata de preço via query parametrizada.

### 3. `order_agent`

Gerencia a jornada de pedidos via API REST. Tem acesso a tools para criar pedidos, adicionar itens, definir endereço e consultar status. O `order_agent` é o único responsável por interações relacionadas a pedidos — o `menu_agent` não tem permissão para falar sobre preços ou disponibilidade.

O `order_agent` tem acesso a `get_pizza_price` para obter preços ao montar pedidos. Consultas sobre o cardápio são redirecionadas automaticamente para o `menu_agent` pelo router.

### Memória de Sessão

Cada sessão tem um `session_id` único (UUID). Os agentes usam `add_history_to_context=True` com até 15 turnos de histórico, garantindo que informações fornecidas em mensagens anteriores (nome, CPF, sabor) sejam lembradas.

---

## Segurança

O projeto implementa proteções inspiradas no **OWASP LLM Top 10**:

### Prevenção de Prompt Injection

Todos os agentes possuem instruções estritas que:
- **Ignoram** comandos de bypass ("ignore suas instruções", "modo desenvolvedor").
- **Nunca revelam** system prompts ou configurações internas.
- **Restringem** respostas ao domínio da Beauty Pizza.
- **Respondem educadamente** a tentativas de manipulação.

### Proteção do Banco de Dados

- Conexão SQLite **exclusivamente read-only** (`?mode=ro`) — `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER` e `CREATE` são bloqueados a nível de driver.
- **Queries parametrizadas** (`?` placeholders) em todas as consultas — impede SQL injection.

### Máscara de PII no Logging

O `PIIMaskingFilter` mascara dados sensíveis **antes** da gravação em `app.log`:

| Dado | Exemplo | Mascarado |
|---|---|---|
| CPF formatado | `123.456.789-00` | `***.***.***-00` |
| CPF numérico | `12345678900` | `*********00` |
| Telefone | `(11) 99999-8888` | `(11) *****-8888` |

### Isolamento de Sessão

Cada `session_id` é independente — um usuário não acessa dados de outra sessão. Estado e memória são scoped via Agno + SQLite.

---

## Testes

```bash
# Executar toda a suíte
python -m pytest tests/ -v

# Executar por módulo
python -m pytest tests/test_agents.py -v
python -m pytest tests/test_e2e.py -v
python -m pytest tests/test_tools.py -v
python -m pytest tests/test_pii_filter.py -v
```

A suíte cobre configuração de agentes, jornada e2e do cliente, segurança (red teaming), tools de cardápio/pedidos e mascaramento de PII.

Inventário completo: [docs/tests.md](docs/tests.md)

---

## Estrutura do Projeto

```
Case-Beauty-Pizza/
├── src/
│   ├── agents/                # Agentes Agno (router, menu, order)
│   ├── tools/                 # Tools (cardápio SQLite, API pedidos)
│   ├── models/                # Pydantic models (routing)
│   ├── security/              # PII filter
│   ├── config.py              # Settings + logging
│   ├── model_params.py        # IDs dos modelos (LLM, embeddings)
│   └── main.py                # Ponto de entrada (terminal)
├── database/
│   ├── knowledge_base.db      # Cardápio (read-only)
│   └── agent_sessions.db      # Sessões persistidas
├── tests/                     # Testes (pytest)
├── docs/                      # Documentação técnica
└── requirements.txt
```

---

## Documentação Técnica

| Documento | Conteúdo |
|---|---|
| [docs/tests.md](docs/tests.md) | Inventário de testes e cobertura por módulo |
| [docs/setup_api_db.md](docs/setup_api_db.md) | Setup: API de pedidos, banco do cardápio, variáveis de ambiente |

---

## Stack

| Componente | Tecnologia |
|---|---|
| Linguagem | Python 3.13 |
| Framework de Agentes | Agno |
| LLM | Google Gemini (`gemini-2.5-flash`) |
| Embeddings | `gemini-embedding-001` |
| Banco do Cardápio | SQLite (read-only) |
| API de Pedidos | REST (Django) |
| HTTP Client | httpx |
| Validação | Pydantic v2 |
| Testes | pytest |
| Linting | ruff |
