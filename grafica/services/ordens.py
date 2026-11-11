"""Ordens de serviço: orçamento, registro, status, fila e conclusão (RF-02 a RF-06, RF-12)."""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .. import config
from ..erros import ErroNegocio
from ..models import ItemOrdemServico, OrdemServico, Perfil, Status
from .clientes import ClienteService
from .comum import agora, exigir
from .materiais import MaterialService


@dataclass
class ResultadoConclusao:
    ordem: OrdemServico
    avisos: list = field(default_factory=list)       # baixas parciais por falta de estoque
    alertas: list = field(default_factory=list)      # materiais que ficaram com estoque baixo


class OrdemServicoService:
    def __init__(self, conn):
        self.conn = conn
        self._materiais = MaterialService(conn)

    # --- leitura ---------------------------------------------------------------
    @staticmethod
    def _de_row(r) -> OrdemServico:
        return OrdemServico(
            r["numero"], r["cliente_id"], r["funcionario_id"], r["largura"], r["altura"], r["arquivo_arte"],
            r["data_criacao"], r["data_entrega"], r["status"], r["valor_total"], r["orcamento_aprovado"],
            cliente_nome=r["cliente_nome"], funcionario_nome=r["funcionario_nome"],
            data_conclusao=r["data_conclusao"])

    _SQL_BASE = ("SELECT o.*, c.nome AS cliente_nome, f.nome AS funcionario_nome FROM ordem_servico o "
                 "JOIN cliente c ON c.id = o.cliente_id JOIN funcionario f ON f.id = o.funcionario_id")

    def listar(self, status: str | None = None, busca: str = "") -> list[OrdemServico]:
        condicoes, params = [], []
        if status:
            condicoes.append("o.status = ?")
            params.append(status)
        busca = (busca or "").strip()
        if busca:
            condicoes.append("(c.nome LIKE ? OR CAST(o.numero AS TEXT) LIKE ?)")
            params += [f"%{busca}%", f"%{busca.lstrip('0') or busca}%"]
        sql = self._SQL_BASE + (" WHERE " + " AND ".join(condicoes) if condicoes else "") + " ORDER BY o.numero DESC"
        return [self._de_row(r) for r in self.conn.execute(sql, params).fetchall()]

    def obter(self, numero: int) -> OrdemServico:
        r = self.conn.execute(self._SQL_BASE + " WHERE o.numero = ?", (numero,)).fetchone()
        if r is None:
            raise ErroNegocio("Ordem de serviço não encontrada.")
        os_ = self._de_row(r)
        itens = self.conn.execute(
            "SELECT i.*, m.nome AS material_nome FROM item_os i JOIN material m ON m.id = i.material_id "
            "WHERE i.os_numero = ? ORDER BY i.id", (numero,)).fetchall()
        os_.itens = [ItemOrdemServico(i["material_id"], i["material_nome"], i["unidade"], i["quantidade"],
                                      i["preco_unitario"], id=i["id"], quantidade_faturada=i["quantidade_faturada"],
                                      subtotal=i["subtotal"], quantidade_utilizada=i["quantidade_utilizada"])
                     for i in itens]
        return os_

    def fila_impressao(self) -> list[OrdemServico]:
        """RF-05 - somente O.S. 'Em Produção', as de entrega mais próxima primeiro."""
        rows = self.conn.execute(
            self._SQL_BASE + " WHERE o.status = ? ORDER BY (o.data_entrega IS NULL), o.data_entrega, o.numero",
            (Status.EM_PRODUCAO,)).fetchall()
        return [self._de_row(r) for r in rows]

    # --- orçamento (RF-03, RN-01, RN-06) ------------------------------------
    def simular_orcamento(self, largura, altura, itens_spec) -> OrdemServico:
        """Monta uma O.S. em memória (sem gravar) e calcula o orçamento.

        itens_spec: lista de (material_id, quantidade). A quantidade é ignorada para
        materiais em m² (calculada pela área) e obrigatória para os demais.
        Os preços unitários são lidos da tabela de materiais neste momento e
        ficam congelados na O.S. quando ela é gravada (RN-06).
        """
        os_ = OrdemServico(None, None, None, largura, altura)
        os_.validar_dimensoes()
        if not itens_spec:
            raise ErroNegocio("Selecione ao menos um material para a O.S.")
        vistos = set()
        for material_id, quantidade in itens_spec:
            if material_id in vistos:
                raise ErroNegocio("O mesmo material não pode ser adicionado duas vezes na O.S.")
            vistos.add(material_id)
            mat = self._materiais.obter(material_id)
            if not mat.ativo:
                raise ErroNegocio(f"O material '{mat.nome}' está desativado.")
            if mat.unidade == config.UNIDADE_AREA:
                qtd = os_.area
            else:
                if quantidade is None or float(quantidade) <= 0:
                    raise ErroNegocio(f"Informe a quantidade de '{mat.nome}' ({mat.unidade}).")
                qtd = float(quantidade)
                if mat.unidade == "un" and qtd != int(qtd):
                    raise ErroNegocio(f"A quantidade de '{mat.nome}' deve ser um número inteiro de unidades.")
            os_.itens.append(ItemOrdemServico(mat.id, mat.nome, mat.unidade, qtd, mat.preco_venda))
        os_.calcular_orcamento()
        return os_

    # --- registro (RF-02) ------------------------------------------------------
    @staticmethod
    def _validar_arte(caminho) -> Path:
        if not caminho:
            raise ErroNegocio("Anexe o arquivo de arte da O.S.")
        p = Path(caminho)
        if not p.is_file() or p.suffix.lower() not in config.EXTENSOES_ARTE:
            formatos = ", ".join(sorted(e.lstrip(".") for e in config.EXTENSOES_ARTE))
            raise ErroNegocio(f"Arquivo de arte inválido. Formatos aceitos: {formatos}.")
        return p

    def registrar(self, usuario, cliente_id, largura, altura, arquivo_arte, itens_spec, data_entrega=None) -> OrdemServico:
        exigir(usuario, Perfil.ATENDENTE, Perfil.ADMINISTRADOR, acao="registrar ordens de serviço")
        ClienteService(self.conn).obter(cliente_id)
        origem = self._validar_arte(arquivo_arte)
        entrega = OrdemServico.validar_data_entrega(data_entrega)
        os_ = self.simular_orcamento(largura, altura, itens_spec)
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO ordem_servico (cliente_id, funcionario_id, data_criacao, data_entrega, largura, altura, "
                "status, valor_total, orcamento_aprovado) VALUES (?,?,?,?,?,?,?,?,0)",
                (cliente_id, usuario.id, agora(), entrega, os_.largura, os_.altura, Status.ORCAMENTO, os_.valor_total))
            numero = cur.lastrowid
            for it in os_.itens:
                self.conn.execute(
                    "INSERT INTO item_os (os_numero, material_id, unidade, quantidade, quantidade_faturada, "
                    "preco_unitario, subtotal) VALUES (?,?,?,?,?,?,?)",
                    (numero, it.material_id, it.unidade, it.quantidade, it.quantidade_faturada,
                     it.preco_unitario, it.subtotal))
            # Copia a arte para a pasta do sistema (evita perder o arquivo se o original for movido).
            config.ARTES_DIR.mkdir(parents=True, exist_ok=True)
            nome_seguro = re.sub(r"[^\w.\-]+", "_", origem.name)
            destino = config.ARTES_DIR / f"OS{numero:05d}_{nome_seguro}"
            shutil.copy2(origem, destino)
            self.conn.execute("UPDATE ordem_servico SET arquivo_arte = ? WHERE numero = ?", (str(destino), numero))
        return self.obter(numero)

    # --- fluxo de status (RF-04, RN-03, RN-04) --------------------------------
    def aprovar_orcamento(self, usuario, numero) -> OrdemServico:
        exigir(usuario, Perfil.ATENDENTE, Perfil.ADMINISTRADOR, acao="aprovar orçamentos")
        os_ = self.obter(numero)
        os_.aprovar_orcamento()                          # valida status e duplicidade
        with self.conn:
            self.conn.execute("UPDATE ordem_servico SET orcamento_aprovado = 1 WHERE numero = ?", (numero,))
        return os_

    def atualizar_status(self, usuario, numero, novo_status) -> OrdemServico:
        if novo_status == Status.CONCLUIDO:
            raise ErroNegocio("Para concluir a O.S. use a Fila de Impressão ('Confirmar Conclusão e Dar Baixa em "
                              "Insumos'): a baixa de estoque só ocorre na conclusão (RN-05).")
        if novo_status in (Status.ENTREGUE, Status.CANCELADO):
            exigir(usuario, Perfil.ATENDENTE, Perfil.ADMINISTRADOR, acao=f"marcar a O.S. como '{novo_status}'")
        os_ = self.obter(numero)
        os_.atualizar_status(novo_status, usuario)       # valida transição, RN-03 e RN-04
        with self.conn:
            self.conn.execute("UPDATE ordem_servico SET status = ? WHERE numero = ?", (os_.status, numero))
        return os_

    # --- conclusão e baixa de estoque (RF-06, RF-07, RN-04, RN-05) -----------
    def confirmar_conclusao(self, usuario, numero, consumos: dict | None = None) -> ResultadoConclusao:
        """consumos: {id_do_item: quantidade_real}. Itens não informados usam a quantidade orçada."""
        exigir(usuario, Perfil.OPERADOR, Perfil.ADMINISTRADOR, acao="concluir ordens de serviço")
        os_ = self.obter(numero)
        os_.atualizar_status(Status.CONCLUIDO, usuario)  # só 'Em Produção' pode concluir
        consumos = consumos or {}
        avisos, tocados = [], []
        with self.conn:
            for item in os_.itens:
                real = float(consumos.get(item.id, item.quantidade))
                if real < 0:
                    raise ErroNegocio(f"Consumo inválido para '{item.material_nome}'.")
                mat = self._materiais.obter(item.material_id)
                falta = mat.dar_baixa(real)
                self.conn.execute("UPDATE material SET saldo_estoque = ? WHERE id = ?", (mat.saldo_estoque, mat.id))
                self.conn.execute("UPDATE item_os SET quantidade_utilizada = ? WHERE id = ?", (real, item.id))
                item.quantidade_utilizada = real
                if falta > 0:                            # EX01 do UC-02: baixa parcial + aviso ao Administrador
                    msg = (f"O.S. {numero:05d}: estoque insuficiente de '{mat.nome}'. Baixa parcial registrada; "
                           f"faltaram {falta:g} {mat.unidade}.")
                    avisos.append(msg)
                    self.conn.execute("INSERT INTO notificacao (mensagem, data) VALUES (?, ?)", (msg, agora()))
                tocados.append(mat)
            self.conn.execute("UPDATE ordem_servico SET status = ?, data_conclusao = ? WHERE numero = ?",
                              (os_.status, agora(), numero))
        alertas = [m for m in tocados if m.verificar_estoque_baixo()]
        return ResultadoConclusao(os_, avisos, alertas)
