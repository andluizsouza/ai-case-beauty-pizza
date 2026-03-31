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

from agno.db.sqlite import SqliteDb

from src.agents.menu_agent import create_menu_agent
from src.agents.order_agent import create_order_agent
from src.agents.router_agent import create_router_agent
from src.config import set_session_id, setup_logging
from src.models.routing import TargetAgent

logger = setup_logging()

WELCOME_MESSAGE = (
    "🍕 Bem-vindo à Beauty Pizza!\n"
    "Sou seu atendente virtual. Posso ajudar com:\n"
    "  • Consultar o cardápio (sabores, preços, ingredientes)\n"
    "  • Fazer e gerenciar pedidos\n"
    "Digite 'sair' para encerrar.\n"
)


def _route_message(router: object, user_input: str, active_agent: str) -> TargetAgent:
    """Roteia a mensagem do usuário para o agente correto.

    Fornece ao router o contexto do agente ativo para decisões
    mais precisas.
    """
    context = f"[Agente ativo: {active_agent}] {user_input}"
    try:
        route_response = router.run(context)
        decision = route_response.content
        return TargetAgent(decision.target_agent)
    except Exception:
        logger.exception("Erro no roteamento")
        return TargetAgent.MENU


def main() -> None:
    """Loop principal do atendente virtual."""
    session_id = str(uuid.uuid4())
    set_session_id(session_id)
    from src.config import settings

    db = SqliteDb(db_file=settings.session_db_path, session_table="agent_sessions")

    router = create_router_agent()
    menu = create_menu_agent(session_id=session_id, db=db)
    order = create_order_agent(session_id=session_id, db=db)

    agents = {
        TargetAgent.MENU: menu,
        TargetAgent.ORDER: order,
    }

    active_agent = TargetAgent.MENU
    last_agent_reply = ""

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

        # 1. Rotear mensagem (com contexto do agente ativo)
        target = _route_message(router, user_input, active_agent.value)
        previous_agent = active_agent

        if target != active_agent:
            logger.info(
                "Handoff: %s → %s (mensagem repassada silenciosamente)",
                active_agent.value,
                target.value,
            )
            active_agent = target
        else:
            logger.info("Mantendo agente: %s", target.value)

        # 2. Montar mensagem com contexto do agente anterior (handoff)
        #    Quando há troca de menu_agent → order_agent, repassar a última
        #    resposta do cardápio para que o order_agent saiba o que foi discutido.
        agent_input = user_input
        if (
            last_agent_reply
            and previous_agent == TargetAgent.MENU
            and target == TargetAgent.ORDER
        ):
            agent_input = f"[Contexto do cardápio: {last_agent_reply}]\n\n{user_input}"

        # 3. Delegar para o agente especializado
        agent = agents[target]
        try:
            response = agent.run(agent_input)
            reply = response.content or "Desculpe, não consegui processar sua mensagem."
        except Exception:
            logger.exception("Erro no agente %s", target.value)
            reply = "Desculpe, ocorreu um erro. Tente novamente."

        last_agent_reply = reply
        print(f"\n🤖 {reply}\n")
        logger.info("Resposta enviada ao usuário")


if __name__ == "__main__":
    main()
