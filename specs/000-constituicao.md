---
id: "000"
titulo: Constituição do projeto
status: aprovado
---

# Constituição

Princípios que valem para todas as specs. Uma spec, um design ou uma task que
contrarie um deles está errada e volta para revisão antes de virar código.

## 1. Honestidade do resultado

- **C1.1** O resultado se chama **"área potencial de café"**. Nunca "café",
  "cafezal" ou "café detectado", na UI, no chat, no GeoJSON ou nos docs.
- **C1.2** Nenhum percentual de acurácia, confiança ou probabilidade é exibido
  sem evidência medida e documentada. O kit não tem gabarito.
- **C1.3** Índice de vegetação sozinho não comprova café. Toda saída deixa
  claro que a classificação é potencial e não validada (`validado: false`).
- **C1.4** Limitações do método são parte do produto: aparecem na UI, no chat
  e no README.

## 2. Números vêm do processamento

- **C2.1** Áreas, contagens, datas, índices e geometrias são calculados pelo
  backend a partir do arquivo enviado. O LLM só lê esses valores por
  ferramenta; nunca os estima.
- **C2.2** Nada de resultado fixo ou pré-calculado. Um arquivo diferente do kit
  gera um resultado diferente.
- **C2.3** Cada análise salva `params` e `method_version` junto do resultado.
  O mesmo arquivo com os mesmos parâmetros produz o mesmo resultado.

## 3. Segurança por padrão

- **C3.1** Todo endpoint, exceto `/health`, exige JWT validado no backend.
- **C3.2** Todo dado é isolado por `user_id`, no banco (RLS) e no código
  (filtro explícito). Recurso de outro usuário responde 404.
- **C3.3** Segredos só em variáveis de ambiente do serviço. No repositório,
  apenas `.env.example`.
- **C3.4** Uploads são validados antes de qualquer processamento, e há limite
  diário de uso por usuário.

## 4. Custo zero para o avaliador

- **C4.1** Só serviços com plano gratuito. O avaliador não paga nem fornece
  chave.
- **C4.2** Cotas, suspensão por inatividade e retenção de dados ficam
  documentadas com a data da consulta.

## 5. Rastreabilidade e dados de terceiros

- **C5.1** Dados de terceiros andam com a atribuição e os termos
  (`data/exemplo/ATRIBUICAO.txt`). Imagens adicionais ganham atribuição
  equivalente.
- **C5.2** Toda referência citada foi aberta e conferida (título, autores, ano).

## 6. Forma de trabalho

- **C6.1** Spec antes de código: requisitos → design → tarefas → implementação,
  com aprovação humana entre as fases.
- **C6.2** Deploy cedo. Algo publicado e funcionando primeiro; melhorias depois.
- **C6.3** Todo código que entra no repositório precisa ser explicável e
  defensável pelo autor. Código gerado por IA é revisado linha a linha.
- **C6.4** O uso de IA é registrado em `docs/uso-de-ia.md` durante o trabalho,
  não no fim.
- **C6.5** Documentação em português do Brasil. Código segue os nomes definidos
  no `design.md` de cada spec.
