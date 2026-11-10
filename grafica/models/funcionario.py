"""Funcionários do sistema: superclasse abstrata e perfis (RF-08, RF-11)."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..erros import ErroNegocio
from ..security import verificar_senha
from .constantes import Perfil


class Funcionario(ABC):
    """Superclasse abstrata dos usuários do sistema (RF-08, RF-11)."""

    ABA_INICIAL = "ordens"
    PERMISSOES: frozenset = frozenset()

    def __init__(self, id, nome, email, senha_hash, ativo=True, precisa_trocar_senha=False):
        self.id = id
        self._nome = nome
        self._email = email
        self._senha = senha_hash          # sempre o hash, nunca a senha em texto
        self.ativo = bool(ativo)
        self.precisa_trocar_senha = bool(precisa_trocar_senha)

    @property
    def nome(self) -> str:
        return self._nome

    @property
    def email(self) -> str:
        return self._email

    @property
    @abstractmethod
    def perfil_acesso(self) -> str:
        """Perfil de acesso (Atendente, Operador ou Administrador)."""

    def autenticar(self, senha: str) -> bool:
        """Confere a senha informada com o hash armazenado."""
        return verificar_senha(senha or "", self._senha)

    def pode_acessar(self, modulo: str) -> bool:
        return modulo in self.PERMISSOES

    def __repr__(self):
        return f"<{type(self).__name__} {self._email}>"


class AtendenteVendas(Funcionario):
    PERMISSOES = frozenset({"ordens", "clientes"})
    ABA_INICIAL = "ordens"

    @property
    def perfil_acesso(self):
        return Perfil.ATENDENTE

    # Métodos do diagrama de classes: delegam para a camada de serviços.
    def cadastrar_cliente(self, servicos, nome, cpf_cnpj, telefone="", email=""):
        return servicos.clientes.salvar(self, nome, cpf_cnpj, telefone, email)

    def registrar_os(self, servicos, **dados):
        return servicos.ordens.registrar(self, **dados)


class OperadorImpressao(Funcionario):
    PERMISSOES = frozenset({"fila", "ordens", "alertas"})
    ABA_INICIAL = "fila"

    @property
    def perfil_acesso(self):
        return Perfil.OPERADOR

    def atualizar_status_os(self, servicos, numero, novo_status):
        return servicos.ordens.atualizar_status(self, numero, novo_status)

    def confirmar_consumo_insumos(self, servicos, numero, consumos=None):
        return servicos.ordens.confirmar_conclusao(self, numero, consumos)


class Administrador(Funcionario):
    PERMISSOES = frozenset({"ordens", "clientes", "fila", "materiais", "alertas", "usuarios"})
    ABA_INICIAL = "ordens"

    @property
    def perfil_acesso(self):
        return Perfil.ADMINISTRADOR


_CLASSES_PERFIL = {
    Perfil.ATENDENTE: AtendenteVendas,
    Perfil.OPERADOR: OperadorImpressao,
    Perfil.ADMINISTRADOR: Administrador,
}


def criar_funcionario(id, nome, email, senha_hash, perfil, ativo=True, precisa_trocar_senha=False) -> Funcionario:
    try:
        classe = _CLASSES_PERFIL[perfil]
    except KeyError:
        raise ErroNegocio(f"Perfil de acesso desconhecido: {perfil}") from None
    return classe(id, nome, email, senha_hash, ativo, precisa_trocar_senha)
