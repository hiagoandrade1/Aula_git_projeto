"""Testes de orçamento e registro de O.S. (RF-02, RF-03, RN-01, RN-06)."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from base import BaseOS  # noqa: E402
from grafica import config  # noqa: E402
from grafica.erros import ErroNegocio  # noqa: E402
from grafica.models import Status  # noqa: E402


class TestOrcamento(BaseOS):
    def test_calculo_por_area(self):                                  # RF-03
        os_ = self.nova_os(2, 1.5, [(self.lona.id, None), (self.ilhos.id, 8)])
        self.assertAlmostEqual(os_.valor_total, 3 * 45 + 8 * 0.8)
        self.assertEqual(os_.status, Status.ORCAMENTO)

    def test_area_minima(self):                                       # RN-01
        os_ = self.nova_os(0.2, 0.2)                                  # 0,04 m² -> cobra 0,25 m²
        self.assertAlmostEqual(os_.area, 0.04)
        self.assertAlmostEqual(os_.valor_total, 0.25 * 45)
        self.assertAlmostEqual(os_.itens[0].quantidade, 0.04)         # consumo físico continua real

    def test_area_exatamente_no_minimo(self):
        self.assertAlmostEqual(self.nova_os(0.5, 0.5).valor_total, 0.25 * 45)

    def test_dimensoes_invalidas(self):                               # EX02 do UC-01
        for l, a in [(0, 1), (1, 0), (-1, 2)]:
            with self.assertRaises(ErroNegocio):
                self.s.ordens.simular_orcamento(l, a, [(self.lona.id, None)])

    def test_preco_congelado(self):                                   # RN-06
        os_ = self.nova_os(1, 1)
        self.s.materiais.salvar(self.admin, "Lona 440g", "Lona", "m²", 18, 99, 5, material_id=self.lona.id)
        depois = self.s.ordens.obter(os_.numero)
        self.assertAlmostEqual(depois.valor_total, 45.0)
        self.assertAlmostEqual(depois.itens[0].preco_unitario, 45.0)
        self.assertAlmostEqual(self.nova_os(1, 1).valor_total, 99.0)  # novas O.S. usam o preço novo

    def test_unidade_exige_quantidade_inteira(self):
        with self.assertRaises(ErroNegocio):
            self.nova_os(1, 1, [(self.ilhos.id, 2.5)])
        with self.assertRaises(ErroNegocio):
            self.nova_os(1, 1, [(self.ilhos.id, None)])

    def test_sem_material_ou_duplicado(self):
        with self.assertRaises(ErroNegocio):
            self.nova_os(1, 1, [])
        with self.assertRaises(ErroNegocio):
            self.nova_os(1, 1, [(self.lona.id, None), (self.lona.id, None)])

    def test_material_desativado(self):
        self.s.materiais.definir_ativo(self.admin, self.lona.id, False)
        with self.assertRaises(ErroNegocio):
            self.nova_os()


class TestRegistroOS(BaseOS):
    def test_arte_invalida(self):                                     # EX01 do UC-01
        ruim = Path(self.tmp.name) / "arte.exe"
        ruim.write_bytes(b"x")
        for caminho in ("", str(ruim), str(Path(self.tmp.name) / "naoexiste.png")):
            with self.assertRaises(ErroNegocio):
                self.s.ordens.registrar(self.atendente, self.cliente.id, 1, 1, caminho, [(self.lona.id, None)])

    def test_arte_copiada_e_numero_unico(self):
        a, b = self.nova_os(), self.nova_os()
        self.assertNotEqual(a.numero, b.numero)
        self.assertTrue(Path(a.arquivo_arte).is_file())
        self.assertTrue(Path(a.arquivo_arte).parent == config.ARTES_DIR)

    def test_data_entrega(self):
        amanha = (date.today() + timedelta(days=1)).isoformat()
        self.assertEqual(self.nova_os(data_entrega=amanha).data_entrega, amanha)
        with self.assertRaises(ErroNegocio):
            self.nova_os(data_entrega=(date.today() - timedelta(days=1)).isoformat())
        with self.assertRaises(ErroNegocio):
            self.nova_os(data_entrega="31/12/2030")

    def test_operador_nao_registra(self):
        with self.assertRaises(ErroNegocio):
            self.s.ordens.registrar(self.operador, self.cliente.id, 1, 1, str(self.arte), [(self.lona.id, None)])


if __name__ == "__main__":
    unittest.main()
