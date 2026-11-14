"""Testes de autenticação e gerenciamento de usuários (RF-08, RF-11, RNF-03)."""
import unittest

from base import BaseUsuarios  # noqa: E402
from grafica.erros import ErroNegocio  # noqa: E402
from grafica.models import Perfil  # noqa: E402


class TestAutenticacaoEUsuarios(BaseUsuarios):
    def test_credenciais_invalidas_sem_revelar_campo(self):           # EX01 do UC-03
        mensagens = set()
        for email, senha in [("ana@g.com", "errada"), ("naoexiste@g.com", "senha123"), ("", "")]:
            with self.assertRaises(ErroNegocio) as ctx:
                self.s.auth.login(email, senha)
            mensagens.add(str(ctx.exception))
        self.assertEqual(mensagens, {"E-mail ou senha inválidos"})

    def test_conta_desativada(self):                                  # EX02 do UC-03
        self.s.usuarios.definir_ativo(self.admin, self.atendente.id, False)
        with self.assertRaises(ErroNegocio) as ctx:
            self.s.auth.login("ana@g.com", "senha123")
        self.assertIn("Conta desativada", str(ctx.exception))

    def test_senha_nao_fica_em_texto_puro(self):                      # RNF-03
        h = self.conn.execute("SELECT senha_hash FROM funcionario WHERE email='ana@g.com'").fetchone()[0]
        self.assertNotIn("senha123", h)
        self.assertTrue(h.startswith(("$2", "pbkdf2_sha256$")))

    def test_primeiro_acesso_troca_senha(self):                       # FA01 do UC-03
        self.assertTrue(self.admin.precisa_trocar_senha)
        with self.assertRaises(ErroNegocio):
            self.s.auth.trocar_senha(self.admin, "123")
        with self.assertRaises(ErroNegocio):
            self.s.auth.trocar_senha(self.admin, "admin123")          # igual à atual
        self.s.auth.trocar_senha(self.admin, "novasenha1")
        self.assertFalse(self.s.auth.login("admin@grafica.com", "novasenha1").precisa_trocar_senha)
        with self.assertRaises(ErroNegocio):
            self.s.auth.login("admin@grafica.com", "admin123")

    def test_perfis_e_permissoes(self):
        self.assertEqual(self.atendente.perfil_acesso, Perfil.ATENDENTE)
        self.assertTrue(self.operador.pode_acessar("fila"))
        self.assertFalse(self.operador.pode_acessar("usuarios"))
        self.assertFalse(self.atendente.pode_acessar("materiais"))
        self.assertTrue(self.admin.pode_acessar("usuarios"))
        self.assertEqual(self.operador.ABA_INICIAL, "fila")

    def test_gerenciar_usuarios(self):                                # RF-11
        with self.assertRaises(ErroNegocio):
            self.s.usuarios.criar(self.atendente, "Fulano de Tal", "f@g.com", Perfil.OPERADOR, "senha123")
        with self.assertRaises(ErroNegocio):
            self.s.usuarios.criar(self.admin, "Outra Ana", "ANA@g.com", Perfil.OPERADOR, "senha123")  # e-mail repetido
        self.s.usuarios.alterar(self.admin, self.operador.id, "Otavio Silva", Perfil.ATENDENTE)
        self.assertEqual(self.s.auth.login("ot@g.com", "senha123").perfil_acesso, Perfil.ATENDENTE)
        self.s.usuarios.redefinir_senha(self.admin, self.operador.id, "temporaria1")
        self.assertTrue(self.s.auth.login("ot@g.com", "temporaria1").precisa_trocar_senha)

    def test_nao_remove_ultimo_admin(self):
        with self.assertRaises(ErroNegocio):
            self.s.usuarios.definir_ativo(self.admin, self.admin.id, False)
        with self.assertRaises(ErroNegocio):
            self.s.usuarios.alterar(self.admin, self.admin.id, "Administrador", Perfil.OPERADOR)


if __name__ == "__main__":
    unittest.main()

