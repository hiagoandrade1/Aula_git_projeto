"""Utilitários compartilhados pelos serviços."""
from datetime import datetime

from .. import config
from ..erros import ErroNegocio

MSG_CREDENCIAIS = "E-mail ou senha inválidos"
MSG_CONTA_INATIVA = "Conta desativada. Contate o Administrador"


def agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def exigir(usuario, *perfis, acao="executar esta ação"):
    """Garante que o perfil do usuário esteja entre os permitidos."""
    if usuario is None or usuario.perfil_acesso not in perfis:
        raise ErroNegocio(f"Seu perfil não tem permissão para {acao}.")


def validar_senha(senha: str) -> None:
    if not senha or len(senha) < config.TAMANHO_MIN_SENHA:
        raise ErroNegocio(f"A senha deve ter pelo menos {config.TAMANHO_MIN_SENHA} caracteres.")
    if len(senha.encode("utf-8")) > 72:
        raise ErroNegocio("A senha deve ter no máximo 72 bytes.")
