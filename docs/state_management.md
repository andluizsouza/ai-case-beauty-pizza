# Gerenciamento de Estado da Sessão

Documentação do `StateManager` e do modelo `SessionState`, responsáveis por manter o estado da conversa do atendente virtual.

---

## Problema

O atendente virtual precisa manter contexto entre interações: qual pedido está ativo, quais ações já foram realizadas, e se o pedido já foi finalizado. Além disso, não deve ser possível alterar um pedido após sua conclusão.

## Solução

Um `StateManager` com validação via Pydantic e bloqueio de atualizações após finalização, integrado ao `SqliteDb` do Agno para persistência automática.

---

## Modelo de Estado (`SessionState`)

```python
class SessionState(BaseModel):
    order_id: int | None = None      # ID do pedido ativo na API
    history: list[str] = []          # Ações realizadas na sessão
    is_completed: bool = False       # Flag de finalização
```

| Campo | Tipo | Padrão | Descrição |
|---|---|---|---|
| `order_id` | `int \| None` | `None` | ID do pedido na API de pedidos |
| `history` | `list[str]` | `[]` | Log de ações (ex: "Pedido criado", "Item adicionado") |
| `is_completed` | `bool` | `False` | Quando `True`, bloqueia todas as atualizações |

---

## StateManager — Interface

### Criação

```python
from src.state_manager import StateManager

# Novo estado
manager = StateManager()

# A partir de estado existente (ex: carregado do Agno)
manager = StateManager(session_state={"order_id": 42, "history": ["Pedido criado"]})
```

### Operações

```python
# Atualizar campos
manager.update(order_id=42)

# Adicionar ao histórico
manager.add_history("Pizza Margherita Grande adicionada")

# Marcar como finalizado
manager.complete()

# Serializar para persistência
state_dict = manager.to_dict()
```

### Bloqueio após Finalização

Após `complete()`, qualquer chamada a `update()` ou `add_history()` levanta `StateCompletedError`:

```python
manager.complete()
manager.update(order_id=99)  # ❌ StateCompletedError
manager.add_history("...")   # ❌ StateCompletedError
```

---

## Integração com Agno

O `StateManager` é framework-agnostic — a persistência é feita pelo `SqliteDb` do Agno:

```python
from agno.agent import Agent
from src.state_manager import StateManager

# Criar db (helper estático)
db = StateManager.create_db(db_path="agent_sessions.db")

# No setup do agente
agent = Agent(
    db=db,
    session_id="unique-session-id",
    session_state=StateManager().to_dict(),  # Estado inicial
    ...
)

# Após interação, o Agno persiste automaticamente o session_state
```

### Fluxo Completo

```
1. Usuário inicia sessão
   └─ StateManager() → estado vazio

2. Pedido criado na API
   └─ manager.update(order_id=42)
   └─ manager.add_history("Pedido criado")

3. Itens adicionados
   └─ manager.add_history("Pizza Margherita adicionada")

4. Pedido finalizado
   └─ manager.complete()
   └─ Atualizações bloqueadas a partir daqui
```

---

## Testes

Os testes estão em `tests/test_state_manager.py` e cobrem:

- Estado inicial com valores padrão.
- Atualização de `order_id` e histórico.
- Bloqueio de `update()` e `add_history()` após `complete()`.
- Serialização/desserialização roundtrip.
- Rejeição de campos inexistentes (`ValueError`).

```bash
pytest tests/test_state_manager.py -v
```
