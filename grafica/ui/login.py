"""Tela de login (UC-03 / RF-08) e troca de senha."""
import tkinter as tk
from tkinter import ttk

from ..erros import ErroNegocio
from .comum import COR_ERRO, FONTE_TITULO, Dialogo, tratar_erros


class DialogTrocaSenha(Dialogo):
    def __init__(self, master, servicos, usuario, obrigatoria=False):
        super().__init__(master, "Definir nova senha" if obrigatoria else "Alterar senha")
        self.servicos, self.usuario, self.obrigatoria = servicos, usuario, obrigatoria
        c = self.corpo
        linha = 0
        if obrigatoria:
            ttk.Label(c, text="Este é o seu primeiro acesso (ou a senha foi redefinida).\n"
                              "Defina uma nova senha para continuar.").grid(row=0, column=0, columnspan=2, pady=(0, 10))
            linha = 1
        self.var_atual, self.var_nova, self.var_conf = tk.StringVar(), tk.StringVar(), tk.StringVar()
        campos = [] if obrigatoria else [("Senha atual:", self.var_atual)]
        campos += [("Nova senha:", self.var_nova), ("Confirmar nova senha:", self.var_conf)]
        primeiro = None
        for rotulo, var in campos:
            ttk.Label(c, text=rotulo).grid(row=linha, column=0, sticky="w", pady=3)
            e = ttk.Entry(c, textvariable=var, show="•", width=30)
            e.grid(row=linha, column=1, pady=3, padx=(8, 0))
            primeiro = primeiro or e
            linha += 1
        self.botoes(linha, "Salvar", self.salvar)
        primeiro.focus_set()
        self.bind("<Return>", lambda _e: self.salvar())

    @tratar_erros
    def salvar(self):
        if self.var_nova.get() != self.var_conf.get():
            raise ErroNegocio("A confirmação não confere com a nova senha.")
        atual = None if self.obrigatoria else self.var_atual.get()
        self.servicos.auth.trocar_senha(self.usuario, self.var_nova.get(), atual)
        self.resultado = True
        self.destroy()


class TelaLogin(ttk.Frame):
    def __init__(self, master, servicos, ao_autenticar):
        super().__init__(master)
        self.servicos, self.ao_autenticar = servicos, ao_autenticar
        centro = ttk.Frame(self, padding=30)
        centro.place(relx=0.5, rely=0.45, anchor="center")
        ttk.Label(centro, text="Sistema de Gestão de Impressões\ne Suprimentos", font=FONTE_TITULO,
                  justify="center").grid(row=0, column=0, columnspan=2, pady=(0, 20))
        self.var_email, self.var_senha = tk.StringVar(), tk.StringVar()
        ttk.Label(centro, text="E-mail:").grid(row=1, column=0, sticky="w", pady=4)
        self.entry_email = ttk.Entry(centro, textvariable=self.var_email, width=34)
        self.entry_email.grid(row=1, column=1, pady=4, padx=(8, 0))
        ttk.Label(centro, text="Senha:").grid(row=2, column=0, sticky="w", pady=4)
        entry_senha = ttk.Entry(centro, textvariable=self.var_senha, show="•", width=34)
        entry_senha.grid(row=2, column=1, pady=4, padx=(8, 0))
        self.lbl_erro = ttk.Label(centro, text="", foreground=COR_ERRO, wraplength=320, justify="center")
        self.lbl_erro.grid(row=3, column=0, columnspan=2, pady=(8, 0))
        ttk.Button(centro, text="Entrar", command=self.entrar).grid(row=4, column=0, columnspan=2, pady=(12, 0))
        for e in (self.entry_email, entry_senha):
            e.bind("<Return>", lambda _e: self.entrar())
        self.entry_email.focus_set()

    def entrar(self):
        self.lbl_erro.config(text="")
        try:
            usuario = self.servicos.auth.login(self.var_email.get(), self.var_senha.get())
        except ErroNegocio as e:
            self.lbl_erro.config(text=str(e))
            self.var_senha.set("")
            return
        if usuario.precisa_trocar_senha:                        # FA01 do UC-03
            if not DialogTrocaSenha(self, self.servicos, usuario, obrigatoria=True).exibir():
                self.lbl_erro.config(text="É necessário definir uma nova senha para continuar.")
                self.var_senha.set("")
                return
        self.ao_autenticar(usuario)
