"""Testes do filtro de mascaramento de PII no logging."""

import io
import logging

import pytest

from src.security.pii_filter import PIIMaskingFilter


@pytest.fixture()
def pii_logger() -> logging.Logger:
    """Cria um logger com PIIMaskingFilter apontando para StringIO."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(PIIMaskingFilter())
    handler.setFormatter(logging.Formatter("%(message)s"))

    logger = logging.getLogger(f"test_pii_{id(stream)}")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False

    logger._test_stream = stream  # type: ignore[attr-defined]
    return logger


def _get_output(logger: logging.Logger) -> str:
    return logger._test_stream.getvalue()  # type: ignore[attr-defined]


# ---------- CPF ----------


class TestCPFMasking:
    """Testes de mascaramento de CPF."""

    def test_logger_masks_pii_data(self, pii_logger: logging.Logger) -> None:
        """Garante que um CPF vazado no log seja substituído por '***'."""
        cpf = "123.456.789-00"
        pii_logger.info("Cliente com CPF: %s fez pedido", cpf)

        output = _get_output(pii_logger)
        assert "123.456.789-00" not in output
        assert "***.***.***-00" in output

    def test_mask_cpf_formatted(self, pii_logger: logging.Logger) -> None:
        """Mascara CPF no formato XXX.XXX.XXX-XX."""
        pii_logger.info("Doc: 987.654.321-10")

        output = _get_output(pii_logger)
        assert "987.654.321-10" not in output
        assert "***.***.***-10" in output

    def test_mask_cpf_raw(self, pii_logger: logging.Logger) -> None:
        """Mascara CPF sem formatação (11 dígitos)."""
        pii_logger.info("Doc: 12345678900")

        output = _get_output(pii_logger)
        assert "12345678900" not in output
        assert "*********00" in output

    def test_cpf_in_args(self, pii_logger: logging.Logger) -> None:
        """Mascara CPF passado via args do logging."""
        pii_logger.info("CPF do cliente: %s", "11122233344")

        output = _get_output(pii_logger)
        assert "11122233344" not in output
        assert "*********44" in output


# ---------- Telefone ----------


class TestPhoneMasking:
    """Testes de mascaramento de telefone."""

    def test_mask_phone_with_space(self, pii_logger: logging.Logger) -> None:
        """Mascara telefone no formato (XX) XXXXX-XXXX."""
        pii_logger.info("Contato: (11) 99999-8888")

        output = _get_output(pii_logger)
        assert "99999" not in output
        assert "(11) *****-8888" in output

    def test_mask_phone_without_space(self, pii_logger: logging.Logger) -> None:
        """Mascara telefone no formato (XX)XXXXX-XXXX."""
        pii_logger.info("Tel: (21)98765-4321")

        output = _get_output(pii_logger)
        assert "98765" not in output
        assert "(21)*****-4321" in output

    def test_mask_phone_8_digits(self, pii_logger: logging.Logger) -> None:
        """Mascara telefone fixo no formato (XX) XXXX-XXXX."""
        pii_logger.info("Fixo: (11) 3456-7890")

        output = _get_output(pii_logger)
        assert "3456" not in output
        assert "(11) ****-7890" in output


# ---------- Múltiplos padrões ----------


class TestMultiplePatterns:
    """Testes com múltiplos PII na mesma mensagem."""

    def test_mask_cpf_and_phone_together(
        self, pii_logger: logging.Logger
    ) -> None:
        """Mascara CPF e telefone na mesma mensagem."""
        pii_logger.info(
            "Cliente 123.456.789-00 tel (11) 99999-8888 registrado"
        )

        output = _get_output(pii_logger)
        assert "123.456.789-00" not in output
        assert "99999" not in output
        assert "***.***.***-00" in output
        assert "(11) *****-8888" in output

    def test_multiple_cpfs(self, pii_logger: logging.Logger) -> None:
        """Mascara múltiplos CPFs na mesma linha."""
        pii_logger.info("Docs: 111.222.333-44 e 555.666.777-88")

        output = _get_output(pii_logger)
        assert "111.222.333-44" not in output
        assert "555.666.777-88" not in output
        assert "***.***.***-44" in output
        assert "***.***.***-88" in output


# ---------- Sem falsos positivos ----------


class TestNoFalsePositives:
    """Garante que dados legítimos não sejam mascarados."""

    def test_short_numbers_not_masked(
        self, pii_logger: logging.Logger,
    ) -> None:
        """Números menores que 11 dígitos não são mascarados como CPF."""
        pii_logger.info("Pedido 12345 criado com sucesso")

        output = _get_output(pii_logger)
        assert "12345" in output

    def test_regular_text_not_masked(
        self, pii_logger: logging.Logger,
    ) -> None:
        """Texto comum permanece inalterado."""
        msg = "Pizza Margherita Grande Borda Tradicional"
        pii_logger.info(msg)

        output = _get_output(pii_logger)
        assert msg in output

    def test_price_not_masked(self, pii_logger: logging.Logger) -> None:
        """Valores monetários não são mascarados."""
        pii_logger.info("Total: R$ 45.00")

        output = _get_output(pii_logger)
        assert "R$ 45.00" in output
