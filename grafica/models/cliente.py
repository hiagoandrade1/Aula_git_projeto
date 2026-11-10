"""Cliente da gráfica (RF-01, RN-02)."""
from __future__ import annotations

from .. import config
from ..erros import ErroNegocio
from ..validacao import cnpj_valido, cpf_valido, email_valido, so_digitos


class Cliente:
    def __init__(self, id, nome, cpf_cnpj, telefone="", email=""):
        self.id = id
        self.nome = nome
        self.cpf_cnpj = so_digitos(cpf_cnpj)
        self.telefone = telefone
        self.email = email

    @property
    def tipo_pessoa(self) -> str:
        return "Pessoa Física" if len(self.cpf_cnpj) == 11 else "Pessoa Jurídica"

    def validar(self) -> None:
        if not self.nome or len(self.nome.strip()) < 3:
            raise ErroNegocio("Informe o nome do cliente (mínimo de 3 caracteres).")
        if len(self.cpf_cnpj) not in (11, 14):
            raise ErroNegocio("CPF deve ter 11 dígitos e CNPJ deve ter 14 dígitos.")
        if config.VALIDAR_DIGITOS_DOCUMENTO:
            valido = cpf_valido(self.cpf_cnpj) if len(self.cpf_cnpj) == 11 else cnpj_valido(self.cpf_cnpj)
            if not valido:
                raise ErroNegocio("CPF/CNPJ inválido (dígitos verificadores não conferem).")
        if self.email and not email_valido(self.email):
            raise ErroNegocio("E-mail do cliente inválido.")
