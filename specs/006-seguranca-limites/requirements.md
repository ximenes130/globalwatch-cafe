---
id: "006"
titulo: Segurança, isolamento e limites de uso
status: aprovado
desafio: [7]
pontos: Segurança e backend (20)
prioridade: P0 (P1 só a retenção automática)
---

# 006 — Segurança e limites: requisitos

## Objetivo

Requisitos transversais de segurança. As specs 001, 002 e 005 implementam
partes deles e apontam para os IDs daqui; esta spec fecha o que faltar e
produz a evidência de testes para o README.

## Histórias

- **H6.1** Como usuário, quero que ninguém veja minhas imagens e análises,
  para confiar no serviço.
- **H6.2** Como dono do projeto, quero limitar uso e proteger chaves, para não
  ter custo ou abuso durante a avaliação.

## Critérios de aceite (EARS)

### Autenticação e isolamento

- **R6.1** — Todo endpoint, exceto `GET /health`, DEVE exigir JWT válido
  (R1.5); sem token, 401.
- **R6.2** — SE um usuário pedir análise, arquivo ou chat de outro usuário,
  ENTÃO O SISTEMA DEVE responder 404 (não 403, para não revelar existência).
- **R6.3** — O backend DEVE filtrar por `user_id` em toda consulta, além da RLS
  do banco (defesa em duas camadas).
- **R6.4** — O storage DEVE ser privado, com caminho
  `analyses/<user_id>/<analysis_id>/` e acesso apenas por URL assinada de até
  5 minutos.

### Validação de upload

- **R6.5** — SE o arquivo passar de 20 MB, ENTÃO O SISTEMA DEVE responder 413
  antes de ler o conteúdo inteiro.
- **R6.6** — SE a extensão não for `.tif/.tiff` ou a assinatura não for TIFF
  (`II*\0`, `MM\0*` ou BigTIFF), ENTÃO O SISTEMA DEVE responder 415.
- **R6.7** — SE o raster não abrir com rasterio em `MemoryFile`, não tiver CRS,
  tiver menos de 4 bandas, não for `uint16` ou passar de 2048 x 2048 px, ENTÃO
  O SISTEMA DEVE responder 422 com mensagem específica para cada caso.

### Limites

- **R6.8** — O SISTEMA DEVE limitar a 5 uploads por usuário por dia, com
  contador no Postgres (`usage_daily`), e responder 429 com mensagem amigável.
- **R6.9** — O SISTEMA DEVE limitar a 30 mensagens de chat por usuário por dia,
  com o mesmo mecanismo.

### Configuração e segredos

- **R6.10** — O CORS DEVE aceitar apenas a origem do front (e `localhost` em
  desenvolvimento).
- **R6.11** — `ANTHROPIC_API_KEY` e `SUPABASE_SERVICE_ROLE_KEY` DEVEM existir
  só nas variáveis do serviço de backend; o front só conhece URL e anon key.
- **R6.12** — Respostas de erro NÃO DEVEM expor stack trace, caminhos ou
  segredos.
- **R6.13** — A conta da Anthropic DEVE ter teto de gasto configurado.

### Dados

- **R6.14** — QUANDO o usuário apagar uma análise, O SISTEMA DEVE remover
  linha, mensagens e arquivos do storage.
- **R6.15** — O SISTEMA DEVE apagar análises com mais de 7 dias *(P1: se
  cortado, a política fica documentada e a limpeza é manual)*.

## Fora de escopo

- WAF, captcha, auditoria de acesso.

## Questões abertas

- Nenhuma.
