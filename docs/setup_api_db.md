# Setup da API de Pedidos e Banco de Conhecimento

Guia para configurar o ambiente local: clonar a API de pedidos, preparar o banco SQLite do cardápio e subir o servidor.

---

## Pré-requisitos

- Python 3.11+
- [Poetry](https://python-poetry.org/docs/#installation) (gerenciador de dependências da API)
- Git
- SQLite3 (já incluso na maioria das distribuições Linux e no Python)

---

## 1. Clonar o Repositório da API de Pedidos

```bash
git clone https://github.com/gbtech-oss/candidates-case-order-api.git
cd candidates-case-order-api
```

---

## 2. Instalar Dependências da API

```bash
# Instalar Poetry (caso não tenha)
curl -sSL https://install.python-poetry.org | python3 -
export PATH="$HOME/.local/bin:$PATH"

# Instalar dependências do projeto
poetry install
```

---

## 3. Aplicar Migrações e Subir a API

```bash
# Criar/atualizar o banco de dados da API (db.sqlite3 para pedidos)
poetry run python manage.py migrate

# Subir o servidor de desenvolvimento
poetry run python manage.py runserver
```

A API estará disponível em: **http://localhost:8000/api/**

### Documentação Interativa

| Interface | URL |
|---|---|
| Swagger UI | http://localhost:8000/swagger/ |
| Redoc | http://localhost:8000/doc/ |

---

## 4. Configurar o Banco SQLite do Cardápio (Knowledge Base)

O banco de conhecimento do cardápio está no repositório clonado em `knowledge_base/knowledge_base.sql`.

### Gerar o arquivo `.db` a partir do script SQL

```bash
# Dentro do repositório clonado (candidates-case-order-api/)
cd knowledge_base
sqlite3 knowledge_base.db < knowledge_base.sql
```

### Copiar o banco para o projeto Beauty Pizza

```bash
# A partir da raiz do projeto Case-Beauty-Pizza/
mkdir -p knowledge_base
cp /caminho/para/candidates-case-order-api/knowledge_base/knowledge_base.sql knowledge_base/
cp /caminho/para/candidates-case-order-api/knowledge_base/knowledge_base.db knowledge_base/
```

### Verificar o banco (opcional)

```bash
sqlite3 knowledge_base/knowledge_base.db

-- Listar tabelas
.tables

-- Verificar sabores disponíveis
SELECT sabor FROM pizzas;

-- Verificar preços de uma pizza
SELECT p.sabor, t.tamanho, b.tipo AS borda, pr.preco
FROM precos pr
JOIN pizzas p ON p.id = pr.pizza_id
JOIN tamanhos t ON t.id = pr.tamanho_id
JOIN bordas b ON b.id = pr.borda_id
WHERE p.sabor = 'Margherita';

.quit
```

> **Importante:** O banco do cardápio deve ser acessado em modo **read-only** pela aplicação (`?mode=ro`). Veja `.github/copilot-instructions.md` para detalhes de segurança.

---

## 5. Configurar Variáveis de Ambiente

```bash
cp .env.example .env
```

Edite o `.env` com sua chave da API Gemini e ajuste os caminhos conforme necessário.
