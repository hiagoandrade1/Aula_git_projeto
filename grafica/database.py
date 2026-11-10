"""Banco de dados SQLite: conexão, criação do esquema e dados iniciais."""
import sqlite3

from . import config
from .models import Perfil
from .security import gerar_hash

ESQUEMA = """
CREATE TABLE IF NOT EXISTS funcionario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    perfil TEXT NOT NULL CHECK (perfil IN ('Atendente','Operador','Administrador')),
    ativo INTEGER NOT NULL DEFAULT 1,
    precisa_trocar_senha INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cliente (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    cpf_cnpj TEXT NOT NULL UNIQUE,              -- RN-02 (somente dígitos)
    telefone TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS material (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL COLLATE NOCASE UNIQUE,
    categoria TEXT NOT NULL DEFAULT '',
    unidade TEXT NOT NULL,
    custo_unitario REAL NOT NULL DEFAULT 0,
    preco_venda REAL NOT NULL,
    saldo_estoque REAL NOT NULL DEFAULT 0,
    limite_minimo REAL NOT NULL DEFAULT 0,
    ativo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS entrada_estoque (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER NOT NULL REFERENCES material(id),
    funcionario_id INTEGER NOT NULL REFERENCES funcionario(id),
    quantidade REAL NOT NULL,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ordem_servico (
    numero INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL REFERENCES cliente(id),
    funcionario_id INTEGER NOT NULL REFERENCES funcionario(id),
    data_criacao TEXT NOT NULL,
    data_entrega TEXT,
    data_conclusao TEXT,
    arquivo_arte TEXT NOT NULL DEFAULT '',
    largura REAL NOT NULL,
    altura REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'Orçamento'
        CHECK (status IN ('Orçamento','Em Produção','Concluído','Entregue','Cancelado')),
    valor_total REAL NOT NULL DEFAULT 0,
    orcamento_aprovado INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS item_os (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    os_numero INTEGER NOT NULL REFERENCES ordem_servico(numero) ON DELETE CASCADE,
    material_id INTEGER NOT NULL REFERENCES material(id),
    unidade TEXT NOT NULL,
    quantidade REAL NOT NULL,
    quantidade_faturada REAL NOT NULL,
    preco_unitario REAL NOT NULL,                -- RN-06 (preço congelado)
    subtotal REAL NOT NULL,
    quantidade_utilizada REAL,                   -- consumo real confirmado na conclusão
    UNIQUE (os_numero, material_id)
);

CREATE TABLE IF NOT EXISTS notificacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mensagem TEXT NOT NULL,
    data TEXT NOT NULL,
    lida INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_os_status ON ordem_servico(status);
CREATE INDEX IF NOT EXISTS idx_os_cliente ON ordem_servico(cliente_id);
"""

ADMIN_PADRAO = ("Administrador", "admin@grafica.com", "admin123")


def conectar(caminho=None) -> sqlite3.Connection:
    caminho = caminho or config.DB_PATH
    if str(caminho) != ":memory:":
        config.DADOS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(caminho))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def inicializar(conn: sqlite3.Connection) -> None:
    """Cria as tabelas e, se não houver nenhum funcionário, o administrador padrão."""
    with conn:
        conn.executescript(ESQUEMA)
    if conn.execute("SELECT COUNT(*) FROM funcionario").fetchone()[0] == 0:
        nome, email, senha = ADMIN_PADRAO
        with conn:
            conn.execute(
                "INSERT INTO funcionario (nome, email, senha_hash, perfil, ativo, precisa_trocar_senha) "
                "VALUES (?,?,?,?,1,1)",
                (nome, email, gerar_hash(senha), Perfil.ADMINISTRADOR),
            )


def popular_demo(conn: sqlite3.Connection) -> None:
    """Carrega usuários, materiais e clientes de exemplo (python main.py --demo)."""
    usuarios = [
        ("Ana Atendente", "atendente@grafica.com", "atendente123", Perfil.ATENDENTE),
        ("Otávio Operador", "operador@grafica.com", "operador123", Perfil.OPERADOR),
    ]
    materiais = [  # nome, categoria, unidade, custo, preço, saldo, mínimo
        ("Lona 440g", "Lona", "m²", 18.0, 45.0, 120.0, 20.0),
        ("Adesivo vinil", "Adesivo", "m²", 22.0, 60.0, 80.0, 15.0),
        ("Papel fotográfico", "Papel", "m²", 10.0, 28.0, 60.0, 10.0),
        ("Ilhós", "Acabamento", "un", 0.20, 0.80, 500.0, 100.0),
        ("Bainha reforçada", "Acabamento", "m", 1.0, 3.50, 200.0, 30.0),
    ]
    clientes = [
        ("João da Silva", "52998224725", "(16) 99999-0001", "joao@email.com"),
        ("Padaria Pão Quente Ltda", "11222333000181", "(16) 3333-0002", "contato@paoquente.com"),
    ]
    with conn:
        for nome, email, senha, perfil in usuarios:
            conn.execute(
                "INSERT OR IGNORE INTO funcionario (nome, email, senha_hash, perfil, ativo, precisa_trocar_senha) "
                "VALUES (?,?,?,?,1,0)", (nome, email, gerar_hash(senha), perfil))
        for m in materiais:
            conn.execute(
                "INSERT OR IGNORE INTO material (nome, categoria, unidade, custo_unitario, preco_venda, "
                "saldo_estoque, limite_minimo) VALUES (?,?,?,?,?,?,?)", m)
        for c in clientes:
            conn.execute("INSERT OR IGNORE INTO cliente (nome, cpf_cnpj, telefone, email) VALUES (?,?,?,?)", c)
