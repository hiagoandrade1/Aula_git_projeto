"""Tela de clientes (RF-01)."""
import tkinter as tk
from tkinter import ttk

from ..validacao import formatar_cpf_cnpj
from .comum import FONTE_SUBTITULO, Dialogo, Tabela, tratar_erros


class DialogCliente(Dialogo):
    def __init__(self, master, servicos, usuario, cliente=None):
        super().__init__(master, "Editar cliente" if cliente else "Novo cliente")
        self.servicos, self.usuario, self.cliente = servicos, usuario, cliente
        self.var_nome = tk.StringVar(value=cliente.nome if cliente else "")
        self.var_doc = tk.StringVar(value=formatar_cpf_cnpj(cliente.cpf_cnpj) if cliente else "")
        self.var_tel = tk.StringVar(value=cliente.telefone if cliente else "")
        self.var_email = tk.StringVar(value=cliente.email if cliente else "")
        c = self.corpo
        campos = [("Nome / Razão social:", self.var_nome), ("CPF ou CNPJ:", self.var_doc),
                  ("Telefone:", self.var_tel), ("E-mail:", self.var_email)]
        for i, (rotulo, var) in enumerate(campos):
            ttk.Label(c, text=rotulo).grid(row=i, column=0, sticky="w", pady=3)
            e = ttk.Entry(c, textvariable=var, width=40)
            e.grid(row=i, column=1, pady=3, padx=(8, 0))
            if i == 0:
                e.focus_set()
        self.botoes(len(campos), "Salvar", self.salvar)

    @tratar_erros
    def salvar(self):
        self.resultado = self.servicos.clientes.salvar(
            self.usuario, self.var_nome.get(), self.var_doc.get(), self.var_tel.get(), self.var_email.get(),
            cliente_id=self.cliente.id if self.cliente else None)
        self.destroy()


class TelaClientes(ttk.Frame):
    def __init__(self, master, servicos, usuario):
        super().__init__(master, padding=10)
        self.servicos, self.usuario = servicos, usuario
        ttk.Label(self, text="Clientes", font=FONTE_SUBTITULO).pack(anchor="w")
        barra = ttk.Frame(self)
        barra.pack(fill="x", pady=8)
        self.var_busca = tk.StringVar()
        busca = ttk.Entry(barra, textvariable=self.var_busca, width=30)
        busca.pack(side="left")
        busca.bind("<Return>", lambda _e: self.atualizar())
        ttk.Button(barra, text="Buscar", command=self.atualizar).pack(side="left", padx=4)
        ttk.Button(barra, text="Limpar", command=self.limpar_busca).pack(side="left")
        ttk.Button(barra, text="Editar", command=self.editar).pack(side="right")
        ttk.Button(barra, text="Novo cliente", command=self.novo).pack(side="right", padx=4)
        self.tabela = Tabela(self, [("nome", "Nome / Razão social", 280), ("tipo", "Tipo", 110),
                                    ("doc", "CPF / CNPJ", 150), ("tel", "Telefone", 130), ("email", "E-mail", 230)])
        self.tabela.pack(fill="both", expand=True)
        self.tabela.ao_duplo_clique(self.editar)
        self.atualizar()

    def limpar_busca(self):
        self.var_busca.set("")
        self.atualizar()

    @tratar_erros
    def atualizar(self):
        self.tabela.limpar()
        for c in self.servicos.clientes.listar(self.var_busca.get()):
            self.tabela.inserir(c.id, (c.nome, c.tipo_pessoa, formatar_cpf_cnpj(c.cpf_cnpj), c.telefone, c.email))

    def novo(self):
        if DialogCliente(self, self.servicos, self.usuario).exibir():
            self.atualizar()

    @tratar_erros
    def editar(self):
        cliente = self.servicos.clientes.obter(int(self.tabela.exigir_selecao("Selecione um cliente para editar.")))
        if DialogCliente(self, self.servicos, self.usuario, cliente).exibir():
            self.atualizar()
