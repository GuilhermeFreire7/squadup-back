# SquadUp Backend — Queue

> Sincronizado com `vision.md` e `roadmap.md` em 2026-07-02. Repositório Git inicializado e publicado em `https://github.com/GuilhermeFreire7/squadup-back` (branch `main`). Fase 1 concluída na branch `feature/fase-1-estrutura-inicial` (ainda não mergeada em `main`).

## Em andamento

_Fase 1 implementada e validada localmente nesta branch; aguardando o commit/PR ser revisado e mergeado antes de iniciar a Fase 2 (Modelagem de dados e migrations)._

## Bloqueios

- Nenhum bloqueio técnico conhecido. Decisões de stack da Fase 1 já tomadas: `venv` + `requirements.txt`, **SQLModel**, **SQLite** em dev. Hospedagem de deploy (Fase 11 — Railway/Render/Fly.io) ainda sem escolha.

## Fase 1 — Estrutura inicial do projeto (concluída)

Ordem de execução (ver `roadmap.md` §3):

1. [x] Inicializar projeto FastAPI (`venv` + `requirements.txt`)
2. [x] Definir estrutura de pastas (`app/{models,schemas,routers,services,core,tests}`)
3. [x] Configurar variáveis de ambiente (`.env` + `pydantic-settings`, ver `app/core/config.py`)
4. [x] Configurar banco de dados local (SQLite via `app/core/database.py`)
5. [x] Configurar ORM (SQLModel) e Alembic para migrations (`alembic/env.py` lê `DATABASE_URL` das settings)
6. [x] Configurar testes (`pytest` + `httpx`/`TestClient`, ver `app/tests/test_health.py`)
7. [x] Configurar lint/format (`ruff` + `black`, config em `pyproject.toml`)
8. [x] Configurar CORS liberando o origin do Expo (ver `cors_origins` em `app/core/config.py`)
9. [x] Endpoint de healthcheck (`GET /health`)

**Resultado alcançado:** `uvicorn app.main:app --reload` sobe e `/health` responde `200 {"status":"ok","environment":"development"}`; `pytest` (1 passed), `ruff check` e `black --check` todos verdes; `alembic current` funcional apontando para o SQLite local.

## Próxima tarefa — Fase 2: Modelagem de dados e migrations

- Criar os modelos `User`, `Match`, `Participant`, `Message`, `Rating`, `Report` em `app/models/` (SQLModel), com FKs e enums descritos em `vision.md` §6;
- Registrar os módulos de modelo em `alembic/env.py` (comentário já deixado no arquivo indicando onde importar);
- Gerar a migration inicial via `alembic revision --autogenerate`;
- Criar seed espelhando `../front/src/mocks/*.ts` (mesmos 6 usuários, ~13 partidas).

## Depois da Fase 1 (backlog, não iniciar ainda)

Seguindo a ordem do `roadmap.md` §14 — cada fase só começa depois que a anterior tiver um endpoint navegável de ponta a ponta:

- Fase 2 — Modelagem de dados e migrations (models `User`, `Match`, `Participant`, `Message`, `Rating`, `Report` + seed espelhando `../front/src/mocks/*.ts`)
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

- Cada fase deve ser desenvolvida em branch própria e mergeada só depois de consumida com sucesso por uma tela real do front (não apenas via Swagger/Postman) — ver `roadmap.md` §2.
- Regras de negócio críticas a não esquecer quando chegar a hora: vagas/`status` de partida sempre derivados da contagem de `Participant.status == confirmed` (nunca campo solto); avaliação só válida com `match.status == closed` e ambos usuários `confirmed`.
