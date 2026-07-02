# SquadUp — Backend

API do **SquadUp**, app mobile para conectar pessoas interessadas em praticar esportes coletivos (futebol, vôlei, basquete). Este repositório é o backend que substitui os dados mockados do front-end (React Native + Expo) por persistência e autenticação reais.

Contexto completo do produto e do roadmap técnico em [`.status/`](.status/):
- [`vision.md`](.status/vision.md) — visão do produto e modelo de dados
- [`roadmap.md`](.status/roadmap.md) — fases de desenvolvimento e status de execução
- [`queue.md`](.status/queue.md) — tarefas ativas e próximos passos
- [`progress.md`](.status/progress.md) — histórico de tarefas concluídas

> **Branch de trabalho principal: `dev`.** A branch `main` recebe merges apenas quando o time decidir promover uma versão estável.

## Stack

- **API:** Python 3.12 + [FastAPI](https://fastapi.tiangolo.com/)
- **ORM / Schemas:** [SQLModel](https://sqlmodel.tiangolo.com/) (SQLAlchemy + Pydantic v2)
- **Banco de dados:** SQLite em desenvolvimento, PostgreSQL previsto para produção
- **Migrations:** [Alembic](https://alembic.sqlalchemy.org/)
- **Autenticação:** JWT (`python-jose`) + hashing de senha com `passlib[bcrypt]`
- **Testes:** `pytest` + `pytest-cov` + `httpx`/`TestClient`
- **Qualidade:** `ruff` (lint), `black` (format), `mypy` (type-check estrito)
- **Segurança:** `bandit` (SAST), `pip-audit` (CVEs em dependências), CodeQL e gitleaks no CI

## Setup local

```bash
python -m venv venv
source venv/Scripts/activate   # Windows (Git Bash) — use `venv\Scripts\activate` no cmd/PowerShell
pip install -r requirements.txt
cp .env.example .env
```

## Rodando a aplicação

```bash
uvicorn app.main:app --reload
```

- Healthcheck: `GET http://127.0.0.1:8000/health`
- Documentação interativa: `http://127.0.0.1:8000/docs` (Swagger) e `/redoc`

## Autenticação

JWT (`python-jose`, HS256) com senha hasheada via `passlib[bcrypt]`:

- `POST /auth/register` — cadastra um usuário (`name`, `email`, `password`, `age`, `location`, `bio?`, `favorite_sports`); retorna `409 EMAIL_ALREADY_REGISTERED` se o e-mail já existir.
- `POST /auth/login` — valida e-mail/senha e retorna `{ access_token, token_type }`; `401 INVALID_CREDENTIALS` em caso de falha.
- `GET /auth/me` — retorna o usuário autenticado a partir do header `Authorization: Bearer <token>`.

A dependency `app.core.dependencies.get_current_user` decodifica o JWT e carrega o `User`; routers futuros que exigirem autenticação devem reutilizá-la via `Depends`.

## Perfil de usuário

- `GET /users/me` — perfil completo do usuário autenticado (`Authorization: Bearer <token>`), incluindo `average_rating` e `matches_played`.
- `PATCH /users/me` — atualiza campos do próprio perfil (`name`, `photo_url`, `age`, `location`, `bio`, `favorite_sports`, `level`); aceita atualização parcial.
- `GET /users/{id}` — perfil público de qualquer usuário (sem `email`/`role`), com as mesmas métricas derivadas.

`average_rating` (média de `Rating.overall`) e `matches_played` (contagem de `Participant.status == confirmed`) são sempre calculados na consulta em `app/services/user_service.py` — nunca armazenados como coluna solta, para não divergirem dos dados reais.

## Partidas

- `GET /matches` — lista partidas com filtros opcionais via query string: `sport`, `date`, `location` (busca parcial, case-insensitive), `level`, `has_open_slots` (só partidas com vagas disponíveis).
- `GET /matches/{id}` — detalhes de uma partida, com `organizer` e `participants` expandidos (perfil público de cada um); `404 MATCH_NOT_FOUND` se não existir.

`confirmed_count` e `available_slots` são sempre calculados em `app/services/match_service.py` a partir de `Participant.status == confirmed` — nunca um campo solto no model `Match`, para não divergir da contagem real de participantes.

## Testes e qualidade

```bash
pytest                                    # testes + relatório de cobertura (gate mínimo: 80%)
ruff check .                              # lint
black --check .                           # formatação
mypy app                                  # checagem de tipos estrita
```

## Segurança

```bash
bandit -c pyproject.toml -r app --exclude app/tests -ll   # SAST
pip-audit -r requirements.txt                              # vulnerabilidades em dependências
```

Todas essas checagens (qualidade + segurança) também rodam automaticamente em CI a cada push/PR — ver [`.github/workflows/`](.github/workflows/).

## Modelo de dados

Tabelas definidas em `app/models/` (SQLModel), seguindo o modelo descrito em `vision.md` §6: `User`, `Match`, `Participant` (associativa Match↔User), `Message`, `Rating`, `Report`. Enums compartilhados (esporte, nível, status, etc.) ficam em `app/models/enums.py`.

Regras de negócio que devem ser aplicadas na camada de serviço (não como colunas soltas): vagas/`status` de partida sempre derivados da contagem de `Participant.status == confirmed`; avaliação só válida com `match.status == closed` e ambos usuários `confirmed`.

## Migrations

```bash
alembic revision --autogenerate -m "descrição da mudança"
alembic upgrade head
```

A URL do banco é lida de `DATABASE_URL` (`.env`), a mesma fonte de verdade usada pela aplicação — ver `alembic/env.py` e `app/core/config.py`.

## Seed de dados de exemplo

```bash
python -m app.seed
```

Popula o banco local com os mesmos dados de exemplo do protótipo do front (`../squadup-app/src/mocks/*.ts`): 6 usuários + 1 usuário de sistema (`system`, autor das mensagens automáticas do chat), 13 partidas, participações, mensagens, avaliações e denúncias. Idempotente — não faz nada se `user-1` já existir no banco. Senha de todos os usuários de seed: `changeme123` (placeholder de desenvolvimento, nunca usar em produção).

## Estrutura de pastas

```
app/
├── core/       # configuração (settings), conexão com banco
├── models/     # modelos SQLModel (tabelas)
├── schemas/    # schemas Pydantic de entrada/saída da API
├── routers/    # endpoints FastAPI
├── services/   # regras de negócio
└── tests/      # testes pytest
alembic/        # migrations do banco de dados
.status/        # visão de produto, roadmap técnico e fila de tarefas
```

## Workflow de desenvolvimento

Cada fase do [`roadmap.md`](.status/roadmap.md) é desenvolvida em branch própria e só é mergeada depois de validada — ver `roadmap.md` §2 e `CLAUDE.md` para as diretrizes completas de desenvolvimento (padrões de código, commits, segurança e LGPD).
