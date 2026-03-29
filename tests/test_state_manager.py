"""Testes do gerenciador de estado da sessão."""

import pytest

from src.state_manager import SessionState, StateCompletedError, StateManager


# ---------- SessionState (Pydantic model) ----------


class TestSessionState:
    """Testes do modelo Pydantic de estado."""

    def test_default_values(self) -> None:
        """Estado inicial tem valores padrão corretos."""
        state = SessionState()
        assert state.order_id is None
        assert state.history == []
        assert state.is_completed is False

    def test_from_dict(self) -> None:
        """Reconstrói estado a partir de dicionário."""
        data = {"order_id": 42, "history": ["Pedido criado"], "is_completed": False}
        state = SessionState(**data)
        assert state.order_id == 42
        assert state.history == ["Pedido criado"]

    def test_serialization_roundtrip(self) -> None:
        """Serializa e desserializa sem perda de dados."""
        original = SessionState(order_id=7, history=["a", "b"], is_completed=True)
        restored = SessionState(**original.model_dump())
        assert restored == original


# ---------- StateManager ----------


class TestStateManager:
    """Testes do gerenciador de estado."""

    def test_initial_state(self) -> None:
        """Estado inicializado com valores padrão."""
        manager = StateManager()
        assert manager.order_id is None
        assert manager.is_completed is False
        assert manager.history == []

    def test_from_existing_state(self) -> None:
        """Reconstrói manager a partir de estado existente."""
        state_dict = {"order_id": 10, "history": ["Pedido criado"]}
        manager = StateManager(session_state=state_dict)
        assert manager.order_id == 10
        assert manager.history == ["Pedido criado"]

    def test_update_order_id(self) -> None:
        """Atualiza order_id com sucesso."""
        manager = StateManager()
        manager.update(order_id=42)
        assert manager.order_id == 42

    def test_add_history(self) -> None:
        """Adiciona entradas ao histórico."""
        manager = StateManager()
        manager.add_history("Pedido criado")
        manager.add_history("Item adicionado")
        assert manager.history == ["Pedido criado", "Item adicionado"]

    def test_complete_order(self) -> None:
        """Marca pedido como finalizado."""
        manager = StateManager()
        manager.update(order_id=1)
        manager.complete()
        assert manager.is_completed is True

    def test_to_dict(self) -> None:
        """Serializa estado para dicionário."""
        manager = StateManager()
        manager.update(order_id=5)
        manager.add_history("Criado")

        result = manager.to_dict()
        assert result == {
            "order_id": 5,
            "history": ["Criado"],
            "is_completed": False,
        }


# ---------- Bloqueio após finalização ----------


class TestStateBlocking:
    """Testes de bloqueio de atualizações após finalização."""

    def _completed_manager(self) -> StateManager:
        """Cria um manager com pedido já finalizado."""
        manager = StateManager(session_state={"order_id": 1})
        manager.complete()
        return manager

    def test_block_update_when_completed(self) -> None:
        """Levanta erro ao tentar atualizar estado finalizado."""
        manager = self._completed_manager()
        with pytest.raises(StateCompletedError):
            manager.update(order_id=99)

    def test_block_add_history_when_completed(self) -> None:
        """Levanta erro ao tentar adicionar histórico após finalização."""
        manager = self._completed_manager()
        with pytest.raises(StateCompletedError):
            manager.add_history("Tentativa inválida")

    def test_state_unchanged_after_blocked_update(self) -> None:
        """Estado permanece inalterado após tentativa bloqueada."""
        manager = self._completed_manager()
        try:
            manager.update(order_id=99)
        except StateCompletedError:
            pass
        assert manager.order_id == 1

    def test_update_invalid_field_raises_value_error(self) -> None:
        """Levanta ValueError para campo inexistente."""
        manager = StateManager()
        with pytest.raises(ValueError, match="Campo 'nonexistent'"):
            manager.update(nonexistent="value")
