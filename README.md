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
- **Autenticação:** JWT (`PyJWT`) + hashing de senha com `passlib[bcrypt]`
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

JWT (`PyJWT`, HS256) com senha hasheada via `passlib[bcrypt]`:

- `POST /auth/register` — cadastra um usuário (`name`, `email`, `password`, `age`, `location`, `bio?`, `favorite_sports`); retorna `409 EMAIL_ALREADY_REGISTERED` se o e-mail já existir.
- `POST /auth/login` — valida e-mail/senha e retorna `{ access_token, refresh_token, token_type }`; `401 INVALID_CREDENTIALS` em caso de falha.
- `GET /auth/me` — retorna o usuário autenticado a partir do header `Authorization: Bearer <token>`.
- `POST /auth/refresh` — troca um `refresh_token` válido por um novo par `{ access_token, refresh_token }` (rotação: o refresh token usado é revogado); `401 INVALID_REFRESH_TOKEN` se estiver inválido, expirado, revogado ou já utilizado.
- `POST /auth/logout` — revoga um `refresh_token`, encerrando a sessão correspondente; `204` em caso de sucesso, `401 INVALID_REFRESH_TOKEN` se o token já não for válido.

A dependency `app.core.dependencies.get_current_user` decodifica o JWT e carrega o `User`; routers futuros que exigirem autenticação devem reutilizá-la via `Depends`.

O `access_token` tem vida curta (`access_token_expire_minutes`, padrão 24h); o `refresh_token` é um valor aleatório opaco (`secrets.token_urlsafe`), armazenado apenas como hash SHA-256 na tabela `refresh_tokens` (`token_hash`), com vida longa (`refresh_token_expire_days`, padrão 30 dias) e rotação a cada uso — o token anterior é sempre marcado como `revoked` ao ser trocado por um novo par, então reutilizar um refresh token já trocado ou revogado retorna `401 INVALID_REFRESH_TOKEN`.

## Perfil de usuário

- `GET /users/me` — perfil completo do usuário autenticado (`Authorization: Bearer <token>`), incluindo `average_rating` e `matches_played`.
- `PATCH /users/me` — atualiza campos do próprio perfil (`name`, `photo_url`, `age`, `location`, `bio`, `favorite_sports`, `level`); aceita atualização parcial.
- `GET /users/{id}` — perfil público de qualquer usuário (sem `email`/`role`), com as mesmas métricas derivadas.

`average_rating` (média de `Rating.overall`) e `matches_played` (contagem de `Participant.status == confirmed`) são sempre calculados na consulta em `app/services/user_service.py` — nunca armazenados como coluna solta, para não divergirem dos dados reais.

## Partidas

- `GET /matches` — lista partidas com filtros opcionais via query string: `sport`, `date`, `location` (busca parcial, case-insensitive), `level`, `has_open_slots` (só partidas com vagas disponíveis).
- `GET /matches/{id}` — detalhes de uma partida, com `organizer` e `participants` expandidos (perfil público de cada um); `404 MATCH_NOT_FOUND` se não existir.
- `POST /matches` — cria uma partida com o usuário autenticado (`Authorization: Bearer <token>`) como `organizer`; requer `sport`, `title`, `location`, `date`, `time`, `max_participants` (> 0), `level`; `allow_beginners` e `requires_approval` são opcionais.

`confirmed_count` e `available_slots` são sempre calculados em `app/services/match_service.py` a partir de `Participant.status == confirmed` — nunca um campo solto no model `Match`, para não divergir da contagem real de participantes.

## Participação em partida

- `POST /matches/{id}/join` — usuário autenticado solicita participação; cria `Participant` como `confirmed` (partidas sem `requires_approval`) ou `pending` (aguardando aprovação do organizador); `400 MATCH_NOT_JOINABLE` se a partida estiver `closed`/`cancelled`, `400 MATCH_FULL` se não houver vagas e a partida não exigir aprovação, `400 ALREADY_PARTICIPATING` se já houver participação ativa.
- `POST /matches/{id}/leave` — cancela a participação do usuário autenticado; `400 NOT_PARTICIPATING` se não houver participação ativa.
- `POST /matches/{id}/participants/{userId}/approve` — organizador confirma uma solicitação `pending`; `403 NOT_MATCH_ORGANIZER` se o autenticado não for o organizador, `404 PENDING_PARTICIPANT_NOT_FOUND` se não houver solicitação pendente para o usuário, `400 MATCH_FULL` se as vagas já tiverem sido preenchidas.
- `POST /matches/{id}/close` — organizador encerra a partida manualmente (`status → closed`), pré-requisito para o fluxo de avaliação pós-partida; `403 NOT_MATCH_ORGANIZER` se o autenticado não for o organizador, `400 MATCH_ALREADY_RESOLVED` se a partida já estiver `closed`/`cancelled`.

