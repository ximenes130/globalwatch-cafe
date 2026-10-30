---
description: Escreve ou revisa o design de uma spec com requisitos aprovados
argument-hint: <NNN>
---

Escreva o design da spec `$ARGUMENTS`.

1. Abra `specs/$ARGUMENTS*/requirements.md`. Se `status` não for `aprovado`,
   pare e diga o que falta.
2. Leia a constituição e os designs das specs de que esta depende.
3. Preencha `design.md`: visão geral, componentes e arquivos, contratos,
   decisões com alternativa recusada, riscos e estratégia de testes cobrindo
   **todos** os `R` da spec.
4. Reaproveite componentes já descritos em outras specs em vez de duplicar.
5. Deixe `status: rascunho`, resuma as decisões principais e peça aprovação.
