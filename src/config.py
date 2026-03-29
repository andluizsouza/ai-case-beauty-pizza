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

    gemini_api_key: str = Field(default="")
    order_api_base_url: str = Field(default="http://localhost:8000/api")
    knowledge_base_path: str = Field(default="database/knowledge_base.db")
    session_db_path: str = Field(default="database/agent_sessions.db")
    log_file: str = Field(default="app.log")


settings = Settings()


def setup_logging() -> logging.Logger:
    """Configura e retorna o logger da aplicação com filtro de PII.

    O logger grava em arquivo (``app.log``) com mascaramento automático
    de dados sensíveis (CPF, telefone) via ``PIIMaskingFilter``.

    Returns:
        Logger configurado com handler de arquivo e filtro de PII.
    """
    logger = logging.getLogger("beauty_pizza")

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    handler = logging.FileHandler(
        BASE_DIR / settings.log_file,
        encoding="utf-8",
    )
    handler.setLevel(logging.INFO)
    handler.addFilter(PIIMaskingFilter())

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger
