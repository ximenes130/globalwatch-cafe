"""Loop de tool use com o Claude e coleta dos cards (R5.6, R5.7, R5.10 a R5.13).

Loop manual em vez do tool runner do SDK (beta): aqui é preciso escolher o
`tool_choice` de cada rodada (resumo forçado na apresentação, `none` na última) e
montar os cards a partir dos resultados das ferramentas.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import anthropic

from app.chat.prompt import SYSTEM_PROMPT
from app.chat.tools import TOOL_DEFINITIONS, AnalysisTools, ToolError

log = logging.getLogger(__name__)

MODEL = "claude-haiku-5-5"
# O raciocínio do Haiku 5.5 conta no `max_tokens`: folga para ele e uma resposta de
# ~150 palavras. Esforço baixo: perguntas curtas sobre dados já calculados.
MAX_TOKENS = 2048
EFFORT = "low"
# Rodadas com ferramentas por mensagem; a seguinte sai com `tool_choice: none` (R5.6).
MAX_TOOL_ROUNDS = 4
# Por chamada à API, com uma nova tentativa do SDK: no pior caso ~1 min por rodada.
TIMEOUT_SECONDS = 30
MAX_RETRIES = 1

UNAVAILABLE = "O assistente não conseguiu responder agora. Tente de novo em instantes."
BUSY = "O assistente está com muitas mensagens agora. Tente de novo em um minuto."


class ChatUnavailable(Exception):
    """Falha da API do modelo; a mensagem é segura para mostrar ao usuário (R5.7)."""


@dataclass
class ChatReply:
    reply: str
    cards: list[dict[str, Any]] = field(default_factory=list)


def make_client(api_key: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=api_key, timeout=TIMEOUT_SECONDS, max_retries=MAX_RETRIES)


def converse(
    client: anthropic.Anthropic,
    tools: AnalysisTools,
    messages: list[dict],
    force_summary: bool = False,
) -> ChatReply:
    """Conversa até o modelo responder com texto; `messages` termina na vez do usuário.

    `force_summary`: na apresentação (R5.1) a primeira rodada é obrigada a chamar
    `get_analysis_summary`, então o card de resumo sempre vem junto.
    """
    cards: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    usage = [0, 0]

    for round_number in range(MAX_TOOL_ROUNDS + 1):
        if round_number == MAX_TOOL_ROUNDS:
            tool_choice = {"type": "none"}
        elif round_number == 0 and force_summary:
            tool_choice = {"type": "tool", "name": "get_analysis_summary"}
        else:
            tool_choice = {"type": "auto"}

        response = _create(client, messages, tool_choice)
        usage[0] += response.usage.input_tokens
        usage[1] += response.usage.output_tokens

        if response.stop_reason == "refusal":
            log.warning("Chat recusado pelo modelo: %s", response.stop_details)
            raise ChatUnavailable("O assistente não pode responder a essa mensagem.")

        tool_uses = [block for block in response.content if block.type == "tool_use"]
        if response.stop_reason != "tool_use" or not tool_uses:
            # O texto pode vir depois de blocos de raciocínio: lido por tipo, não por posição.
            text = "".join(b.text for b in response.content if b.type == "text").strip()
            if not text:
                log.warning("Chat sem texto (stop_reason=%s)", response.stop_reason)
                raise ChatUnavailable(UNAVAILABLE)
            log.info(
                "Chat: %d rodada(s), %d card(s), %d tokens de entrada, %d de saída",
                round_number + 1,
                len(cards),
                *usage,
            )
            return ChatReply(text, cards)

        # A resposta volta inteira (com os blocos de raciocínio) antes dos resultados.
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in tool_uses:
            try:
                output = tools.run(block.name, block.input)
            except ToolError as exc:
                # Sem card: o modelo explica a falha no texto (R5.13).
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(exc),
                        "is_error": True,
                    }
                )
                continue
            # O mesmo objeto vai ao modelo e ao card (R5.11).
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(output.data, ensure_ascii=False),
                }
            )
            key = (block.name, json.dumps(block.input, sort_keys=True))
            if key not in seen:  # R5.12
                seen.add(key)
                cards.append({"kind": output.kind, "data": output.data})
        # Todos os resultados numa mensagem só, como a API espera.
        messages.append({"role": "user", "content": results})

    raise AssertionError("inalcançável: a última rodada sai com tool_choice none")


def _create(client: anthropic.Anthropic, messages: list[dict], tool_choice: dict):
    try:
        return client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            tool_choice=tool_choice,
            output_config={"effort": EFFORT},
            messages=messages,
        )
    except anthropic.RateLimitError as exc:
        log.warning("Chat: limite da API do modelo (%s)", exc.status_code)
        raise ChatUnavailable(BUSY) from exc
    except (anthropic.APITimeoutError, anthropic.APIConnectionError) as exc:
        log.warning("Chat: API do modelo inacessível ou lenta: %s", exc)
        raise ChatUnavailable(UNAVAILABLE) from exc
    except anthropic.APIStatusError as exc:
        # 400/401/5xx: o detalhe fica no log; o usuário recebe a mensagem neutra.
        log.error("Chat: API do modelo respondeu %s: %s", exc.status_code, exc.message)
        raise ChatUnavailable(UNAVAILABLE) from exc
