# Specs

Desenvolvimento orientado a especificação (SDD), no formato enxuto do Kiro.
Princípios inegociáveis em [000-constituicao.md](000-constituicao.md).

## Fluxo

```text
requirements.md ──ok──> design.md ──ok──> tasks.md ──ok──> implementação (uma task por vez)
   rascunho → aprovado     rascunho → aprovado     rascunho → aprovado → em-implementacao → concluido
```

- Cada fase só começa com a anterior `aprovado` (aprovação humana).
- Se a implementação mostrar que a spec está errada, atualize a spec primeiro.
- Comandos: `/spec-new`, `/spec-design`, `/spec-tasks`, `/spec-impl`,
  `/spec-status` (em `.claude/commands/`).

## Convenções

- **Requisitos** em EARS, em português, com ID `R<spec>.<n>`:
  `O SISTEMA DEVE …` · `QUANDO <evento>, …` · `SE <condição>, ENTÃO …` ·
  `ENQUANTO <estado>, …` · `ONDE <opcional>, …`.
- **Tarefas** com ID `T<spec>.<n>`, prioridade `P0` (obrigatório) ou `P1`
  (corta se estourar), `_Req: …_` apontando para os requisitos, arquivos e
  verificação.
- Rastreabilidade: item do DESAFIO → `R` → `T` → teste/evidência.
- Modelos em [_templates/](_templates/).

## Índice

| Spec | Itens do DESAFIO | Pontos | Bloco do dia | Status |
| --- | --- | --- | --- | --- |
| [001 Fundação, auth e deploy](001-fundacao-auth-deploy/) | 1, 8 | Deploy 10 + seg. | 8h–10h | concluido |
| [002 Processamento e classificação](002-processamento-classificacao/) | 2, 3 | 20 | 10h–13h | rascunho |
| [003 Imagem adicional](003-imagem-adicional/) | pesquisa | parte de 15 | 13h–14h | rascunho |
| [004 Mapa e UI](004-mapa-ui/) | 4, 6 | 20 | 14h–16h30 | rascunho |
| [005 Chat com IA](005-chat-ia/) | 5 | 10 | 16h30–18h | rascunho |
| [006 Segurança e limites](006-seguranca-limites/) | 7 | 20 | 18h–19h (transversal) | rascunho |
| [007 Documentação e entrega](007-documentacao-entrega/) | entregáveis | 15 + 10 + 5 | 19h–22h30 | rascunho |

A coluna Status espelha o frontmatter dos arquivos; `/spec-status` recalcula.
