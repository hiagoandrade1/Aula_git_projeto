"""Testes do fluxo de status, fila e conclusão (RF-04 a RF-07, RN-03 a RN-05, RN-07)."""
import unittest

from base import BaseOS  # noqa: E402
from grafica.erros import ErroNegocio  # noqa: E402
from grafica.models import Status  # noqa: E402


class TestFluxoStatus(BaseOS):
    def test_producao_exige_aprovacao(self):                          # RN-03
        os_ = self.nova_os()
        with self.assertRaises(ErroNegocio) as ctx:
            self.s.ordens.atualizar_status(self.atendente, os_.numero, Status.EM_PRODUCAO)
        self.assertIn("RN-03", str(ctx.exception))
        self.s.ordens.aprovar_orcamento(self.atendente, os_.numero)
        self.s.ordens.atualizar_status(self.atendente, os_.numero, Status.EM_PRODUCAO)
        self.assertEqual(self.s.ordens.obter(os_.numero).status, Status.EM_PRODUCAO)

    def test_aprovar_duas_vezes(self):
        os_ = self.nova_os()
        self.s.ordens.aprovar_orcamento(self.atendente, os_.numero)
        with self.assertRaises(ErroNegocio):
            self.s.ordens.aprovar_orcamento(self.atendente, os_.numero)

    def test_atendente_nao_conclui(self):                             # RN-04
        os_ = self.os_em_producao()
        with self.assertRaises(ErroNegocio) as ctx:
            self.s.ordens.confirmar_conclusao(self.atendente, os_.numero)
        self.assertIn("permissão", str(ctx.exception))
        # e não há atalho pela atualização genérica de status
        with self.assertRaises(ErroNegocio):
            self.s.ordens.atualizar_status(self.atendente, os_.numero, Status.CONCLUIDO)
        self.assertEqual(self.s.ordens.obter(os_.numero).status, Status.EM_PRODUCAO)

    def test_transicoes_invalidas(self):
        os_ = self.nova_os()
        with self.assertRaises(ErroNegocio):
            self.s.ordens.atualizar_status(self.atendente, os_.numero, Status.ENTREGUE)
        self.s.ordens.atualizar_status(self.atendente, os_.numero, Status.CANCELADO)
        with self.assertRaises(ErroNegocio):
            self.s.ordens.atualizar_status(self.atendente, os_.numero, Status.EM_PRODUCAO)

    def test_fluxo_completo(self):
        os_ = self.os_em_producao()
        self.s.ordens.confirmar_conclusao(self.operador, os_.numero)
        self.s.ordens.atualizar_status(self.atendente, os_.numero, Status.ENTREGUE)
        self.assertEqual(self.s.ordens.obter(os_.numero).status, Status.ENTREGUE)

    def test_operador_nao_entrega_nem_cancela(self):
        os_ = self.nova_os()
        with self.assertRaises(ErroNegocio):
            self.s.ordens.atualizar_status(self.operador, os_.numero, Status.CANCELADO)


class TestFilaEEstoque(BaseOS):
    def test_fila_so_em_producao(self):                               # RF-05
        a = self.nova_os()
        b = self.os_em_producao()
        c = self.os_em_producao()
        self.assertEqual([o.numero for o in self.s.ordens.fila_impressao()], [b.numero, c.numero])
        self.assertNotIn(a.numero, [o.numero for o in self.s.ordens.fila_impressao()])

    def test_baixa_somente_na_conclusao(self):                        # RN-05
        os_ = self.os_em_producao(largura=2, altura=1)
        self.assertAlmostEqual(self.s.materiais.obter(self.lona.id).saldo_estoque, 10)
        self.s.ordens.confirmar_conclusao(self.operador, os_.numero)
        self.assertAlmostEqual(self.s.materiais.obter(self.lona.id).saldo_estoque, 8)
        item = self.s.ordens.obter(os_.numero).itens[0]
        self.assertAlmostEqual(item.quantidade_utilizada, 2)

    def test_consumo_real_com_perda(self):                            # FA01 do UC-02
        os_ = self.os_em_producao(largura=2, altura=1)
        item = self.s.ordens.obter(os_.numero).itens[0]
        self.s.ordens.confirmar_conclusao(self.operador, os_.numero, {item.id: 3.5})
        self.assertAlmostEqual(self.s.materiais.obter(self.lona.id).saldo_estoque, 6.5)

    def test_alerta_estoque_baixo(self):                              # RF-07
        self.assertEqual(self.s.materiais.listar_estoque_baixo(), [])
        os_ = self.os_em_producao(largura=2.5, altura=2)              # 5 m² -> saldo 5 == limite 5
        res = self.s.ordens.confirmar_conclusao(self.operador, os_.numero)
        self.assertEqual([m.nome for m in res.alertas], ["Lona 440g"])
        self.assertEqual([m.nome for m in self.s.materiais.listar_estoque_baixo()], ["Lona 440g"])

    def test_estoque_insuficiente_baixa_parcial(self):                # EX01 do UC-02
        os_ = self.os_em_producao(largura=5, altura=3)                # 15 m² > saldo 10
        res = self.s.ordens.confirmar_conclusao(self.operador, os_.numero)
        self.assertEqual(len(res.avisos), 1)
        self.assertAlmostEqual(self.s.materiais.obter(self.lona.id).saldo_estoque, 0)
        self.assertEqual(self.s.ordens.obter(os_.numero).status, Status.CONCLUIDO)
        self.assertEqual(len(self.s.materiais.listar_notificacoes()), 1)  # Administrador é notificado
        self.s.materiais.marcar_notificacoes_lidas(self.admin)
        self.assertEqual(self.s.materiais.listar_notificacoes(), [])

    def test_conclusao_atomica(self):
        os_ = self.os_em_producao()
        item = self.s.ordens.obter(os_.numero).itens[0]
        with self.assertRaises(ErroNegocio):
            self.s.ordens.confirmar_conclusao(self.operador, os_.numero, {item.id: -1})
        self.assertEqual(self.s.ordens.obter(os_.numero).status, Status.EM_PRODUCAO)
        self.assertAlmostEqual(self.s.materiais.obter(self.lona.id).saldo_estoque, 10)

    def test_nao_conclui_os_fora_de_producao(self):
        os_ = self.nova_os()
        with self.assertRaises(ErroNegocio):
            self.s.ordens.confirmar_conclusao(self.operador, os_.numero)


if __name__ == "__main__":
    unittest.main()
