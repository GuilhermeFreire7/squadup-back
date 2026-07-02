# SquadUp Backend — Queue

> Sincronizado com `vision.md` e `roadmap.md` em 2026-07-02. Repositório Git em `https://github.com/GuilhermeFreire7/squadup-back`. **Branch principal de trabalho: `dev`** (não `main` — `main` está atrasada e ainda não recebeu Fase 1/CI). Para o histórico de tarefas concluídas (Fase 1, CI, updates de dependências), ver `progress.md`.

## Em andamento

_Nenhuma tarefa em andamento. Pronto para iniciar a Fase 2 (Modelagem de dados e migrations) a partir de `dev`._

## Bloqueios

- Nenhum bloqueio técnico conhecido. Decisões de stack da Fase 1 já tomadas: `venv` + `requirements.txt`, **SQLModel**, **SQLite** em dev. Hospedagem de deploy (Fase 11 — Railway/Render/Fly.io) ainda sem escolha.

## Próxima tarefa — Fase 2: Modelagem de dados e migrations

- Criar os modelos `User`, `Match`, `Participant`, `Message`, `Rating`, `Report` em `app/models/` (SQLModel), com FKs e enums descritos em `vision.md` §6;
- Registrar os módulos de modelo em `alembic/env.py` (comentário já deixado no arquivo indicando onde importar);
- Gerar a migration inicial via `alembic revision --autogenerate`;
- Criar seed espelhando `../front/src/mocks/*.ts` (mesmos 6 usuários, ~13 partidas).

## Depois da Fase 2 (backlog, não iniciar ainda)

Seguindo a ordem do `roadmap.md` §14 — cada fase só começa depois que a anterior tiver um endpoint navegável de ponta a ponta:

- Fase 3 — Autenticação (`/auth/register`, `/auth/login`, `/auth/me`, JWT)
- Fase 4 — Perfil de usuário
- Fase 5 — Partidas: listagem, busca e detalhes
- Fase 6 — Criação de partida
- Fase 7 — Participação em partida
- Fase 8 — Mensagens (chat da partida)
- Fase 9 — Avaliação pós-partida (com validação de regra de negócio)
- Fase 10 — Denúncia e moderação (RBAC mínimo)
- Fase 11 — Hardening e integração final com o front

## Notas

- Cada fase deve ser desenvolvida em branch própria (a partir de `dev`) e mergeada só depois de consumida com sucesso por uma tela real do front (não apenas via Swagger/Postman) — ver `roadmap.md` §2.
- Regras de negócio críticas a não esquecer quando chegar a hora: vagas/`status` de partida sempre derivados da contagem de `Participant.status == confirmed` (nunca campo solto); avaliação só válida com `match.status == closed` e ambos usuários `confirmed`.
