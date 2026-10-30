---
id: "006"
titulo: Segurança, isolamento e limites de uso
status: em-implementacao
---

# 006 — Segurança e limites: design

## Componentes e arquivos

| Arquivo | Responsabilidade |
| --- | --- |
| `backend/app/auth.py` | `current_user` (001) aplicado como dependência em todos os routers |
| `backend/app/validation.py` | Tamanho em streaming, assinatura TIFF, checagens do raster |
| `backend/app/ratelimit.py` | `consume(user_id, kind)`: `insert … on conflict do update … returning` atômico |
| `backend/app/storage.py` | Caminhos com `user_id`, URLs assinadas de 300 s |
| `backend/app/errors.py` | Middleware ASGI, por dentro do CORS, que converte exceções inesperadas em 500 neutro (JSON em português) e registra o detalhe no log |
| `.github/workflows/retention.yml` | *(P1)* agenda diária (e disparo manual) que roda `python -m app.retention` com `DATABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY` dos secrets do GitHub |
| `backend/app/retention.py` | *(P1)* apaga as análises com mais de 7 dias, de qualquer usuário: arquivos no Storage primeiro, depois a linha (mensagens por cascata); análise cujo Storage falhar fica para o dia seguinte e o job termina com erro |

## Limites na interface (R6.16 a R6.19, T6.8)

`GET /me/usage` (com JWT, R6.1) lê a linha de hoje em `usage_daily` sem incrementar:

```json
{
  "uploads": {"used": 2, "limit": 5},
  "messages": {"used": 7, "limit": 30},
  "resets_at": "2026-10-31T00:00:00Z",
  "retention_days": 7
}
```

`resets_at` é a próxima meia-noite UTC (o `current_date` do Supabase). O front guarda a
resposta no TanStack Query e a invalida depois de cada envio, de cada mensagem e de
cada 429.

| Onde | O que aparece |
| --- | --- |
| Área de envio | "3 de 5 envios restantes hoje · renova às 21:00" (hora local) e "As análises ficam guardadas por 7 dias." Com 0: zona de soltar e botão desabilitados e "Você usou os 5 envios de hoje. Libera às 21:00." |
| Rodapé do chat | "27 mensagens restantes hoje"; a partir de 5 restantes, em destaque (cor de aviso, sem vermelho); com 0, campo e sugestões desabilitados com "Libera às 21:00." |
| Lista e painel da análise | "Apagada em 6 dias" (ou "amanhã", "hoje") a partir de `created_at` + 7 dias; na lista, só quando faltar 2 dias ou menos, para não poluir |

Sem número inventado: o restante é `limit - used` vindo da API, e a data de exclusão
usa o `created_at` do banco com o `retention_days` da API. Se `GET /me/usage` falhar, os
avisos de cota somem e o envio continua liberado: o 429 do backend segue valendo.

## Decisões

| Decisão | Alternativa recusada | Motivo |
| --- | --- | --- |
| RLS + filtro no backend | Só RLS; só filtro | O backend usa service role (ignora RLS); a RLS protege acesso direto com anon key |
| Contador no Postgres | Limite em memória (slowapi) | Sobrevive a restart e hibernação do Render |
| 404 para recurso alheio | 403 | Não revela que o id existe |
| URL assinada curta | Bucket público | Isolamento também nos arquivos |
| Documentação da API (`/docs`, `/redoc`, `/openapi.json`) desligada por padrão; `API_DOCS=true` liga no desenvolvimento | Deixar pública | R6.1 só abre `/health`; o schema descreve todas as rotas e não é útil a quem usa o front |
| Retenção por GitHub Actions com os secrets do banco e do Storage | `pg_cron` no Supabase; limpeza na subida da API | O `pg_cron` apaga linhas, mas os arquivos do Storage só saem pela API; o Render free dorme e não tem agenda própria |
| Validação na rota, só o cabeçalho do raster, antes da cota | Deixar para o worker (análise `failed`) | R6.6 e R6.7 pedem 415/422 na resposta; recusar antes não cria linha nem gasta envio do dia. O worker continua tratando o que só aparece nos pixels ou na comparação entre arquivos (grade da SCL e da segunda data) |

## Estratégia de testes

| Requisito | Teste |
| --- | --- |
| R6.1 | `test_auth.py`: todas as rotas do OpenAPI do app sem token e com token inválido → 401, exceto `/health`; documentação da API → 404 por padrão |
| R6.2, R6.3 | `test_isolation.py`: token de B em GET/DELETE/chat da análise de A → 404 |
| R6.5–R6.7 | `test_upload.py`: PNG renomeado, > 20 MB, sem CRS, 3 bandas, float32, 4096 px |
| R6.8, R6.9 | `test_ratelimit.py`: 6º upload e 31ª mensagem → 429 |
| R6.10 | `curl -H "Origin: https://evil.example"` sem header CORS na resposta |
| R6.11 | `git log -p \| grep -iE "key\|secret"` e busca no bundle do front |
| R6.12 | `test_errors.py`: exceção forçada → corpo sem traceback |
| R6.14 | `test_isolation.py`: após DELETE, arquivos não existem |
| R6.16, R6.19 | `test_usage.py`: `GET /me/usage` igual ao contador depois de envios e mensagens, sem incrementar; outro usuário vê os próprios números; sem token → 401 |
| R6.16 a R6.18 | Harness: textos com 5, 1 e 0 restantes em 375 e 1440 px; com 0, envio e chat desabilitados; prazo de exclusão de uma análise de 6 dias atrás |
| R6.15 | `test_retention.py`: só as antigas saem, arquivos antes da linha, falha do Storage preserva a linha e dá código de saída 1; `test_repository.py`: seleção por idade contra Postgres |
