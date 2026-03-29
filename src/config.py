"""Configurações centrais do projeto e setup do logging."""

import logging
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

from src.security.pii_filter import PIIMaskingFilter

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Configurações carregadas de variáveis de ambiente."""

    google_api_key: str = Field(default="")
    order_api_base_url: str = Field(default="http://localhost:8000/api")
    knowledge_base_path: str = Field(default="database/knowledge_base.db")
    session_db_path: str = Field(default="database/agent_sessions.db")
    logs_filename: str = Field(default="database/agent_logs.log")


settings = Settings()


class SessionFilter(logging.Filter):
    """Injeta ``session_id`` em todo LogRecord.

    Permite atualizar o ``session_id`` em runtime via
    ``set_session_id`` sem reconfigurar o logger.
    """

    def __init__(self) -> None:
        super().__init__()
        self.session_id = "-"

    def filter(self, record: logging.LogRecord) -> bool:
        record.session_id = self.session_id  # type: ignore[attr-defined]
        return True


# Instância global — acessível via set_session_id()
_session_filter = SessionFilter()


def set_session_id(session_id: str) -> None:
    """Define o session_id que será incluído em todas as mensagens de log."""
    _session_filter.session_id = session_id


def setup_logging() -> logging.Logger:
    """Configura e retorna o logger da aplicação com filtro de PII.

    O logger grava em arquivo (definido por ``LOGS_FILENAME``) com mascaramento
    automático de dados sensíveis (CPF, telefone) via ``PIIMaskingFilter``.

    Returns:
        Logger configurado com handler de arquivo e filtro de PII.
    """
    logger = logging.getLogger("beauty_pizza")

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    handler = logging.FileHandler(
        BASE_DIR / settings.logs_filename,
        encoding="utf-8",
    )
    handler.setLevel(logging.INFO)
    handler.addFilter(PIIMaskingFilter())
    handler.addFilter(_session_filter)

    formatter = logging.Formatter(
        "%(asctime)s | %(session_id)s | %(levelname)s | %(filename)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger
