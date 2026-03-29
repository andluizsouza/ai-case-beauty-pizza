"""Ponto de entrada do Atendente Virtual Beauty Pizza.

Loop interativo de terminal que recebe mensagens do usuário,
roteia via ``router_agent`` e delega para o agente especializado
(``menu_agent`` ou ``order_agent``), mantendo memória de sessão
via Agno + SQLite.

Uso::

    python src/main.py
"""

import sys
import uuid
from pathlib import Path

# Garante que o diretório raiz do projeto esteja no sys.path
# para permitir execução via `python src/main.py`.
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.agents.menu_agent import create_menu_agent
from src.agents.order_agent import create_order_agent
from src.agents.router_agent import create_router_agent
from src.config import setup_logging
from src.models.routing import TargetAgent
from src.state_manager import StateManager

logger = setup_logging()

WELCOME_MESSAGE = (
    "🍕 Bem-vindo à Beauty Pizza!\n"
    "Sou seu atendente virtual. Posso ajudar com:\n"
    "  • Consultar o cardápio (sabores, preços, ingredientes)\n"
    "  • Fazer e gerenciar pedidos\n"
    "Digite 'sair' para encerrar.\n"
)


def main() -> None:
    """Loop principal do atendente virtual."""
    session_id = str(uuid.uuid4())
    db = StateManager.create_db()

    router = create_router_agent()
    menu = create_menu_agent(session_id=session_id, db=db)
    order = create_order_agent(session_id=session_id, db=db)

    agents = {
        TargetAgent.MENU: menu,
        TargetAgent.ORDER: order,
    }

    logger.info("Sessão iniciada: %s", session_id)
    print(WELCOME_MESSAGE)

    while True:
        try:
            user_input = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté logo! 👋")
            break

        if not user_input:
            continue

        if user_input.lower() in ("sair", "exit", "quit"):
            print("Até logo! 👋")
            break

        logger.info("Usuário: %s", user_input)

        # 1. Rotear mensagem
        try:
            route_response = router.run(user_input)
            decision = route_response.content
            target = TargetAgent(decision.target_agent)
        except Exception:
            logger.exception("Erro no roteamento")
            target = TargetAgent.ORDER

        logger.info("Roteado para: %s", target.value)

        # 2. Delegar para o agente especializado
        agent = agents[target]
        try:
            response = agent.run(user_input)
            reply = response.content or "Desculpe, não consegui processar sua mensagem."
        except Exception:
            logger.exception("Erro no agente %s", target.value)
            reply = "Desculpe, ocorreu um erro. Tente novamente."

        print(f"\n🤖 {reply}\n")
        logger.info("Resposta enviada ao usuário")


if __name__ == "__main__":
    main()
