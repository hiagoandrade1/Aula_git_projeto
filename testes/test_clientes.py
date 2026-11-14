"""Testes do cadastro de clientes (RF-01, RN-02)."""
import unittest

from base import CNPJ_OK, CPF_OK, BaseUsuarios  # noqa: E402
from grafica.erros import ErroNegocio  # noqa: E402


class TestClientes(BaseUsuarios):
    def setUp(self):
        super().setUp()
        self.cliente = self.s.clientes.salvar(self.atendente, "João da Silva", CPF_OK)

    def test_unicidade_cpf_cnpj(self):                                # RN-02
        with self.assertRaises(ErroNegocio) as ctx:
            self.s.clientes.salvar(self.atendente, "Outro Nome", "52998224725")
        self.assertIn("RN-02", str(ctx.exception))

    def test_edicao_do_proprio_cliente_nao_conflita(self):
        c = self.s.clientes.salvar(self.atendente, "João S. Silva", CPF_OK, cliente_id=self.cliente.id)
        self.assertEqual(c.id, self.cliente.id)

    def test_pessoa_juridica_e_busca(self):
        pj = self.s.clientes.salvar(self.atendente, "Padaria Pão Quente", CNPJ_OK, "(16) 3333-0000", "a@b.com")
        self.assertEqual(pj.tipo_pessoa, "Pessoa Jurídica")
        self.assertEqual([c.id for c in self.s.clientes.listar("11222333")], [pj.id])
        self.assertEqual(len(self.s.clientes.listar()), 2)

    def test_documentos_invalidos(self):
        for doc in ("123", "11111111111", "52998224726", "11222333000182"):
            with self.assertRaises(ErroNegocio):
                self.s.clientes.salvar(self.atendente, "Fulano de Tal", doc)

    def test_operador_nao_cadastra_cliente(self):
        with self.assertRaises(ErroNegocio):
            self.s.clientes.salvar(self.operador, "Fulano de Tal", CNPJ_OK)


if __name__ == "__main__":
    unittest.main()
