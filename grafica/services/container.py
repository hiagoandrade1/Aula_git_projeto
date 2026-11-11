"""Contêiner que agrupa os serviços para injeção na interface."""
from .autenticacao import AuthService
from .clientes import ClienteService
from .materiais import MaterialService
from .ordens import OrdemServicoService
from .usuarios import UsuarioService


class Servicos:
    """Agrupa os serviços para facilitar a injeção na interface."""

    def __init__(self, conn):
        self.conn = conn
        self.auth = AuthService(conn)
        self.usuarios = UsuarioService(conn)
        self.clientes = ClienteService(conn)
        self.materiais = MaterialService(conn)
        self.ordens = OrdemServicoService(conn)
