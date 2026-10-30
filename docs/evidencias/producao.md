# Verificação em produção (T2.11, T3.4)

Execuções de `scripts/smoke_analysis.sh` contra `https://globalwatch-cafe-api.onrender.com`
em 30/10/2026, com o token da sessão do usuário. O tempo do script vai do início do upload até
o `GET` que vê o status final (consulta a cada 2 s), então inclui upload e espera da consulta.

| Envio | Análise | Status | Tempo no script | Área potencial | Polígonos | Excluído por amplitude |
| --- | --- | --- | --- | --- | --- | --- |
| Kit (16/08/2025) | `35109eae` | `completed` | 24 s | 214,54 ha | 124 | 0,00 ha |
| Kit (16/08/2025) | `057cab57` | `completed` | 22 s | 214,54 ha | 124 | 0,00 ha |
| Kit (16/08/2025) | `c9efd5c0` | `completed` | 25 s | 214,54 ha | 124 | 0,00 ha |
| Cena adicional (10/01/2026) | `fcacb95e` | `completed` | 19 s | 139,12 ha | 75 | 0,00 ha |
| Kit + segunda data (10/01/2026) | `dda20b94` | `completed` | 23 s | 103,04 ha | 68 | 101,78 ha |

Em todas: área total 2.621,44 ha, `erro: None` e os quatro links assinados
(`rgb_png`, `classification_png`, `polygons_png`, `geojson`).

## Conferência

- Kit: mesmos números da execução local e dos testes (T2.9).
- Cena adicional: igual a `comparacao-datas/resumo.txt` (139,12 ha, 75 polígonos), como pede a T3.4.
- Duas datas: igual à verificação local da T3.5 (103,04 ha, 68 polígonos, N3c com 101,78 ha).

## Duração do processamento no servidor (T2.11)

Pendente. A linha `Análise … terminou como … em N s` do worker não aparecia no log: o uvicorn
só configura os próprios loggers, e os `log.info` de `app.*` eram descartados. Corrigido em
`backend/app/main.py`; a duração entra aqui depois de um novo envio em produção.
