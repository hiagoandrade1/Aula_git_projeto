"""Materiais, entradas de estoque e notificações (RF-07, RF-09, RF-10)."""
from __future__ import annotations

import sqlite3

from ..erros import ErroNegocio
from ..models import Material, Perfil
from .comum import agora, exigir


class MaterialService:
    def __init__(self, conn):
        self.conn = conn

    @staticmethod
    def _de_row(r) -> Material:
        return Material(r["id"], r["nome"], r["categoria"], r["unidade"], r["custo_unitario"],
                        r["preco_venda"], r["saldo_estoque"], r["limite_minimo"], r["ativo"])

    def listar(self, apenas_ativos: bool = False) -> list[Material]:
        sql = "SELECT * FROM material"
        if apenas_ativos:
            sql += " WHERE ativo = 1"
        rows = self.conn.execute(sql + " ORDER BY categoria COLLATE NOCASE, nome COLLATE NOCASE").fetchall()
        return [self._de_row(r) for r in rows]

    def obter(self, material_id) -> Material:
        r = self.conn.execute("SELECT * FROM material WHERE id = ?", (material_id,)).fetchone()
        if r is None:
            raise ErroNegocio("Material não encontrado.")
        return self._de_row(r)

    def listar_estoque_baixo(self) -> list[Material]:
        """RF-07 - materiais ativos com saldo <= limite mínimo."""
        rows = self.conn.execute(
            "SELECT * FROM material WHERE ativo = 1 AND saldo_estoque <= limite_minimo "
            "ORDER BY nome COLLATE NOCASE").fetchall()
        return [self._de_row(r) for r in rows]

    def salvar(self, usuario, nome, categoria, unidade, custo_unitario, preco_venda, limite_minimo,
               saldo_inicial=0.0, material_id=None) -> Material:
        """RF-09. O saldo só pode ser definido na criação; depois, apenas por entradas (RF-10) e baixas."""
        exigir(usuario, Perfil.ADMINISTRADOR, acao="gerenciar materiais")
        if material_id is None:
            saldo = float(saldo_inicial)
        else:
            saldo = self.obter(material_id).saldo_estoque
        material = Material(material_id, (nome or "").strip(), (categoria or "").strip(), unidade,
                            custo_unitario, preco_venda, saldo, limite_minimo)
        material.validar()
        try:
            with self.conn:
                if material_id is None:
                    cur = self.conn.execute(
                        "INSERT INTO material (nome, categoria, unidade, custo_unitario, preco_venda, "
                        "saldo_estoque, limite_minimo) VALUES (?,?,?,?,?,?,?)",
                        (material.nome, material.categoria, material.unidade, material.custo_unitario,
                         material.preco_venda, material.saldo_estoque, material.limite_minimo))
                    material.id = cur.lastrowid
                    if material.saldo_estoque > 0:
                        self.conn.execute(
                            "INSERT INTO entrada_estoque (material_id, funcionario_id, quantidade, data) "
                            "VALUES (?,?,?,?)", (material.id, usuario.id, material.saldo_estoque, agora()))
                else:
                    self.conn.execute(
                        "UPDATE material SET nome = ?, categoria = ?, unidade = ?, custo_unitario = ?, "
                        "preco_venda = ?, limite_minimo = ? WHERE id = ?",
                        (material.nome, material.categoria, material.unidade, material.custo_unitario,
                         material.preco_venda, material.limite_minimo, material_id))
        except sqlite3.IntegrityError:
            raise ErroNegocio("Já existe um material com este nome.") from None
        return material

    def definir_ativo(self, usuario, material_id, ativo: bool) -> None:
        exigir(usuario, Perfil.ADMINISTRADOR, acao="gerenciar materiais")
        self.obter(material_id)
        with self.conn:
            self.conn.execute("UPDATE material SET ativo = ? WHERE id = ?", (1 if ativo else 0, material_id))

    def registrar_entrada(self, usuario, material_id, quantidade) -> Material:
        """RF-10."""
        exigir(usuario, Perfil.ADMINISTRADOR, acao="registrar entradas de estoque")
        material = self.obter(material_id)
        material.registrar_entrada(float(quantidade))
        with self.conn:
            self.conn.execute("UPDATE material SET saldo_estoque = ? WHERE id = ?",
                              (material.saldo_estoque, material_id))
            self.conn.execute(
                "INSERT INTO entrada_estoque (material_id, funcionario_id, quantidade, data) VALUES (?,?,?,?)",
                (material_id, usuario.id, float(quantidade), agora()))
        return material

    # --- notificações para o Administrador (EX01 do UC-02) -------------------
    def listar_notificacoes(self, somente_nao_lidas: bool = True) -> list[dict]:
        sql = "SELECT * FROM notificacao"
        if somente_nao_lidas:
            sql += " WHERE lida = 0"
        return [dict(r) for r in self.conn.execute(sql + " ORDER BY id DESC").fetchall()]

    def marcar_notificacoes_lidas(self, usuario) -> None:
        exigir(usuario, Perfil.ADMINISTRADOR, acao="gerenciar notificações")
        with self.conn:
            self.conn.execute("UPDATE notificacao SET lida = 1 WHERE lida = 0")
