---
id: "001"
titulo: Fundação, autenticação com Google e deploy
status: aprovado
desafio: [1, 8]
pontos: Deploy e documentação (10) + parte de Segurança e backend (20)
prioridade: P0
---

# 001 — Fundação, autenticação e deploy: requisitos

## Objetivo

Ter cedo um esqueleto publicado de ponta a ponta: front e back hospedados de
graça, login com Google funcionando em produção e o backend validando a
identidade do usuário. Todo o resto é construído em cima disso.

## Histórias

- **H1.1** Como avaliador, quero entrar com minha conta Google sem cadastro
  prévio, para testar a aplicação sem pedir acesso a ninguém.
- **H1.2** Como usuário, quero sair da conta, para encerrar a sessão em um
  computador compartilhado.
- **H1.3** Como desenvolvedor, quero que cada push publique front e back, para
  validar em produção o tempo todo.

## Critérios de aceite (EARS)

- **R1.1** — QUANDO um usuário não autenticado abrir a aplicação, O SISTEMA
  DEVE mostrar a tela de login com uma frase sobre o produto e o botão
  "Entrar com Google".
- **R1.2** — QUANDO o usuário concluir o login com Google pela primeira vez, O
  SISTEMA DEVE criar a conta e levá-lo à lista de análises (login e cadastro
  são o mesmo fluxo).
- **R1.3** — O SISTEMA DEVE aceitar qualquer conta Google (tela de
  consentimento OAuth publicada em "In production", escopos `email` e
  `profile`).
- **R1.4** — QUANDO o usuário clicar em "Sair", O SISTEMA DEVE encerrar a
  sessão no cliente e voltar à tela de login.
- **R1.5** — O backend DEVE validar o JWT do Supabase em cada requisição
  protegida pelo JWKS do projeto, conferindo assinatura, `iss`, `aud` e `exp`,
  sem confiar em dados vindos do front.
- **R1.6** — SE o token estiver ausente, inválido ou expirado, ENTÃO o backend
  DEVE responder 401 sem detalhes internos.
- **R1.7** — O backend DEVE expor `GET /health` público que executa `select 1`
  no banco e responde 200 com status do banco.
- **R1.8** — O front DEVE estar publicado em hospedagem gratuita (Vercel ou
  Cloudflare Pages) e o back em hospedagem gratuita (Render; plano B Hugging
  Face Spaces), sem custo para o avaliador.
- **R1.9** — O repositório DEVE ter `.env.example` para front e back, e nenhum
  segredo versionado.
- **R1.10** — O banco DEVE ter as tabelas `analyses`, `chat_messages` e
  `usage_daily` com RLS ligada (`user_id = auth.uid()`), criadas por migration
  versionada.
- **R1.11** — O CI DEVE rodar lint e testes do backend e o build do front em
  cada push.

## Fora de escopo

- Login por e-mail/senha ou outros provedores.
- Perfis, papéis ou administração de usuários.

## Questões abertas

- Vercel ou Cloudflare Pages para o front? (padrão: Vercel)
