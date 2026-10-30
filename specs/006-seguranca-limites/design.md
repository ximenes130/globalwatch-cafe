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
| `backend/app/errors.py` | Handler global que converte exceções em mensagens neutras |
| `.github/workflows/retention.yml` | *(P1)* agenda diária que chama a limpeza |

## Decisões

| Decisão | Alternativa recusada | Motivo |
| --- | --- | --- |
| RLS + filtro no backend | Só RLS; só filtro | O backend usa service role (ignora RLS); a RLS protege acesso direto com anon key |
| Contador no Postgres | Limite em memória (slowapi) | Sobrevive a restart e hibernação do Render |
| 404 para recurso alheio | 403 | Não revela que o id existe |
| URL assinada curta | Bucket público | Isolamento também nos arquivos |
| Validação na rota, só o cabeçalho do raster, antes da cota | Deixar para o worker (análise `failed`) | R6.6 e R6.7 pedem 415/422 na resposta; recusar antes não cria linha nem gasta envio do dia. O worker continua tratando o que só aparece nos pixels ou na comparação entre arquivos (grade da SCL e da segunda data) |

## Estratégia de testes

| Requisito | Teste |
| --- | --- |
| R6.1 | `test_auth.py`: todas as rotas registradas sem token → 401 (itera o router) |
| R6.2, R6.3 | `test_isolation.py`: token de B em GET/DELETE/chat da análise de A → 404 |
| R6.5–R6.7 | `test_upload.py`: PNG renomeado, > 20 MB, sem CRS, 3 bandas, float32, 4096 px |
| R6.8, R6.9 | `test_ratelimit.py`: 6º upload e 31ª mensagem → 429 |
| R6.10 | `curl -H "Origin: https://evil.example"` sem header CORS na resposta |
| R6.11 | `git log -p \| grep -iE "key\|secret"` e busca no bundle do front |
| R6.12 | `test_errors.py`: exceção forçada → corpo sem traceback |
| R6.14 | `test_isolation.py`: após DELETE, arquivos não existem |
