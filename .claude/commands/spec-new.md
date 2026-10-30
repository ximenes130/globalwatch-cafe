---
description: Cria uma nova spec e escreve os requisitos (EARS) com o usuário
argument-hint: <nome-da-funcionalidade>
---

Crie uma nova spec para: $ARGUMENTS

1. Leia `specs/README.md` e `specs/000-constituicao.md`.
2. Descubra o próximo número livre `NNN` em `specs/` e crie
   `specs/NNN-<slug>/` copiando os três arquivos de `specs/_templates/`.
3. Escreva `requirements.md`: objetivo, histórias, critérios em EARS com IDs
   `R<NNN sem zeros>.<n>`, fora de escopo e questões abertas. Ligue aos itens
   do `data/exemplo/DESAFIO.txt` no frontmatter.
4. Se houver dúvida que muda o escopo, pergunte antes de escrever.
5. Adicione a linha da spec no índice de `specs/README.md`.
6. Deixe `status: rascunho`, mostre um resumo e peça aprovação. Não escreva
   design nem código.
