"""Criptografia de senhas (RNF-03).

Usa BCrypt quando a biblioteca 'bcrypt' está instalada (recomendado:
pip install -r requirements.txt). Caso contrário, recorre a PBKDF2-HMAC-SHA256
da biblioteca padrão, que também é um algoritmo seguro para armazenamento de senhas.
"""
import hashlib
import hmac
import os

try:
    import bcrypt
    BCRYPT_DISPONIVEL = True
except ImportError:  # pragma: no cover - depende do ambiente
    bcrypt = None
    BCRYPT_DISPONIVEL = False

_ITERACOES = 310_000


def _bytes(senha: str) -> bytes:
    # BCrypt considera no máximo 72 bytes
    return senha.encode("utf-8")[:72]


def gerar_hash(senha: str) -> str:
    if BCRYPT_DISPONIVEL:
        return bcrypt.hashpw(_bytes(senha), bcrypt.gensalt()).decode("ascii")
    sal = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, _ITERACOES)
    return f"pbkdf2_sha256${_ITERACOES}${sal.hex()}${dk.hex()}"


def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    if not hash_armazenado:
        return False
    if hash_armazenado.startswith("$2"):
        if not BCRYPT_DISPONIVEL:
            raise RuntimeError("Hash BCrypt armazenado, mas a biblioteca 'bcrypt' não está instalada.")
        return bcrypt.checkpw(_bytes(senha), hash_armazenado.encode("ascii"))
    if hash_armazenado.startswith("pbkdf2_sha256$"):
        _, iteracoes, sal, esperado = hash_armazenado.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), bytes.fromhex(sal), int(iteracoes))
        return hmac.compare_digest(dk.hex(), esperado)
    return False
