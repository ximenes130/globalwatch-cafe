---
id: "007"
titulo: Documentação, nota de pesquisa e entrega
status: rascunho
---

# 007 — Documentação e entrega: tarefas

Blocos do dia: 19h às 21h (docs) e 21h às 22h30 (vídeo e envio).
Corte se estourar: comparação com MapBiomas (vira limitação na nota).
`docs/uso-de-ia.md` é preenchido ao longo do dia, não só aqui.

- [ ] **T7.1** (P0) Keepalive do Supabase.
  - _Req: R7.3_
  - Arquivos: `.github/workflows/keepalive.yml`
  - Verificação: execução manual do workflow verde.
- [ ] **T7.2** (P0) README completo com cotas, suspensão, retenção e evidências.
  - _Req: R7.1, R7.2_
  - Arquivos: `README.md`
  - Verificação: checklist de seções do R7.1 e R7.2.
- [ ] **T7.3** (P0) Inspeção visual de 10 a 20 pontos e registro do erro encontrado.
  - _Req: R7.7_
  - Arquivos: `docs/evidencias/inspecao-visual.md`
  - Verificação: tabela de pontos preenchida; antes/depois do ajuste salvo.
- [ ] **T7.4** (P1) Comparação com MapBiomas.
  - _Req: R7.8_
  - Arquivos: `scripts/compare_mapbiomas.py`
  - Verificação: tabela de concordância em `docs/evidencias/`.
- [ ] **T7.5** (P0) Nota de pesquisa com fontes conferidas.
  - _Req: R7.4, R7.5, R7.6, R7.7_
  - Arquivos: `docs/nota-de-pesquisa.md`
  - Verificação: PDF com até 2 páginas; cada referência aberta.
- [ ] **T7.6** (P0) Fechar o relato de uso de IA.
  - _Req: R7.9_
  - Arquivos: `docs/uso-de-ia.md`
  - Verificação: tem ferramentas, validação e um erro concreto.
- [ ] **T7.7** (P0) Licença e auditoria final do repositório.
  - _Req: R7.10_
  - Arquivos: `LICENSE`
  - Verificação: greps de segredos e dados pessoais vazios.
- [ ] **T7.8** (P0) Teste final em aba anônima e gravação do vídeo.
  - _Req: R7.11, R7.12_
  - Verificação: vídeo ≤ 3 min com link público.
