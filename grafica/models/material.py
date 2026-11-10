"""Material/insumo e regras de estoque (RF-07, RF-09, RF-10)."""
from __future__ import annotations

from .. import config
from ..erros import ErroNegocio


class Material:
    def __init__(self, id, nome, categoria, unidade, custo_unitario, preco_venda,
                 saldo_estoque, limite_minimo, ativo=True):
        self.id = id
        self.nome = nome
        self.categoria = categoria
        self.unidade = unidade
        self.custo_unitario = float(custo_unitario)
        self.preco_venda = float(preco_venda)
        self.saldo_estoque = float(saldo_estoque)
        self.limite_minimo = float(limite_minimo)
        self.ativo = bool(ativo)

    def validar(self) -> None:
        if not self.nome or not self.nome.strip():
            raise ErroNegocio("Informe o nome do material.")
        if self.unidade not in config.UNIDADES:
            raise ErroNegocio(f"Unidade inválida. Use: {', '.join(config.UNIDADES)}.")
        if self.custo_unitario < 0:
            raise ErroNegocio("O custo unitário não pode ser negativo.")
        if self.preco_venda <= 0:
            raise ErroNegocio("O preço de venda deve ser maior que zero.")
        if self.limite_minimo < 0 or self.saldo_estoque < 0:
            raise ErroNegocio("Saldo e limite mínimo não podem ser negativos.")

    def registrar_entrada(self, qtd: float) -> None:
        """RF-10 - soma a quantidade adquirida ao saldo."""
        if qtd <= 0:
            raise ErroNegocio("A quantidade de entrada deve ser maior que zero.")
        self.saldo_estoque = round(self.saldo_estoque + qtd, 4)

    def dar_baixa(self, qtd: float) -> float:
        """Deduz do saldo. Retorna a quantidade que FALTOU (0 se o saldo foi suficiente)."""
        if qtd < 0:
            raise ErroNegocio("A quantidade de baixa não pode ser negativa.")
        if qtd <= self.saldo_estoque:
            self.saldo_estoque = round(self.saldo_estoque - qtd, 4)
            return 0.0
        falta = round(qtd - self.saldo_estoque, 4)
        self.saldo_estoque = 0.0
        return falta

    def verificar_estoque_baixo(self) -> bool:
        """RF-07 - saldo igual ou abaixo do limite mínimo."""
        return self.saldo_estoque <= self.limite_minimo
