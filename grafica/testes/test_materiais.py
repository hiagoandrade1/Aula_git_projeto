"""Testes de materiais e entradas de estoque (RF-09, RF-10)."""
import unittest

from base import BaseCatalogo  # noqa: E402
from grafica.erros import ErroNegocio  # noqa: E402


class TestMateriais(BaseCatalogo):
    def test_entrada_de_estoque(self):                                # RF-10
        m = self.s.materiais.registrar_entrada(self.admin, self.lona.id, 25)
        self.assertAlmostEqual(m.saldo_estoque, 35)
        with self.assertRaises(ErroNegocio):
            self.s.materiais.registrar_entrada(self.admin, self.lona.id, 0)
        with self.assertRaises(ErroNegocio):
            self.s.materiais.registrar_entrada(self.operador, self.lona.id, 5)

    def test_gerenciar_materiais_so_admin(self):                      # RF-09
        with self.assertRaises(ErroNegocio):
            self.s.materiais.salvar(self.atendente, "Novo", "X", "m²", 1, 2, 0)
        with self.assertRaises(ErroNegocio):
            self.s.materiais.salvar(self.admin, "lona 440G", "Lona", "m²", 1, 2, 0)   # nome duplicado


if __name__ == "__main__":
    unittest.main()
