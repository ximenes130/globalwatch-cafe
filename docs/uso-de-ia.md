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
| 30/10 | T1.3 | Migration `001_init.sql` com RLS e teste de isolamento | Teste SQL em Postgres 17 local e no Supabase (rollback, 0 linhas residuais); teste negativo com `update` indevido concedido falha como esperado; `/health` local com `db: ok` | Spec só dizia `user_id = auth.uid()`: política de escrita deixaria o usuário zerar `usage_daily`. Design ajustado para leitura apenas |
| 30/10 | T1.4 | Validação do JWT por JWKS (ES256), rota `/me` e testes | 21 testes (token válido, ausente, malformado, expirado, `aud`/`iss` errados, claims faltando, outra chave, `kid` desconhecido, HS256, sessão anônima, JWKS fora); teste de mutação: remover `issuer`, a checagem de anônimo ou liberar HS256 derruba o teste certo; JWKS real do projeto carregado; `curl` no container | |
| 30/10 | T1.5 | Frontend (Vite, React, Tailwind, shadcn/ui), login Google, sair, cliente da API, identidade visual | `tsc`, `oxlint`, `npm run build`; capturas do Chrome headless em 1440 px e 375 px revelaram dois defeitos na régua de NDVI (moldura cobrindo o "0,6", rótulo cortado no celular), corrigidos; login Google ponta a ponta confirmado pelo usuário em `localhost:5173` (e-mail vindo de `/me`) | O shadcn gerou dependência do pacote `cn`, cuja versão 0.5.1 tinha sido publicada 30 min antes: fixada a 0.5.0 (duas semanas) por precaução de cadeia de suprimentos |
| 30/10 | T1.6 | `.env.example` de backend e frontend | `git check-ignore` confirma `.env` e `.env.local` ignorados e os exemplos versionáveis | |
| 30/10 | T1.8 | CI com ruff, pytest, teste de RLS em Postgres 17 e build do front | Execução 41013727541 verde; log confirma `OK: isolamento da RLS verificado` e `21 passed` | |
| 30/10 | T1.9 | `compose.yaml` (api com reload, web com Vite, perfil de teste de RLS) e script único `run.sh` usado também pelo CI | `docker compose config`; perfil `test` executado duas vezes seguidas com `OK` (stub tornado idempotente); `up --wait` com `/health` em `db: ok`, `/me` 401, Vite servindo; recarga do backend e HMR do front confirmados nos logs | Requisito fora das specs: R1.12 e T1.9 acrescentados à spec 001 antes do código |
| 30/10 | T1.7 (preparo) | Avaliar front no mesmo provedor do back; migrar de Vercel para Static Site no Render | `render.yaml` validado contra o JSON Schema oficial do Render; spec 001 atualizada antes (R1.8, decisão no design, T1.7) | IA recomendou não servir o front pelo FastAPI (página presa ao cold start) |
| 30/10 | T1.7 | Deploy pelo Blueprint e diagnóstico do redirect para `localhost:3000` | Bundle de produção inspecionado (URLs da API e do Supabase corretas); preflight CORS aceita só a origem do front; causa identificada como Site URL padrão do Supabase com a URL de produção fora de Redirect URLs; após o ajuste, login em produção confirmado pelo usuário; `curl`: `/health` com `db: ok`, `/me` 401 sem token e com token inválido, cabeçalhos de segurança e rewrite de SPA no front | |

| 30/10 | Design 002 (pesquisa) | Pesquisar métodos publicados de mapeamento de café e atualizar o design de processamento e classificação | Só entraram no design referências abertas; PDFs de Parreiras (2025) e Maskell (2021) lidos por `pdftotext`, não por resumo; nível de conferência de cada referência anotado no design; números do kit (histograma, r NDVI x GNDVI = 0,96) medidos em script descartável | Busca sugeriu "Kawakubo" como artigo de café no Sudeste sem achá-lo: não citado. A própria IA escreveu que o EVI é mais sensível a ruído atmosférico (é o contrário, o azul serve para corrigir isso) e citou um "relato da Embrapa" não aberto: ambos corrigidos antes de mostrar |
| 30/10 | Requisitos e tarefas 002 | Alinhar requisitos e tarefas ao design revisado pela pesquisa | Conferido que todo R2.x aparece em alguma T2.x e na tabela de testes do design | A IA tinha dito que os requisitos não precisavam mudar; ao reler, R2.9 atribuía ao GNDVI a separação mata x café, que a pesquisa não sustenta (corrigido), e R2.14/R2.18 não cobriam a área por nível e as referências |

## Casos em que a IA errou

<!-- pelo menos um caso concreto: o que gerou, como percebeu, como corrigiu -->

- **Identificadores em português (30/10, T1.2):** a IA escreveu specs e código
  com nomes em pt-BR (`leitura.py`, `db.verificar()`, `"nao_configurado"`,
  `obter_poligono`). Percebido na revisão do T1.2. Correção: regra C6.5 na
  constituição (identificadores em en-US, textos em pt-BR), renomeação em todas
  as specs e no backend, testes e build refeitos.
