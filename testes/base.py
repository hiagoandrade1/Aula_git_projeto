"""Bases compartilhadas pelos testes (banco em memória e dados mínimos)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from grafica import config, database, security      # noqa: E402
from grafica.models import Perfil                    # noqa: E402
from grafica.services import Servicos                # noqa: E402

security._ITERACOES = 1000      # acelera os testes (em produção usa 310 mil iterações)

CPF_OK = "529.982.247-25"
CNPJ_OK = "11.222.333/0001-81"


class BaseUsuarios(unittest.TestCase):
    """Banco em memória com administrador, atendente e operador."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        config.ARTES_DIR = Path(self.tmp.name) / "artes"
        self.conn = database.conectar(":memory:")
        database.inicializar(self.conn)
        self.s = Servicos(self.conn)
        self.admin = self.s.auth.login("admin@grafica.com", "admin123")
        self.s.usuarios.criar(self.admin, "Ana Atendente", "ana@g.com", Perfil.ATENDENTE, "senha123")
        self.s.usuarios.criar(self.admin, "Otavio Operador", "ot@g.com", Perfil.OPERADOR, "senha123")
        self.atendente = self.s.auth.login("ana@g.com", "senha123")
        self.operador = self.s.auth.login("ot@g.com", "senha123")

    def tearDown(self):
        self.tmp.cleanup()


class BaseCatalogo(BaseUsuarios):
    """Acrescenta dois materiais: Lona (m²) e Ilhós (un)."""

    def setUp(self):
        super().setUp()
        self.lona = self.s.materiais.salvar(self.admin, "Lona 440g", "Lona", "m²", 18, 45, 5, saldo_inicial=10)
        self.ilhos = self.s.materiais.salvar(self.admin, "Ilhós", "Acabamento", "un", 0.2, 0.8, 10, saldo_inicial=100)


class BaseOS(BaseCatalogo):
    """Acrescenta um cliente, um arquivo de arte e atalhos para criar O.S."""

    def setUp(self):
        super().setUp()
        self.cliente = self.s.clientes.salvar(self.atendente, "João da Silva", CPF_OK)
        self.arte = Path(self.tmp.name) / "arte.png"
        self.arte.write_bytes(b"\x89PNG fake")

    def nova_os(self, largura=2, altura=1, itens=None, **kw):
        itens = itens if itens is not None else [(self.lona.id, None)]
        return self.s.ordens.registrar(self.atendente, self.cliente.id, largura, altura, str(self.arte), itens, **kw)

    def os_em_producao(self, **kw):
        os_ = self.nova_os(**kw)
        self.s.ordens.aprovar_orcamento(self.atendente, os_.numero)
        self.s.ordens.atualizar_status(self.atendente, os_.numero, "Em Produção")
        return os_
