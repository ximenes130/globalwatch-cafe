---
id: "007"
titulo: Documentação, nota de pesquisa e entrega
status: em-implementacao
---

# 007 — Documentação e entrega: tarefas

A inspeção vem primeiro, porque a nota cita o resultado dela.
A comparação com o MapBiomas já foi feita (T2.5, T3.3); aqui ela só é resumida.
`docs/uso-de-ia.md` é preenchido ao longo do dia, não só aqui.

- [x] **T7.1** (P0) Inspeção visual de 15 pontos.
  - _Req: R7.7_
  - Arquivos: `scripts/inspect_points.py`, `docs/evidencias/inspecao/`
  - Verificação: prancha gerada pelo pipeline do app; tabela preenchida e
    revisada pelo usuário.
- [x] **T7.2** (P0) Nota de pesquisa em duas páginas e método detalhado.
  - _Req: R7.4, R7.5, R7.6, R7.7, R7.8, R7.13_
  - Arquivos: `docs/nota-de-pesquisa.md`, `docs/nota-de-pesquisa.pdf`,
    `docs/metodo.md`
  - Verificação: `pdfinfo` com até 2 páginas; condições de uso conferidas na
    fonte; nenhuma acurácia ou confiança.
- [ ] **T7.3** (P0) README completo.
  - _Req: R7.1, R7.2, R7.3_
  - Arquivos: `README.md`
  - Verificação: checklist de seções do R7.1 a R7.3; cotas com data da
    consulta; diagrama renderizado no GitHub.
- [ ] **T7.4** (P0) Fechar o relato de uso de IA.
  - _Req: R7.9_
  - Arquivos: `docs/uso-de-ia.md`
  - Verificação: tem ferramentas, validação e casos concretos de erro.
- [ ] **T7.5** (P0) Licença, auditoria final e repositório público.
  - _Req: R7.10_
  - Arquivos: `LICENSE`
  - Verificação: greps de segredos e dados pessoais no histórico inteiro
    vazios; repositório público com o ok do usuário.
- [ ] **T7.6** (P0, usuário) Teste em aba anônima, vídeo e envio.
  - _Req: R7.11, R7.12_
  - Verificação: fluxo completo com outra conta Google, com o kit e a imagem
    adicional; vídeo de até 3 min com link público.
