"""Cadastro de clientes (RF-01, RN-02)."""
from __future__ import annotations

import sqlite3

from ..erros import ErroNegocio
from ..models import Cliente, Perfil
from ..validacao import so_digitos
from .comum import exigir


class ClienteService:
    def __init__(self, conn):
        self.conn = conn

    @staticmethod
    def _de_row(r) -> Cliente:
        return Cliente(r["id"], r["nome"], r["cpf_cnpj"], r["telefone"], r["email"])

    def listar(self, busca: str = "") -> list[Cliente]:
        busca = (busca or "").strip()
        if busca:
            digitos = so_digitos(busca)
            rows = self.conn.execute(
                "SELECT * FROM cliente WHERE nome LIKE ? OR telefone LIKE ? OR (? <> '' AND cpf_cnpj LIKE ?) "
                "ORDER BY nome COLLATE NOCASE",
                (f"%{busca}%", f"%{busca}%", digitos, f"%{digitos}%")).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM cliente ORDER BY nome COLLATE NOCASE").fetchall()
        return [self._de_row(r) for r in rows]

    def obter(self, cliente_id) -> Cliente:
        r = self.conn.execute("SELECT * FROM cliente WHERE id = ?", (cliente_id,)).fetchone()
        if r is None:
            raise ErroNegocio("Cliente não encontrado.")
        return self._de_row(r)

    def salvar(self, usuario, nome, cpf_cnpj, telefone="", email="", cliente_id=None) -> Cliente:
        exigir(usuario, Perfil.ATENDENTE, Perfil.ADMINISTRADOR, acao="gerenciar clientes")
        cliente = Cliente(cliente_id, (nome or "").strip(), cpf_cnpj, (telefone or "").strip(),
                          (email or "").strip().lower())
        cliente.validar()
        dup = self.conn.execute(
            "SELECT id FROM cliente WHERE cpf_cnpj = ? AND (? IS NULL OR id <> ?)",
            (cliente.cpf_cnpj, cliente_id, cliente_id)).fetchone()
        if dup:
            raise ErroNegocio("RN-02: já existe um cliente cadastrado com este CPF/CNPJ.")
        try:
            with self.conn:
                if cliente_id is None:
                    cur = self.conn.execute(
                        "INSERT INTO cliente (nome, cpf_cnpj, telefone, email) VALUES (?,?,?,?)",
                        (cliente.nome, cliente.cpf_cnpj, cliente.telefone, cliente.email))
                    cliente.id = cur.lastrowid
                else:
                    self.obter(cliente_id)
                    self.conn.execute(
                        "UPDATE cliente SET nome = ?, cpf_cnpj = ?, telefone = ?, email = ? WHERE id = ?",
                        (cliente.nome, cliente.cpf_cnpj, cliente.telefone, cliente.email, cliente_id))
        except sqlite3.IntegrityError:
            raise ErroNegocio("RN-02: já existe um cliente cadastrado com este CPF/CNPJ.") from None
        return cliente
