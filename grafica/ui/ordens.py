"""Tela de ordens de serviço (RF-02, RF-03, RF-04) - UC-01."""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .. import config
from ..erros import ErroNegocio
from ..models import Perfil, Status
from ..validacao import formatar_cpf_cnpj
from .clientes import DialogCliente
from .comum import (FONTE_SUBTITULO, Dialogo, Tabela, abrir_arquivo, data_br, data_hora_br, moeda, numero,
                    parse_data_br, parse_numero, qtd_txt, tratar_erros)

COLUNAS_ITENS = [("material", "Material", 200), ("un", "Un.", 50, "center"), ("qtd", "Qtde", 80, "e"),
                 ("fat", "Qtde faturada", 100, "e"), ("preco", "Preço unit.", 90, "e"), ("sub", "Subtotal", 100, "e")]


def _linha_item(it):
    return (it.material_nome, it.unidade, qtd_txt(it.quantidade), qtd_txt(it.quantidade_faturada),
            moeda(it.preco_unitario), moeda(it.subtotal))


class DialogNovaOS(Dialogo):
    def __init__(self, master, servicos, usuario):
        super().__init__(master, "Nova Ordem de Serviço")
        self.servicos, self.usuario = servicos, usuario
        self.itens = []                                   # lista de (material_id, quantidade|None)
        self.materiais = servicos.materiais.listar(apenas_ativos=True)
        self.clientes = []
        c = self.corpo

        # Cliente (passo 3 e FA01)
        ttk.Label(c, text="Cliente:").grid(row=0, column=0, sticky="w", pady=3)
        self.cmb_cliente = ttk.Combobox(c, state="readonly", width=52)
        self.cmb_cliente.grid(row=0, column=1, columnspan=2, sticky="w", padx=(8, 0))
        ttk.Button(c, text="Cadastrar cliente", command=self.cadastrar_cliente).grid(row=0, column=3, padx=(6, 0))
        self._carregar_clientes()

        # Dimensões (passo 4)
        self.var_larg, self.var_alt = tk.StringVar(), tk.StringVar()
        ttk.Label(c, text="Largura (m):").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Entry(c, textvariable=self.var_larg, width=10).grid(row=1, column=1, sticky="w", padx=(8, 0))
        ttk.Label(c, text="Altura (m):").grid(row=1, column=1, sticky="w", padx=(110, 0))
        ttk.Entry(c, textvariable=self.var_alt, width=10).grid(row=1, column=1, sticky="w", padx=(185, 0))

        # Arte
        self.var_arte = tk.StringVar()
        ttk.Label(c, text="Arquivo de arte:").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Entry(c, textvariable=self.var_arte, state="readonly", width=55).grid(
            row=2, column=1, columnspan=2, sticky="w", padx=(8, 0))
        ttk.Button(c, text="Procurar...", command=self.procurar_arte).grid(row=2, column=3, padx=(6, 0))

        # Entrega
        self.var_entrega = tk.StringVar()
        ttk.Label(c, text="Entrega (DD/MM/AAAA):").grid(row=3, column=0, sticky="w", pady=3)
        ttk.Entry(c, textvariable=self.var_entrega, width=14).grid(row=3, column=1, sticky="w", padx=(8, 0))

        # Materiais (passo 5)
        ttk.Separator(c).grid(row=4, column=0, columnspan=4, sticky="ew", pady=8)
        ttk.Label(c, text="Material / acabamento:").grid(row=5, column=0, sticky="w")
        self.cmb_material = ttk.Combobox(c, state="readonly", width=40, values=[
            f"{m.nome} ({m.unidade}) - {moeda(m.preco_venda)}" for m in self.materiais])
        self.cmb_material.grid(row=5, column=1, sticky="w", padx=(8, 0))
        self.cmb_material.bind("<<ComboboxSelected>>", self._ao_escolher_material)
        self.var_qtd = tk.StringVar()
        ttk.Label(c, text="Qtde:").grid(row=5, column=2, sticky="e")
        self.entry_qtd = ttk.Entry(c, textvariable=self.var_qtd, width=10, state="disabled")
        self.entry_qtd.grid(row=5, column=3, sticky="w", padx=(6, 0))
        quadro = ttk.Frame(c)
        quadro.grid(row=6, column=1, sticky="w", padx=(8, 0), pady=4)
        ttk.Button(quadro, text="Adicionar", command=self.adicionar_item).pack(side="left")
        ttk.Button(quadro, text="Remover selecionado", command=self.remover_item).pack(side="left", padx=6)
        self.tab_itens = Tabela(c, COLUNAS_ITENS, altura=6)
        self.tab_itens.grid(row=7, column=0, columnspan=4, sticky="ew", pady=4)

        self.lbl_total = ttk.Label(c, text="", font=FONTE_SUBTITULO)
        self.lbl_total.grid(row=8, column=0, columnspan=4, sticky="w", pady=(6, 0))
        self.botoes(9, "Confirmar registro", self.confirmar, coluna_span=4)
        self.var_larg.trace_add("write", self._recalcular)
        self.var_alt.trace_add("write", self._recalcular)
        self._recalcular()

    # --- clientes ---------------------------------------------------------
    def _carregar_clientes(self, selecionar_id=None):
        self.clientes = self.servicos.clientes.listar()
        self.cmb_cliente["values"] = [f"{cl.nome} - {formatar_cpf_cnpj(cl.cpf_cnpj)}" for cl in self.clientes]
        if selecionar_id is not None:
            for i, cl in enumerate(self.clientes):
                if cl.id == selecionar_id:
                    self.cmb_cliente.current(i)

    def cadastrar_cliente(self):                                  # FA01
        novo = DialogCliente(self, self.servicos, self.usuario).exibir()
        if novo:
            self._carregar_clientes(selecionar_id=novo.id)

    # --- arte -------------------------------------------------------------
    def procurar_arte(self):
        tipos = " ".join(f"*{e}" for e in sorted(config.EXTENSOES_ARTE))
        caminho = filedialog.askopenfilename(parent=self, title="Selecione o arquivo de arte",
                                             filetypes=[("Arquivos de arte", tipos), ("Todos os arquivos", "*.*")])
        if caminho:
            self.var_arte.set(caminho)

    # --- itens ------------------------------------------------------------
    def _material_escolhido(self):
        idx = self.cmb_material.current()
        return self.materiais[idx] if idx >= 0 else None

    def _ao_escolher_material(self, _evento=None):
        mat = self._material_escolhido()
        if mat is None:
            return
        if mat.unidade == config.UNIDADE_AREA:
            self.var_qtd.set("")
            self.entry_qtd.config(state="disabled")
        else:
            self.entry_qtd.config(state="normal")
            self.var_qtd.set("1")

    @tratar_erros
    def adicionar_item(self):
        mat = self._material_escolhido()
        if mat is None:
            raise ErroNegocio("Selecione um material.")
        if any(mid == mat.id for mid, _ in self.itens):
            raise ErroNegocio("Este material já foi adicionado.")
        qtd = None
        if mat.unidade != config.UNIDADE_AREA:
            qtd = parse_numero(self.var_qtd.get(), f"quantidade de {mat.nome}")
        self.itens.append((mat.id, qtd))
        self._recalcular()

    @tratar_erros
    def remover_item(self):
        iid = self.tab_itens.exigir_selecao("Selecione um item para remover.")
        del self.itens[int(iid)]
        self._recalcular()

    # --- orçamento ao vivo (RF-03) ------------------------------------------
    def _recalcular(self, *_args):
        self.tab_itens.limpar()
        try:
            larg = parse_numero(self.var_larg.get(), "largura")
            alt = parse_numero(self.var_alt.get(), "altura")
            os_ = self.servicos.ordens.simular_orcamento(larg, alt, self.itens)
        except ErroNegocio as e:
            nomes = {m.id: m for m in self.materiais}
            for i, (mid, qtd) in enumerate(self.itens):
                m = nomes[mid]
                self.tab_itens.inserir(i, (m.nome, m.unidade, qtd_txt(qtd) if qtd else "auto", "-", moeda(m.preco_venda), "-"))
            self.lbl_total.config(text=f"Total: -   ({e})")
            return
        for i, it in enumerate(os_.itens):
            self.tab_itens.inserir(i, _linha_item(it))
        aviso = "  [área mínima de 0,25 m² aplicada]" if os_.area < config.AREA_MINIMA_M2 else ""
        self.lbl_total.config(text=f"Área: {numero(os_.area)} m² (faturada: {numero(os_.area_faturada)} m²){aviso}"
                                   f"     Total: {moeda(os_.valor_total)}")

    # --- confirmação (passo 8) ----------------------------------------------
    @tratar_erros
    def confirmar(self):
        idx = self.cmb_cliente.current()
        if idx < 0:
            raise ErroNegocio("Selecione o cliente.")
        larg = parse_numero(self.var_larg.get(), "largura")
        alt = parse_numero(self.var_alt.get(), "altura")
        entrega = parse_data_br(self.var_entrega.get())
        os_ = self.servicos.ordens.registrar(self.usuario, self.clientes[idx].id, larg, alt,
                                             self.var_arte.get(), self.itens, entrega)
        messagebox.showinfo("O.S. registrada", f"O.S. {os_.numero:05d} registrada com status 'Orçamento'.\n"
                                               f"Valor total: {moeda(os_.valor_total)}", parent=self)
        self.resultado = os_
        self.destroy()


