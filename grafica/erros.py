"""Exceções de domínio."""


class ErroNegocio(Exception):
    """Violação de regra de negócio ou dado inválido; a mensagem é exibida ao usuário."""
