-- Cards das respostas do chat (specs/005-chat-ia, T5.5, R5.9).

-- O mesmo objeto que a ferramenta entregou ao modelo, para a conversa voltar
-- igual ao recarregar. Mensagem do usuário fica com a lista vazia.
alter table public.chat_messages
  add column cards jsonb not null default '[]'::jsonb;
