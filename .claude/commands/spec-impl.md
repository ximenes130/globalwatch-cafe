---
description: Implementa a próxima task (ou a indicada) de uma spec aprovada
argument-hint: <NNN> [T<n>.<m>]
---

Implemente uma task da spec. Argumentos: $ARGUMENTS

1. Abra a pasta `specs/<NNN>*/`. Se `tasks.md` não estiver `aprovado` ou
   `em-implementacao`, pare.
2. Escolha a task indicada ou a primeira `[ ]` em ordem. Leia os `R` que ela
   cita e o trecho do design correspondente.
3. Se a task conflitar com a constituição ou a spec parecer errada, pare e
   proponha a alteração na spec antes de codar.
4. Implemente só essa task, com testes quando a verificação pedir.
5. Rode a verificação da task e mostre a saída real.
6. Se passou: marque `[x]`; mude `status` dos três arquivos para
   `em-implementacao` (ou `concluido` se era a última task), atualize o índice
   em `specs/README.md` e adicione uma linha em `docs/uso-de-ia.md`.
7. Pare e peça revisão. Não faça commit sem pedido.
