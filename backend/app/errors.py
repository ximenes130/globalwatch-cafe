"""Erro inesperado vira uma resposta neutra (R6.12).

O detalhe (stack trace, caminhos, mensagens com dados) fica só no log do servidor. A
resposta é JSON em português, como os outros erros da API.

É um middleware ASGI registrado antes do CORS, para ficar por dentro dele: o 500 sai
com `Access-Control-Allow-Origin` e o front consegue ler a mensagem. Sem isso, o
navegador vê um erro de CORS e o front mostra "sem conexão".
"""

import logging

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

log = logging.getLogger(__name__)

INTERNAL_ERROR = "Erro interno do servidor. Tente de novo em instantes."


class NeutralErrors:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = False

        async def tracking_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, tracking_send)
        except Exception:
            log.exception("Erro inesperado em %s %s", scope.get("method"), scope.get("path"))
            # Resposta já começou (ex.: tarefa depois do 202): não dá para trocar.
            if started:
                raise
            await JSONResponse({"detail": INTERNAL_ERROR}, status_code=500)(scope, receive, send)
