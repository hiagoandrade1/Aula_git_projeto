"""Gerenciamento de usuários - somente Administrador (RF-11)."""
from __future__ import annotations

import sqlite3

from ..erros import ErroNegocio
from ..models import Funcionario, Perfil
from ..security import gerar_hash
from ..validacao import email_valido
from .autenticacao import funcionario_de_row
from .comum import exigir, validar_senha


class UsuarioService:
    def __init__(self, conn):
        self.conn = conn

    def listar(self) -> list[Funcionario]:
        rows = self.conn.execute("SELECT * FROM funcionario ORDER BY nome COLLATE NOCASE").fetchall()
        return [funcionario_de_row(r) for r in rows]

    def _garantir_outro_admin(self, usuario_id):
        n = self.conn.execute(
            "SELECT COUNT(*) FROM funcionario WHERE perfil = ? AND ativo = 1 AND id <> ?",
            (Perfil.ADMINISTRADOR, usuario_id)).fetchone()[0]
        if n == 0:
            raise ErroNegocio("Deve existir ao menos um Administrador ativo no sistema.")

    def _obter(self, usuario_id) -> Funcionario:
        row = self.conn.execute("SELECT * FROM funcionario WHERE id = ?", (usuario_id,)).fetchone()
        if row is None:
            raise ErroNegocio("Usuário não encontrado.")
        return funcionario_de_row(row)

    def criar(self, admin, nome, email, perfil, senha_inicial) -> int:
        exigir(admin, Perfil.ADMINISTRADOR, acao="gerenciar usuários")
        nome, email = (nome or "").strip(), (email or "").strip().lower()
        if len(nome) < 3:
            raise ErroNegocio("Informe o nome do funcionário.")
        if not email_valido(email):
            raise ErroNegocio("E-mail inválido.")
        if perfil not in Perfil.TODOS:
            raise ErroNegocio("Selecione um perfil de acesso válido.")
        validar_senha(senha_inicial)
        try:
            with self.conn:
                cur = self.conn.execute(
                    "INSERT INTO funcionario (nome, email, senha_hash, perfil, ativo, precisa_trocar_senha) "
                    "VALUES (?,?,?,?,1,1)", (nome, email, gerar_hash(senha_inicial), perfil))
        except sqlite3.IntegrityError:
            raise ErroNegocio("Já existe um funcionário com este e-mail.") from None
        return cur.lastrowid

    def alterar(self, admin, usuario_id, nome, perfil) -> None:
        exigir(admin, Perfil.ADMINISTRADOR, acao="gerenciar usuários")
        alvo = self._obter(usuario_id)
        nome = (nome or "").strip()
        if len(nome) < 3:
            raise ErroNegocio("Informe o nome do funcionário.")
        if perfil not in Perfil.TODOS:
            raise ErroNegocio("Selecione um perfil de acesso válido.")
        if alvo.perfil_acesso == Perfil.ADMINISTRADOR and perfil != Perfil.ADMINISTRADOR and alvo.ativo:
            self._garantir_outro_admin(usuario_id)
        with self.conn:
            self.conn.execute("UPDATE funcionario SET nome = ?, perfil = ? WHERE id = ?", (nome, perfil, usuario_id))

    def definir_ativo(self, admin, usuario_id, ativo: bool) -> None:
        exigir(admin, Perfil.ADMINISTRADOR, acao="gerenciar usuários")
        alvo = self._obter(usuario_id)
        if not ativo:
            if admin.id == usuario_id:
                raise ErroNegocio("Você não pode desativar a sua própria conta.")
            if alvo.perfil_acesso == Perfil.ADMINISTRADOR:
                self._garantir_outro_admin(usuario_id)
        with self.conn:
            self.conn.execute("UPDATE funcionario SET ativo = ? WHERE id = ?", (1 if ativo else 0, usuario_id))

    def redefinir_senha(self, admin, usuario_id, senha_temporaria) -> None:
        exigir(admin, Perfil.ADMINISTRADOR, acao="gerenciar usuários")
        self._obter(usuario_id)
        validar_senha(senha_temporaria)
        with self.conn:
            self.conn.execute("UPDATE funcionario SET senha_hash = ?, precisa_trocar_senha = 1 WHERE id = ?",
                              (gerar_hash(senha_temporaria), usuario_id))
