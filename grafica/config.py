"""Configurações globais do Sistema de Gestão de Impressões e Suprimentos."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DADOS_DIR = BASE_DIR / "dados"
DB_PATH = DADOS_DIR / "grafica.db"
ARTES_DIR = DADOS_DIR / "artes"          # cópia dos arquivos de arte anexados às O.S.

# RN-01 - área mínima de faturamento (m²)
AREA_MINIMA_M2 = 0.25

# Unidades aceitas para materiais. Materiais em "m²" têm a quantidade calculada
# automaticamente a partir das dimensões da O.S.; os demais são informados à mão.
UNIDADE_AREA = "m²"
UNIDADES = (UNIDADE_AREA, "un", "m")

# EX01 do UC-01 - formatos de arte aceitos
EXTENSOES_ARTE = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}

# Se False, o cadastro de clientes aceita qualquer CPF/CNPJ com 11/14 dígitos
# (útil para demonstrações); se True, valida também os dígitos verificadores.
VALIDAR_DIGITOS_DOCUMENTO = True

TAMANHO_MIN_SENHA = 6
