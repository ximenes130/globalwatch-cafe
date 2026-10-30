---
description: Gera as tarefas rastreadas de uma spec com design aprovado
argument-hint: <NNN>
---

Gere as tarefas da spec `$ARGUMENTS`.

1. Abra `requirements.md` e `design.md` de `specs/$ARGUMENTS*/`. Se o design
   não estiver `aprovado`, pare.
2. Escreva `tasks.md` em ordem de execução. Cada task: `T<n>.<m>`, `P0`/`P1`,
   `_Req: …_`, arquivos e verificação concreta (teste ou comando).
3. Todo `R` precisa de pelo menos uma task; toda task aponta para um `R`
   existente. Confira e informe.
4. Tasks pequenas o bastante para revisar de uma vez (idealmente < 1 h).
5. Deixe `status: rascunho` e peça aprovação.
