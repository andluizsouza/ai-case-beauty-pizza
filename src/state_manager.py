"""Gerenciador de estado da sessão do Atendente Virtual.

Mantém o estado da conversa (``order_id``, histórico de ações,
flag de conclusão) com validação via Pydantic e bloqueio de
atualizações após finalização do pedido.

A persistência é delegada ao ``SqliteDb`` do Agno,
que serializa o estado automaticamente a cada interação.
"""

from agno.db.sqlite import SqliteDb
from pydantic import BaseModel, Field


class SessionState(BaseModel):
    """Modelo do estado persistido por sessão.

    Attributes:
        order_id: ID do pedido ativo na API (``None`` se ainda não criado).
        history: Lista de ações realizadas na sessão (resumos curtos).
        is_completed: Indica se o pedido foi finalizado. Quando ``True``,
            impede qualquer atualização posterior.
    """

    order_id: int | None = None
    history: list[str] = Field(default_factory=list)
    is_completed: bool = False


class StateCompletedError(Exception):
    """Exceção levantada ao tentar atualizar um pedido já finalizado."""


class StateManager:
    """Gerencia o estado da sessão com bloqueio para pedidos finalizados.

    Exemplo de uso com Agno::

        db = StateManager.create_db("sessions.db")
        manager = StateManager(session_state=agent.session_state)
        manager.update(order_id=42)
        manager.add_history("Pedido criado")
        agent.session_state = manager.to_dict()
    """

    def __init__(self, session_state: dict | None = None) -> None:
        raw = session_state or {}
        self._state = SessionState(**raw)

    @staticmethod
    def create_db(db_path: str = "agent_sessions.db") -> SqliteDb:
        """Cria o banco SQLite para persistência de sessões via Agno.

        Args:
            db_path: Caminho do arquivo SQLite para sessões.

        Returns:
            Instância de ``SqliteDb`` configurada.
        """
        return SqliteDb(
            db_file=db_path,
            session_table="agent_sessions",
        )

    @property
    def order_id(self) -> int | None:
        """ID do pedido ativo."""
        return self._state.order_id

    @property
    def is_completed(self) -> bool:
        """Se o pedido foi finalizado."""
        return self._state.is_completed

    @property
    def history(self) -> list[str]:
        """Histórico de ações da sessão."""
        return list(self._state.history)

    def update(self, **kwargs: object) -> None:
        """Atualiza campos do estado.

        Args:
            **kwargs: Campos a atualizar (``order_id``, ``is_completed``).

        Raises:
            StateCompletedError: Se o pedido já estiver finalizado.
            ValueError: Se um campo informado não existir no estado.
        """
        if self._state.is_completed:
            raise StateCompletedError(
                "Pedido já finalizado. Não é possível alterar o estado."
            )

        for key, value in kwargs.items():
            if not hasattr(self._state, key):
                raise ValueError(
                    f"Campo '{key}' não existe no estado da sessão."
                )
            setattr(self._state, key, value)

    def add_history(self, entry: str) -> None:
        """Adiciona uma entrada ao histórico da sessão.

        Args:
            entry: Descrição curta da ação realizada.

        Raises:
            StateCompletedError: Se o pedido já estiver finalizado.
        """
        if self._state.is_completed:
            raise StateCompletedError(
                "Pedido já finalizado. Não é possível alterar o estado."
            )
        self._state.history.append(entry)

    def complete(self) -> None:
        """Marca o pedido como finalizado, bloqueando atualizações futuras."""
        self._state.is_completed = True

    def to_dict(self) -> dict:
        """Serializa o estado para dicionário (compatível com Agno).

        Returns:
            Dicionário com todos os campos do estado.
        """
        return self._state.model_dump()
