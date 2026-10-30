-- Resultado da análise e arquivos (specs/002-processamento-classificacao, T2.10).

-- Justificativa técnica estruturada (R2.18): devolvida no GET /analyses/{id}.
alter table public.analyses add column rationale jsonb;

-- Bucket privado (R6.4). Só o backend acessa, com a service role; o front
-- recebe URLs assinadas de até 5 minutos. Sem políticas em storage.objects
-- para anon/authenticated, nenhum usuário lê ou grava direto.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'analyses',
  'analyses',
  false,
  25 * 1024 * 1024,
  array['image/tiff', 'image/png', 'application/geo+json']
)
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;
