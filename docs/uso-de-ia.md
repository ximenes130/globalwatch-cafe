# Uso de IA no desenvolvimento

Preenchido durante o trabalho, não no fim (C6.4). Requisito: R7.9.

## Ferramentas

- Claude Code (Claude Opus) — specs, código e testes, em fluxo SDD com aprovação humana entre fases.

## Diário

| Data/hora | Task | O que foi pedido à IA | Como foi validado | Erro pego / correção |
| --- | --- | --- | --- | --- |
| 30/10 | Organização | Estrutura SDD e specs a partir do enunciado e do plano | Revisão manual das specs; checagem de rastreabilidade R → T | |
| 30/10 | T1.1 | Criar repositório público e primeiro push via `gh` | `git log -p` sem padrões de chave (`sk-ant-`, JWT, `gh*_`, `AKIA`); só menções textuais nas specs | |
| 30/10 | T1.2 | Backend mínimo (FastAPI, `/health` com `select 1`, Dockerfile) | `pytest` (3 testes, incluindo falha real de conexão), `ruff`, `docker build` + `curl /health` nas portas 8000 e 9000 (`PORT` do Render), container sem root | Spec não definia `/health` com banco fora: ajustado o design antes do código. Trocado `httpx` por `httpx2` após aviso de depreciação do Starlette 1.10 |

## Casos em que a IA errou

<!-- pelo menos um caso concreto: o que gerou, como percebeu, como corrigiu -->

- **Identificadores em português (30/10, T1.2):** a IA escreveu specs e código
  com nomes em pt-BR (`leitura.py`, `db.verificar()`, `"nao_configurado"`,
  `obter_poligono`). Percebido na revisão do T1.2. Correção: regra C6.5 na
  constituição (identificadores em en-US, textos em pt-BR), renomeação em todas
  as specs e no backend, testes e build refeitos.
