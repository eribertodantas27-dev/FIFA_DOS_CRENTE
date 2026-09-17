# FC Championship Python 2.0 — Render

Sistema Flask responsivo para administrar campeonato de FIFA/EA FC pelo celular.

## Recursos
- inscrições públicas;
- aprovação e distribuição em grupos A-H;
- seleção da fase atual;
- lançamento/exclusão de placares;
- classificação automática na fase de grupos (J, V, E, D, GP, GC, SG, PTS);
- PostgreSQL para dados persistentes;
- `/health` para teste;
- pronto para Render com `render.yaml`.

## Publicar no Render
1. Envie esta pasta para um repositório GitHub.
2. No Render, escolha **New > Blueprint** e selecione o repositório.
3. O `render.yaml` cria o serviço web e o PostgreSQL.
4. Defina a variável secreta `ADMIN_PASSWORD` no serviço.
5. Aguarde o deploy e abra a URL do serviço no Chrome ou Safari.

### Alternativa manual
Build: `pip install -r requirements.txt`
Start: `gunicorn app:app`
Variáveis: `SECRET_KEY`, `ADMIN_PASSWORD`, `DATABASE_URL` (URL do PostgreSQL).

## Login
A senha padrão local é `1234`; em produção, defina `ADMIN_PASSWORD` no Render.

## Observação
O banco PostgreSQL é a opção adequada para manter os dados do campeonato entre celulares e reinicializações do serviço. O próximo passo pode incluir autenticação de administrador mais forte, mata-mata automático e edição de partidas.
