"""Ordem de Serviço e seus itens (RF-02 a RF-04, RF-12, RN-01, RN-03, RN-04, RN-06)."""
from __future__ import annotations

from datetime import date

from .. import config
from ..erros import ErroNegocio
from .constantes import Perfil, Status
from .funcionario import Funcionario


class ItemOrdemServico:
    """Classe associativa entre OrdemServico e Material.

    Guarda o preço unitário congelado no momento do registro (RN-06).
    """

    def __init__(self, material_id, material_nome, unidade, quantidade, preco_unitario,
                 id=None, quantidade_faturada=None, subtotal=0.0, quantidade_utilizada=None):
        self.id = id
        self.material_id = material_id
        self.material_nome = material_nome
        self.unidade = unidade
        self.quantidade = float(quantidade)                      # quantidade física orçada
        self.quantidade_faturada = float(quantidade if quantidade_faturada is None else quantidade_faturada)
        self.preco_unitario = float(preco_unitario)              # congelado (RN-06)
        self.subtotal = float(subtotal)
        self.quantidade_utilizada = quantidade_utilizada         # consumo real, na conclusão


# ----------------------------------------------------------- Ordem de Serviço
class OrdemServico:
    TRANSICOES = {
        Status.ORCAMENTO: {Status.EM_PRODUCAO, Status.CANCELADO},
        Status.EM_PRODUCAO: {Status.CONCLUIDO, Status.CANCELADO},
        Status.CONCLUIDO: {Status.ENTREGUE},
        Status.ENTREGUE: set(),
        Status.CANCELADO: set(),
    }

    def __init__(self, numero, cliente_id, funcionario_id, largura, altura, arquivo_arte="",
                 data_criacao=None, data_entrega=None, status=Status.ORCAMENTO, valor_total=0.0,
                 orcamento_aprovado=False, itens=None, cliente_nome="", funcionario_nome="",
                 data_conclusao=None):
        self.numero = numero
        self.cliente_id = cliente_id
        self.funcionario_id = funcionario_id
        self.largura = float(largura)
        self.altura = float(altura)
        self.arquivo_arte = arquivo_arte
        self.data_criacao = data_criacao
        self.data_entrega = data_entrega
        self.data_conclusao = data_conclusao
        self.status = status
        self.valor_total = float(valor_total)
        self.orcamento_aprovado = bool(orcamento_aprovado)
        self.itens: list[ItemOrdemServico] = itens or []
        self.cliente_nome = cliente_nome
        self.funcionario_nome = funcionario_nome

    # --- área --------------------------------------------------------------
    @property
    def area(self) -> float:
        return round(self.largura * self.altura, 4)

    @property
    def area_faturada(self) -> float:
        """RN-01 - abaixo de 0,25 m² cobra-se 0,25 m²."""
        return max(self.area, config.AREA_MINIMA_M2)

    def validar_dimensoes(self) -> None:
        if self.largura <= 0 or self.altura <= 0:
            raise ErroNegocio("Largura e altura devem ser maiores que zero.")

    # --- orçamento (RF-03) -------------------------------------------------
    def calcular_orcamento(self) -> float:
        """Calcula subtotais e valor total usando os preços congelados nos itens (RN-06)."""
        self.validar_dimensoes()
        total = 0.0
        for item in self.itens:
            if item.unidade == config.UNIDADE_AREA:
                item.quantidade = self.area
                item.quantidade_faturada = self.area_faturada
            else:
                item.quantidade_faturada = item.quantidade
            item.subtotal = round(item.quantidade_faturada * item.preco_unitario, 2)
            total += item.subtotal
        self.valor_total = round(total, 2)
        return self.valor_total

    # --- aprovação do orçamento (RF-12 / RN-03) ----------------------------
    def aprovar_orcamento(self) -> None:
        """Registra a aprovação do orçamento; pré-requisito para entrar em produção (RN-03)."""
        if self.status != Status.ORCAMENTO:
            raise ErroNegocio("Somente O.S. com status 'Orçamento' podem ter o orçamento aprovado.")
        if self.orcamento_aprovado:
            raise ErroNegocio("O orçamento desta O.S. já foi aprovado.")
        self.orcamento_aprovado = True

    # --- status (RF-04) ----------------------------------------------------
    def atualizar_status(self, novo_status: str, usuario: Funcionario) -> None:
        if novo_status not in Status.TODOS:
            raise ErroNegocio(f"Status inválido: {novo_status}")
        if novo_status not in self.TRANSICOES[self.status]:
            raise ErroNegocio(f"Transição não permitida: '{self.status}' → '{novo_status}'.")
        if novo_status == Status.EM_PRODUCAO and not self.orcamento_aprovado:
            raise ErroNegocio("RN-03: o orçamento precisa ser aprovado antes de iniciar a produção.")
        if novo_status == Status.CONCLUIDO and usuario.perfil_acesso not in (Perfil.OPERADOR, Perfil.ADMINISTRADOR):
            raise ErroNegocio("RN-04: somente Operador de Impressão ou Administrador podem concluir uma O.S.")
        self.status = novo_status

    @staticmethod
    def validar_data_entrega(data_iso):
        if not data_iso:
            return None
        try:
            d = date.fromisoformat(data_iso)
        except ValueError:
            raise ErroNegocio("Data de entrega inválida. Use DD/MM/AAAA.") from None
        if d < date.today():
            raise ErroNegocio("A data de entrega não pode estar no passado.")
        return d.isoformat()
