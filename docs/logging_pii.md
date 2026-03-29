# Logging com Máscara de PII

Documentação do sistema de logging seguro com mascaramento automático de dados sensíveis.

---

## Problema

Logs de aplicação frequentemente capturam dados pessoais (PII) como CPF e telefone durante o fluxo normal de atendimento. Gravar esses dados em texto plano viola a LGPD e as diretrizes OWASP LLM Top 10.

## Solução

Um `logging.Filter` customizado (`PIIMaskingFilter`) intercepta **todas** as mensagens de log **antes** da gravação em arquivo, identificando e substituindo padrões de PII por versões mascaradas.

---

## Padrões Mascarados

| Tipo | Entrada | Saída |
|---|---|---|
| CPF formatado | `123.456.789-00` | `***.***.***-00` |
| CPF numérico | `12345678900` | `*********00` |
| Telefone celular | `(11) 99999-8888` | `(11) *****-8888` |
| Telefone fixo | `(11) 3456-7890` | `(11) ****-7890` |

> Os dois últimos dígitos do CPF e os quatro últimos do telefone são preservados para permitir identificação parcial em debugging, sem expor o dado completo.

---

## Arquitetura

```
logger.info("CPF: 123.456.789-00")
        │
        ▼
┌──────────────────────┐
│   PIIMaskingFilter    │  ← logging.Filter
│   src/security/       │
│   pii_filter.py       │
│                       │
│  1. Formata msg+args  │
│  2. Aplica regex CPF  │
│  3. Aplica regex Tel  │
└──────────┬───────────┘
           ▼
  app.log: "CPF: ***.***.***-00"
```

### Fluxo de Mascaramento

1. O filtro intercepta o `LogRecord` antes do handler processar.
2. Se existem `args` (ex: `logger.info("CPF: %s", cpf)`), a mensagem é formatada antecipadamente para capturar PII nos argumentos.
3. Três regex são aplicados em sequência: CPF formatado → CPF numérico → Telefone.
4. A mensagem mascarada segue para o handler (arquivo `app.log`).

---

## Uso

O logger é configurado centralmente em `src/config.py`:

```python
from src.config import setup_logging

logger = setup_logging()
logger.info("Pedido do cliente CPF 123.456.789-00")
# app.log → "Pedido do cliente CPF ***.***.***-00"
```

Qualquer módulo que use o logger `beauty_pizza` terá PII automaticamente mascarado:

```python
import logging

logger = logging.getLogger("beauty_pizza")
logger.info("Tel: (11) 99999-8888")
# app.log → "Tel: (11) *****-8888"
```

---

## Testes

Ver [tests.md](tests.md) para o inventário completo de testes do PII filter.
