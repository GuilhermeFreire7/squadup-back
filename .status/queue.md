# SquadUp Backend — Queue

> Sincronizado com `vision.md` e `roadmap.md` em 2026-07-02. Repositório ainda vazio — nenhum código escrito até o momento (apenas `CLAUDE.md` e `.status/`).

## Em andamento

_Nenhuma tarefa em andamento no momento._

## Bloqueios

- Nenhum bloqueio técnico conhecido. Decisões de stack ainda em aberto (ver `roadmap.md` §1): ORM (SQLModel vs. SQLAlchemy + Pydantic v2), Docker Compose com Postgres vs. SQLite para dev, hospedagem de deploy (Fase 11 — Railway/Render/Fly.io, nenhuma escolha feita ainda).

## Próximas tarefas — Fase 1: Estrutura inicial do projeto

Ordem sugerida de execução (ver `roadmap.md` §3):

1. [ ] Inicializar projeto FastAPI (Poetry ou `venv` + `requirements.txt`)
2. [ ] Definir estrutura de pastas (`app/{models,schemas,routers,services,core,tests}`)
3. [ ] Configurar variáveis de ambiente (`.env` + `pydantic-settings`)
4. [ ] Configurar banco de dados local (Docker Compose com Postgres, ou SQLite para começar)
5. [ ] Configurar ORM (SQLModel ou SQLAlchemy + Pydantic v2) e Alembic para migrations
6. [ ] Configurar testes (`pytest` + `httpx`/`TestClient`)
7. [ ] Configurar lint/format (`ruff` + `black`)
8. [ ] Configurar CORS liberando o origin do Expo (`npm run web`) e do app mobile
9. [ ] Endpoint de healthcheck (`GET /health`)

**Resultado esperado da Fase 1:** servidor FastAPI rodando localmente (`uvicorn app.main:app --reload`), endpoint `/health` respondendo, banco conectado, `pytest` executando (mesmo que só com o teste do healthcheck).

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
