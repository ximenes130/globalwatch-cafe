# Auditoria de segredos (T6.6, R6.11, R6.13)

Feita em 30/10/2026, depois do commit `ed8b237`. Nenhum valor de chave aparece aqui:
os achados foram impressos mascarados (12 primeiros caracteres e o tamanho).

## Histórico do git

`git log -p --all` inteiro, procurando nas linhas adicionadas: `sk-ant-…` (Anthropic),
`sb_secret_…` (Supabase), JWT (`eyJ….….…`), `GOCSPX-…` (segredo do OAuth do Google) e
connection string com senha (`postgres://usuário:senha@…`).

| Achado | Arquivo | O que é |
| --- | --- | --- |
| `sb_secret_abc123` | `backend/tests/test_errors.py` | Segredo falso: o teste confere que ele não vaza na resposta de erro |
| `postgresql://postgres.<ref>:<senha>@…` | `backend/.env.example` | Exemplo com marcadores |
| `postgresql://postgres:test@localhost…` | `.github/workflows/ci.yml` | Postgres descartável do CI |
| `postgresql://user:password@127.0.0.1:1/db` | `backend/tests/test_health.py` | Endereço inválido de propósito (teste de banco fora do ar) |

Nenhum JWT, chave `sk-ant-`, `GOCSPX-` ou `sb_secret_` real. Arquivos `.env` que já
entraram em algum commit: só `backend/.env.example` e `frontend/.env.example`.

## Bundle do front em produção

Todos os arquivos servidos por `https://globalwatch-cafe.onrender.com` (HTML, os dois
chunks JS, o CSS e o worker do MapLibre), seguindo os imports relativos entre chunks:

| Procura | Ocorrências |
| --- | --- |
| `sk-ant-` | 0 |
| `sb_secret_` | 0 |
| `GOCSPX-` | 0 |
| `service_role` | 0 |
| `postgres://` | 0 |
| JWT | 1, com `role: anon` (a chave pública do Supabase, que o front precisa) |

O front só lê `VITE_API_URL`, `VITE_SUPABASE_URL` e `VITE_SUPABASE_ANON_KEY`.

## Variáveis por serviço no Render (`render.yaml`)

| Serviço | Variáveis |
| --- | --- |
| `globalwatch-cafe` (front) | `NODE_VERSION`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_URL` |
| `globalwatch-cafe-api` (backend) | `SUPABASE_URL`, `SUPABASE_JWT_AUDIENCE`, `DATABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `ANTHROPIC_API_KEY`, `CORS_ORIGINS` |

As secretas (`DATABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `ANTHROPIC_API_KEY`) estão com
`sync: false`: o valor só existe no painel do Render, nunca no repositório.

## Teto de gasto da Anthropic (R6.13)

Pendente: configurado pelo dono da conta no console da Anthropic; o print (sem a chave)
entra aqui como `anthropic-teto.png`.
