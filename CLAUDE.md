# Global Watch — assistente geoespacial para café

Desafio técnico: app React + Python em que o usuário entra com Google, envia
uma imagem Sentinel-2 e conversa com uma IA sobre **áreas potenciais** de café.
Enunciado: `data/exemplo/DESAFIO.txt`. Prazo: 30/10/2026.

## Forma de trabalho: SDD

Leia `specs/README.md` e `specs/000-constituicao.md` antes de qualquer tarefa.

1. Nada de código sem spec. Toda mudança aponta para uma task `T<n>.<m>` de
   `specs/<NNN>/tasks.md`, que aponta para requisitos `R<n>.<m>`.
2. Fases com gate humano: requirements → design → tasks → implementação. Não
   mude um `status` para `aprovado` sem o usuário dizer que aprovou.
3. Implemente **uma task por vez**: faça, rode a verificação da task, mostre o
   resultado, marque `[x]` e pare para revisão.
4. Se a spec estiver errada ou incompleta, pare e proponha a alteração na spec
   antes de seguir.
5. Registre em `docs/uso-de-ia.md` cada task feita com IA (o que foi pedido,
   como foi validado, erros pegos).
6. O usuário precisa conseguir explicar todo o código: prefira soluções simples
   e comente o porquê das decisões não óbvias.

## Regras que não se negociam (resumo da constituição)

- Resultado é "área potencial de café", nunca "café". Sem acurácia ou
  confiança sem evidência.
- Números e geometrias só vêm do processamento; o LLM lê por ferramenta.
- Processar o arquivo enviado de verdade; nada pré-calculado.
- JWT validado no backend em toda rota exceto `/health`; isolamento por
  `user_id` (RLS + filtro no código); recurso alheio → 404.
- Segredos só em env; no repositório, só `.env.example`.
- Só serviços gratuitos. Dados de terceiros sempre com atribuição.
- DN → reflectância **uma vez só**; área em UTM antes de reprojetar; kit = 2.621,44 ha.
- Identificadores de código em inglês (en-US); comentários, docstrings, textos de UI,
  specs e docs em pt-BR (C6.5).

## Stack

- Frontend: Vite, React, TypeScript, Tailwind, shadcn/ui, MapLibre GL, TanStack Query.
- Backend: FastAPI, rasterio, numpy, scipy, shapely, pyproj.
- Supabase: Auth (Google), Postgres com RLS, Storage privado.
- LLM: Claude Haiku 5.5 (`claude-haiku-5-5`) com tool use e visão.
- Deploy: Vercel (front), Render Docker free (back).

## Layout

```text
specs/          SDD: constituição, templates e uma pasta por funcionalidade
backend/        FastAPI (app/, tests/)
frontend/       React
supabase/       migrations
scripts/        download da cena adicional, calibração, comparações
data/exemplo/   kit original (não alterar; SHA256SUMS.txt confere)
docs/           nota de pesquisa, uso de IA, evidências
```

## Commits

[Conventional Commits](https://www.conventionalcommits.org/pt-br/v1.0.0/):
`<tipo>(<escopo>): <descrição>`.

- Tipos: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `build`, `ci`,
  `chore`, `style`.
- Escopo opcional: `backend`, `frontend`, `supabase`, `scripts`, `specs`,
  `deploy` ou o número da spec (`001`).
- Descrição em português, no imperativo, minúscula, sem ponto final, até ~72
  caracteres. Corpo opcional explica o porquê; cite a task (`T1.2`).
- Mudança incompatível: `!` após o tipo/escopo e rodapé `BREAKING CHANGE:`.
- Sem trailer `Co-Authored-By` nem outra atribuição de IA (o uso de IA fica
  em `docs/uso-de-ia.md`).

Exemplos: `feat(backend): adiciona /health com checagem do banco` ·
`docs(specs): aprova spec 001` · `test(002): cobre conversão única de DN`.

## Comandos

Tudo junto (`compose.yaml`, requer `backend/.env` e `frontend/.env.local`):

- Subir: `docker compose up --build` (API em :8000 e front em :5173, com recarga automática)
- Teste de RLS em Postgres descartável: `docker compose --profile test run --rm rls-test`
- Parar: `docker compose down` (perfil de teste: `docker compose --profile test down`)

Backend (em `backend/`):

- Ambiente: `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"`
- Rodar: `.venv/bin/uvicorn app.main:app --reload` (lê `backend/.env`)
- Testes: `.venv/bin/pytest -q`
- Lint e formatação: `.venv/bin/ruff check . && .venv/bin/ruff format --check .`
- Docker: `docker build -t globalwatch-backend . && docker run -p 8000:8000 globalwatch-backend`

Banco (Supabase, migrations em `supabase/migrations/`):

- Teste de RLS local: `supabase/tests/run.sh` contra qualquer Postgres puro (variáveis `PG*`);
  é o que o perfil `test` do compose e o CI executam.
- No Supabase: mesmos arquivos (sem o stub) com `psql "$DATABASE_URL"` lido de `backend/.env`;
  migration com `--single-transaction`. O teste roda em transação com rollback.

Frontend (em `frontend/`, variáveis em `frontend/.env.local`):

- Ambiente: `npm ci`
- Rodar: `npm run dev` (http://localhost:5173)
- Lint, tipos e build: `npm run lint && npm run build`

CI: `.github/workflows/ci.yml` roda backend (ruff, pytest), banco (migrations + teste de RLS em
Postgres 17) e frontend (oxlint, build). Deploy: `render.yaml` (back) e `frontend/vercel.json`.

Kit: integridade com `cd data/exemplo && sha256sum -c SHA256SUMS.txt`
