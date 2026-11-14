"""Componentes e utilitários compartilhados pelas telas."""
import functools
import logging
import os
import subprocess
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

from ..erros import ErroNegocio

FONTE_TITULO = ("Helvetica", 16, "bold")
FONTE_SUBTITULO = ("Helvetica", 11, "bold")
COR_ERRO = "#b00020"
COR_ALERTA_FUNDO = "#fff3cd"
COR_ALERTA_TEXTO = "#7a5b00"


# ------------------------------------------------------------ formatação
def _trocar_separadores(texto: str) -> str:
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def moeda(valor) -> str:
    return "R$ " + _trocar_separadores(f"{float(valor):,.2f}")


def numero(valor, casas=2) -> str:
    return _trocar_separadores(f"{float(valor):,.{casas}f}")


def qtd_txt(valor) -> str:
    """Quantidade sem zeros desnecessários (até 4 casas), com vírgula decimal."""
    return f"{float(valor):.4f}".rstrip("0").rstrip(".").replace(".", ",")


def data_br(iso) -> str:
    if not iso:
        return "-"
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y")
    except ValueError:
        return str(iso)


def data_hora_br(iso) -> str:
    if not iso:
        return "-"
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return str(iso)


def parse_numero(texto, campo="valor") -> float:
    """Aceita '1,5' e '1.5' (e '1.234,56')."""
    t = (texto or "").strip()
    if not t:
        raise ErroNegocio(f"Informe {campo}.")
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        raise ErroNegocio(f"Valor inválido para {campo}: '{texto}'.") from None


def parse_data_br(texto):
    """'DD/MM/AAAA' -> 'AAAA-MM-DD'. Vazio -> None."""
    t = (texto or "").strip()
    if not t:
        return None
    try:
        return datetime.strptime(t, "%d/%m/%Y").date().isoformat()
    except ValueError:
        raise ErroNegocio("Data inválida. Use o formato DD/MM/AAAA.") from None


def abrir_arquivo(caminho) -> None:
    if not caminho or not Path(caminho).exists():
        raise ErroNegocio("Arquivo de arte não encontrado.")
    if sys.platform.startswith("win"):
        os.startfile(caminho)  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.Popen(["open", caminho])
    else:
        subprocess.Popen(["xdg-open", caminho])


# ------------------------------------------------------ tratamento de erros
def tratar_erros(func):
    """Decorator para handlers de botões: mostra ErroNegocio como aviso e erros inesperados em diálogo."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        pai = args[0].winfo_toplevel() if args and hasattr(args[0], "winfo_toplevel") else None
        try:
            return func(*args, **kwargs)
        except ErroNegocio as e:
            messagebox.showwarning("Atenção", str(e), parent=pai)
        except Exception as e:  # noqa: BLE001
            logging.exception("Erro inesperado")
            messagebox.showerror("Erro inesperado", f"Ocorreu um erro: {e}", parent=pai)
    return wrapper


# ----------------------------------------------------------------- widgets
class Tabela(ttk.Frame):
    """Treeview com barras de rolagem. colunas = [(id, titulo, largura, alinhamento)]."""

    def __init__(self, master, colunas, altura=14):
        super().__init__(master)
        ids = [c[0] for c in colunas]
        self.tree = ttk.Treeview(self, columns=ids, show="headings", height=altura, selectmode="browse")
        for c in colunas:
            alinhamento = c[3] if len(c) > 3 else "w"
            self.tree.heading(c[0], text=c[1])
            self.tree.column(c[0], width=c[2], anchor=alinhamento, stretch=True)
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.tree.tag_configure("alerta", background="#ffd9d9")
        self.tree.tag_configure("inativo", foreground="#888888")
        self.tree.tag_configure("cancelado", foreground="#888888")
        self.tree.tag_configure("concluido", background="#e3f6e3")
        self.tree.tag_configure("producao", background="#e3eefc")

    def limpar(self):
        self.tree.delete(*self.tree.get_children())

    def inserir(self, iid, valores, tags=()):
        self.tree.insert("", "end", iid=str(iid), values=valores, tags=tags)

    def selecionado(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    def exigir_selecao(self, mensagem="Selecione um item na lista."):
        iid = self.selecionado()
        if iid is None:
            raise ErroNegocio(mensagem)
        return iid

    def ao_duplo_clique(self, funcao):
        self.tree.bind("<Double-1>", lambda _e: funcao())


class Dialogo(tk.Toplevel):
    """Janela modal base. Use `.exibir()` para abrir e obter `.resultado`."""

    def __init__(self, master, titulo):
        super().__init__(master)
        self.title(titulo)
        self.transient(master.winfo_toplevel())
        self.resizable(False, False)
        self.resultado = None
        self.protocol("WM_DELETE_WINDOW", self.cancelar)
        self.bind("<Escape>", lambda _e: self.cancelar())
        self.corpo = ttk.Frame(self, padding=14)
        self.corpo.pack(fill="both", expand=True)

    def exibir(self):
        self.update_idletasks()
        pai = self.master.winfo_toplevel()
        x = pai.winfo_rootx() + (pai.winfo_width() - self.winfo_reqwidth()) // 2
        y = pai.winfo_rooty() + (pai.winfo_height() - self.winfo_reqheight()) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass
        self.focus_set()
        self.wait_window(self)
        return self.resultado

    def cancelar(self):
        self.resultado = None
        self.destroy()

    def botoes(self, linha, texto_ok, comando_ok, coluna_span=2):
        quadro = ttk.Frame(self.corpo)
        quadro.grid(row=linha, column=0, columnspan=coluna_span, sticky="e", pady=(12, 0))
        ttk.Button(quadro, text="Cancelar", command=self.cancelar).pack(side="right", padx=(6, 0))
        ttk.Button(quadro, text=texto_ok, command=comando_ok).pack(side="right")
