"""Modelos de domínio - correspondem ao Diagrama de Classes (seção 4.5).

As classes concentram o comportamento que não depende de banco de dados
(cálculo de orçamento, transições de status, baixa de estoque...).
A persistência fica na camada de serviços.
"""
from .cliente import Cliente
from .constantes import Perfil, Status
from .funcionario import (Administrador, AtendenteVendas, Funcionario, OperadorImpressao,
                          criar_funcionario)
from .material import Material
from .ordem_servico import ItemOrdemServico, OrdemServico

__all__ = ["Administrador", "AtendenteVendas", "Cliente", "Funcionario", "ItemOrdemServico", "Material",
           "OperadorImpressao", "OrdemServico", "Perfil", "Status", "criar_funcionario"]
