"""Filtro de logging para mascarar dados sensíveis (PII).

Implementa um ``logging.Filter`` que identifica padrões de CPF e telefone
nas mensagens de log e os substitui por versões mascaradas antes da gravação
em arquivo. Garante conformidade com OWASP LLM Top 10 e LGPD.
"""

import logging
import re


class PIIMaskingFilter(logging.Filter):
    """Filtro que identifica e mascara padrões de PII antes da gravação em log.

    Padrões mascarados:
        - CPF formatado: ``123.456.789-00`` → ``***.***.***-00``
        - CPF numérico:  ``12345678900``    → ``*********00``
        - Telefone:      ``(11) 99999-8888`` → ``(11) *****-8888``
    """

    CPF_FORMATTED = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
    CPF_RAW = re.compile(r"(?<!\d)\d{11}(?!\d)")
    PHONE = re.compile(r"(\(\d{2}\)\s?)(\d{4,5})(-\d{4})")

    def filter(self, record: logging.LogRecord) -> bool:
        """Mascara PII na mensagem do log antes da emissão."""
        if record.args:
            try:
                record.msg = str(record.msg) % record.args
            except (TypeError, ValueError):
                record.msg = str(record.msg)
            record.args = None
        record.msg = self._mask(str(record.msg))
        return True

    def _mask(self, text: str) -> str:
        """Aplica todas as regras de mascaramento ao texto."""
        text = self.CPF_FORMATTED.sub(lambda m: f"***.***.***-{m.group()[-2:]}", text)
        text = self.CPF_RAW.sub(lambda m: f"*********{m.group()[-2:]}", text)
        text = self.PHONE.sub(
            lambda m: f"{m.group(1)}{'*' * len(m.group(2))}{m.group(3)}",
            text,
        )
        return text
