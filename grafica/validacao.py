"""Funções utilitárias de validação e formatação de documentos e e-mails."""
import re


def so_digitos(texto) -> str:
    return re.sub(r"\D", "", texto or "")


def cpf_valido(cpf: str) -> bool:
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for i in (9, 10):
        soma = sum(int(cpf[n]) * (i + 1 - n) for n in range(i))
        if ((soma * 10) % 11) % 10 != int(cpf[i]):
            return False
    return True


def cnpj_valido(cnpj: str) -> bool:
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False

    def digito(base, pesos):
        resto = sum(int(d) * p for d, p in zip(base, pesos)) % 11
        return 0 if resto < 2 else 11 - resto

    p1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    p2 = [6] + p1
    return digito(cnpj[:12], p1) == int(cnpj[12]) and digito(cnpj[:13], p2) == int(cnpj[13])


def email_valido(email: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email or ""))


def formatar_cpf_cnpj(valor: str) -> str:
    d = so_digitos(valor)
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    if len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    return d
