"""Autenticação e troca de senha (RF-08)."""
from __future__ import annotations

from ..erros import ErroNegocio
from ..models import Funcionario, criar_funcionario
from ..security import gerar_hash
from .comum import MSG_CONTA_INATIVA, MSG_CREDENCIAIS, validar_senha


def funcionario_de_row(row) -> Funcionario:
    return criar_funcionario(row["id"], row["nome"], row["email"], row["senha_hash"], row["perfil"],
                             row["ativo"], row["precisa_trocar_senha"])


class AuthService:
    def __init__(self, conn):
        self.conn = conn

    def login(self, email: str, senha: str) -> Funcionario:
        email = (email or "").strip().lower()
        row = self.conn.execute("SELECT * FROM funcionario WHERE email = ?", (email,)).fetchone()
        if row is None or not senha:
            raise ErroNegocio(MSG_CREDENCIAIS)               # EX01: não revela qual campo errou
        usuario = funcionario_de_row(row)
        if not usuario.autenticar(senha):
            raise ErroNegocio(MSG_CREDENCIAIS)
        if not usuario.ativo:                                # EX02
            raise ErroNegocio(MSG_CONTA_INATIVA)
        return usuario

    def trocar_senha(self, usuario: Funcionario, nova_senha: str, senha_atual: str | None = None) -> None:
        if senha_atual is not None and not usuario.autenticar(senha_atual):
            raise ErroNegocio("Senha atual incorreta.")
        validar_senha(nova_senha)
        if usuario.autenticar(nova_senha):
            raise ErroNegocio("A nova senha deve ser diferente da senha atual.")
        novo_hash = gerar_hash(nova_senha)
        with self.conn:
            self.conn.execute("UPDATE funcionario SET senha_hash = ?, precisa_trocar_senha = 0 WHERE id = ?",
                              (novo_hash, usuario.id))
        usuario._senha = novo_hash
        usuario.precisa_trocar_senha = False
