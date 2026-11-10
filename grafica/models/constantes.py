"""Constantes de domínio: perfis de acesso e status da O.S."""


class Perfil:
    ATENDENTE = "Atendente"
    OPERADOR = "Operador"
    ADMINISTRADOR = "Administrador"
    TODOS = (ATENDENTE, OPERADOR, ADMINISTRADOR)


class Status:
    ORCAMENTO = "Orçamento"
    EM_PRODUCAO = "Em Produção"
    CONCLUIDO = "Concluído"
    ENTREGUE = "Entregue"
    CANCELADO = "Cancelado"
    TODOS = (ORCAMENTO, EM_PRODUCAO, CONCLUIDO, ENTREGUE, CANCELADO)