O `status` da partida (`open`/`full`) é recalculado automaticamente a cada join/leave/approve a partir da contagem real de `Participant.status == confirmed` — nunca definido manualmente. `closed` é a única transição manual, disparada exclusivamente pelo organizador via `POST /matches/{id}/close`.

## Mensagens (chat da partida)

- `GET /matches/{id}/messages` — histórico de mensagens em ordem cronológica, paginado via `skip`/`limit` (padrão `limit=50`, máximo `100`).
- `POST /matches/{id}/messages` — envia uma nova mensagem (`text`, não vazio); `created_at` é gerado pelo servidor.

Ambos os endpoints exigem `Authorization: Bearer <token>` e são restritos ao organizador da partida ou a participantes com `Participant.status == confirmed` — `403 NOT_MATCH_PARTICIPANT` caso contrário, `404 MATCH_NOT_FOUND` se a partida não existir. Não há WebSocket nesta fase; o front deve fazer polling/refetch.

Ao criar uma partida (`POST /matches`), o servidor emite automaticamente uma primeira `Message` com `type: "system"` (`sender` = organizador, texto fixo "Partida criada. Bem-vindos!") — o chat da partida nunca começa vazio.

## Avaliação pós-partida

- `POST /matches/{id}/ratings/{userId}` — usuário autenticado avalia outro usuário com os 5 critérios (`punctuality`, `respect`, `behavior`, `presence`, `overall`, cada um de 1 a 5) e `comment` opcional. Regras de negócio aplicadas no servidor: `400 MATCH_NOT_CLOSED` se `match.status != closed`; `400 CANNOT_RATE_SELF` se tentar avaliar a si mesmo; `403 NOT_MATCH_PARTICIPANT` se o avaliador não tinha `Participant.status == confirmed` nessa partida; `400 RATED_USER_NOT_PARTICIPANT` se o avaliado não tinha `confirmed` nessa partida; `400 ALREADY_RATED` se o mesmo par avaliador/avaliado já tiver uma avaliação para essa partida.
- `GET /users/{id}/ratings` — lista as avaliações recebidas por um usuário, mais recentes primeiro, com `rater` e `rated_user` expandidos como perfil público (mesmo padrão de `MessageRead.sender`/`ParticipantRead.user`; `RatingRead` não expõe mais `rated_user_id` solto). `RatingRead.match` também é expandido como `MatchRef` (`id, title, sport, date`) em vez de um `match_id` solto, para o front não precisar de uma segunda chamada para saber a que partida a avaliação se refere.

`average_rating` do perfil (`GET /users/{id}`, `GET /users/me`) é sempre recalculado a partir das linhas de `ratings` — nenhuma avaliação é somada manualmente a um total solto.

Para chegar a `match.status == closed` sem manipular o banco diretamente, use `POST /matches/{id}/close` (ver seção "Participação em partida").

## Denúncia e moderação

- `POST /reports` — usuário autenticado denuncia outro usuário (`reported_user_id`, `reason`, `description`, `match_id` opcional). `400 CANNOT_REPORT_SELF` se tentar denunciar a si mesmo; `404 USER_NOT_FOUND`/`404 MATCH_NOT_FOUND` se o usuário denunciado ou a partida referenciada não existirem. Na resposta (`ReportRead`), o `match_id` de entrada vira `match: MatchRef | null` (`id, title, sport, date`), `null` quando a denúncia não referencia nenhuma partida.
- `GET /reports` — lista todas as denúncias, mais recentes primeiro. Requer `role == admin`; `403 ADMIN_ONLY` caso contrário.
- `PATCH /reports/{id}` — aplica uma ação de moderação (`action`: `archive`, `warn` ou `ban`), atualizando `status` da denúncia (`archived`, `warned`, `banned`). Requer `role == admin`; `400 REPORT_ALREADY_RESOLVED` se a denúncia não estiver mais `pending`; `404 REPORT_NOT_FOUND` se não existir.

RBAC mínimo via campo `role` (`user`/`admin`) em `User`, checado pela dependency `app.core.dependencies.get_current_admin` (reutiliza `get_current_user` e adiciona a verificação de papel). Nenhuma ação de moderação tem efeito colateral sobre a conta do usuário denunciado (ex.: `ban` não bloqueia login) — escopo desta fase é replicar as 3 ações já previstas no protótipo do front, não um sistema de enforcement real.

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

Tabelas definidas em `app/models/` (SQLModel), seguindo o modelo descrito em `vision.md` §6: `User`, `Match`, `Participant` (associativa Match↔User), `Message`, `Rating`, `Report`. `RefreshToken` foi adicionado na Fase 11 (fora do `vision.md` original, que não previa rotação de sessão) para suportar `POST /auth/refresh`/`POST /auth/logout`. Enums compartilhados (esporte, nível, status, etc.) ficam em `app/models/enums.py`.

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