class DialogDetalhesOS(Dialogo):
    def __init__(self, master, servicos, numero_os):
        os_ = servicos.ordens.obter(numero_os)
        super().__init__(master, f"O.S. {os_.numero:05d}")
        self.os = os_
        c = self.corpo
        info = [("Cliente", os_.cliente_nome), ("Registrada por", os_.funcionario_nome),
                ("Criada em", data_hora_br(os_.data_criacao)), ("Entrega prevista", data_br(os_.data_entrega)),
                ("Dimensões", f"{numero(os_.largura)} m × {numero(os_.altura)} m  =  {numero(os_.area)} m²"
                              f"  (faturada: {numero(os_.area_faturada)} m²)"),
                ("Status", os_.status), ("Orçamento aprovado", "Sim" if os_.orcamento_aprovado else "Não"),
                ("Concluída em", data_hora_br(os_.data_conclusao)), ("Arquivo de arte", os_.arquivo_arte or "-")]
        for i, (rotulo, valor) in enumerate(info):
            ttk.Label(c, text=f"{rotulo}:", font=("Helvetica", 10, "bold")).grid(row=i, column=0, sticky="nw", pady=1)
            ttk.Label(c, text=valor, wraplength=520, justify="left").grid(row=i, column=1, sticky="w", padx=(10, 0))
        tab = Tabela(c, COLUNAS_ITENS + [("real", "Consumo real", 100, "e")], altura=6)
        tab.grid(row=len(info), column=0, columnspan=2, pady=10, sticky="ew")
        for i, it in enumerate(os_.itens):
            real = qtd_txt(it.quantidade_utilizada) if it.quantidade_utilizada is not None else "-"
            tab.inserir(i, _linha_item(it) + (real,))
        ttk.Label(c, text=f"Valor total: {moeda(os_.valor_total)}", font=FONTE_SUBTITULO).grid(
            row=len(info) + 1, column=0, columnspan=2, sticky="e")
        quadro = ttk.Frame(c)
        quadro.grid(row=len(info) + 2, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(quadro, text="Fechar", command=self.cancelar).pack(side="right")
        ttk.Button(quadro, text="Abrir arte", command=self.abrir_arte).pack(side="right", padx=6)

    @tratar_erros
    def abrir_arte(self):
        abrir_arquivo(self.os.arquivo_arte)


class TelaOrdens(ttk.Frame):
    def __init__(self, master, servicos, usuario):
        super().__init__(master, padding=10)
        self.servicos, self.usuario = servicos, usuario
        pode_registrar = usuario.perfil_acesso in (Perfil.ATENDENTE, Perfil.ADMINISTRADOR)
        ttk.Label(self, text="Ordens de Serviço", font=FONTE_SUBTITULO).pack(anchor="w")

        filtros = ttk.Frame(self)
        filtros.pack(fill="x", pady=(8, 2))
        ttk.Label(filtros, text="Status:").pack(side="left")
        self.var_status = tk.StringVar(value="Todos")
        cmb = ttk.Combobox(filtros, state="readonly", width=14, textvariable=self.var_status,
                           values=["Todos"] + list(Status.TODOS))
        cmb.pack(side="left", padx=(4, 10))
        cmb.bind("<<ComboboxSelected>>", lambda _e: self.atualizar())
        ttk.Label(filtros, text="Cliente / nº:").pack(side="left")
        self.var_busca = tk.StringVar()
        busca = ttk.Entry(filtros, textvariable=self.var_busca, width=24)
        busca.pack(side="left", padx=4)
        busca.bind("<Return>", lambda _e: self.atualizar())
        ttk.Button(filtros, text="Buscar", command=self.atualizar).pack(side="left")
        if pode_registrar:
            ttk.Button(filtros, text="Nova O.S.", command=self.nova_os).pack(side="right")

        acoes = ttk.Frame(self)
        acoes.pack(fill="x", pady=(2, 8))
        ttk.Button(acoes, text="Detalhes", command=self.detalhes).pack(side="left")
        if pode_registrar:
            ttk.Button(acoes, text="Aprovar orçamento", command=self.aprovar).pack(side="left", padx=4)
        ttk.Button(acoes, text="Iniciar produção", command=lambda: self.mudar(Status.EM_PRODUCAO)).pack(side="left")
        if pode_registrar:
            ttk.Button(acoes, text="Marcar como entregue",
                       command=lambda: self.mudar(Status.ENTREGUE)).pack(side="left", padx=4)
            ttk.Button(acoes, text="Cancelar O.S.", command=lambda: self.mudar(Status.CANCELADO)).pack(side="left")

        self.tabela = Tabela(self, [("num", "Nº", 70, "center"), ("cliente", "Cliente", 230), ("criada", "Criada em", 90),
                                    ("entrega", "Entrega", 90), ("area", "Área (m²)", 80, "e"),
                                    ("valor", "Valor", 100, "e"), ("status", "Status", 100),
                                    ("aprov", "Aprovada", 70, "center")])
        self.tabela.pack(fill="both", expand=True)
        self.tabela.ao_duplo_clique(self.detalhes)
        self.atualizar()

    @tratar_erros
    def atualizar(self):
        status = None if self.var_status.get() == "Todos" else self.var_status.get()
        self.tabela.limpar()
        marcas = {Status.EM_PRODUCAO: "producao", Status.CONCLUIDO: "concluido", Status.CANCELADO: "cancelado"}
        for o in self.servicos.ordens.listar(status, self.var_busca.get()):
            self.tabela.inserir(o.numero, (f"{o.numero:05d}", o.cliente_nome, data_br(o.data_criacao),
                                           data_br(o.data_entrega), numero(o.area), moeda(o.valor_total), o.status,
                                           "Sim" if o.orcamento_aprovado else "Não"),
                                tags=(marcas.get(o.status, ""),))

    def _selecionada(self) -> int:
        return int(self.tabela.exigir_selecao("Selecione uma O.S. na lista."))

    def nova_os(self):
        if DialogNovaOS(self, self.servicos, self.usuario).exibir():
            self.atualizar()

    @tratar_erros
    def detalhes(self):
        DialogDetalhesOS(self, self.servicos, self._selecionada()).exibir()

    @tratar_erros
    def aprovar(self):
        self.servicos.ordens.aprovar_orcamento(self.usuario, self._selecionada())
        self.atualizar()

    @tratar_erros
    def mudar(self, novo_status):
        numero_os = self._selecionada()
        if novo_status == Status.CANCELADO and not messagebox.askyesno(
                "Cancelar O.S.", f"Confirma o cancelamento da O.S. {numero_os:05d}?", parent=self):
            return
        self.servicos.ordens.atualizar_status(self.usuario, numero_os, novo_status)
        self.atualizar()
