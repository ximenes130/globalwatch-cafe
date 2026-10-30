"""Erros esperados do processamento."""


class ProcessingError(Exception):
    """Falha prevista, com mensagem em português que pode ir para o usuário.

    Erros inesperados continuam como exceções comuns: o worker registra o stack
    trace no log e grava uma mensagem genérica (R2.19).
    """
