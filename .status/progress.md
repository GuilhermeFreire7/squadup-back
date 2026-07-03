# SquadUp Backend — Progress Log

> Histórico de tarefas concluídas. Para o estado ativo e próxima tarefa, ver `queue.md`. Para o plano completo, ver `roadmap.md`.

## Fase 1 — Estrutura inicial do projeto (concluída e mergeada)

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

**Merge:** implementado na branch `feature/fase-1-estrutura-inicial` (commit `33f0ea6`), mergeado em `dev`.

## CI — Qualidade e Segurança (concluído e mergeado)

Adicionado em `.github/` (branch `feature/ci-pipelines`, commit `95700bd`), sem ser uma fase numerada do roadmap — infraestrutura transversal que passa a valer a partir de agora:

- `.github/workflows/ci.yml`: job `quality` (ruff, black --check, mypy strict, pytest com cobertura mínima de 80% via `pytest-cov`, upload do `coverage.xml` como artifact) + job `alembic-check` (`alembic upgrade head` e `alembic check` para pegar migration faltante antes do merge);
- `.github/workflows/security.yml`: `bandit` (SAST, exclui `app/tests`), `pip-audit` (CVEs em dependências, também roda semanalmente via `schedule`), `CodeQL` (análise estática do GitHub) e `gitleaks` (varredura de segredos no diff e no histórico do PR);
- `.github/dependabot.yml`: atualizações semanais de dependências pip e GitHub Actions;
- `.gitleaks.toml`: allowlist só para o placeholder `change-me-in-.env` do `.env.example`, para não gerar falso positivo;
- `pyproject.toml` ganhou seções `[tool.mypy]` (strict, com override para `app/tests` e `alembic`), `[tool.bandit]` e `[tool.coverage.run]`; `requirements.txt` ganhou `pytest-cov`, `mypy`, `bandit`, `pip-audit`;
- Corrigido durante a validação: `pytest` estava pinado em `>=8.3` (vulnerável a `CVE-2025-71176`, corrigido só na 9.0.3) e `black` em `<25.0` (vulnerável a `CVE-2026-32274`, corrigido na 26.3.1) — ambos os pisos foram subidos e a suíte revalidada (`pytest 9.1.1`, `black 26.5.1`) sem quebras.

**Merge:** mergeado em `dev`.

## Fase 2 — Modelagem de dados e migrations (concluída e mergeada)

Ordem de execução (ver `roadmap.md` §4):

1. [x] Criar os modelos `User`, `Match`, `Participant`, `Message`, `Rating`, `Report` em `app/models/` (SQLModel), com FKs e enums (`app/models/enums.py`) descritos em `vision.md` §6;
2. [x] Registrar os módulos de modelo em `alembic/env.py` (`import app.models`);
3. [x] Gerar a migration inicial via `alembic revision --autogenerate` (`alembic/versions/70043fe6862c_create_initial_tables.py`);
4. [x] Criar seed espelhando `../squadup-app/src/mocks/*.ts` (`app/seed.py`) — mesmos 6 usuários + 1 usuário de sistema, 13 partidas, participações, mensagens, avaliações e denúncias.

**Decisões tomadas além do escopo original do `vision.md` §6:**

- `User` ganhou `email`, `hashed_password` e `role` (não previstos no `vision.md`, que não cobria auth) para não exigir uma migration extra na Fase 3. `role` usa o enum `UserRole` (`user`/`admin`), preparando o RBAC mínimo da Fase 10.
- `average_rating` e `matches_played` **não** são colunas em `User` — permanecem como valores derivados a calcular na camada de serviço (Fase 4), conforme `roadmap.md` §6, para não haver dado solto que possa divergir da realidade.
- `Message.sender_id` referencia um usuário `system` real (criado no seed) em vez de aceitar `NULL`/string livre, para manter a FK íntegra — o front usa `senderId: "system"` como convenção nos mocks.
- Criado `app/core/security.py` com `hash_password`/`verify_password` (Passlib + bcrypt) já na Fase 2, para o seed poder gerar senhas hasheadas; será reaproveitado sem mudanças pela Fase 3.

**Bug corrigido durante a validação:** `passlib[bcrypt]==1.7.4` lê `bcrypt.__about__.__version__` para detectar a versão do backend; esse atributo foi removido em `bcrypt>=4.1` (o pip instalou `bcrypt==5.0.0` por padrão), causando falha silenciosa de truncamento de senha (`ValueError: password cannot be longer than 72 bytes`) em qualquer chamada de hash. Corrigido pinando `bcrypt>=4.0,<4.1` em `requirements.txt` — repetição do mesmo padrão de incompatibilidade entre libs de auth/hash já visto com `pytest`/`black` na Fase 1/CI.

**Resultado alcançado:** `alembic upgrade head` cria as 6 tabelas (`users`, `matches`, `messages`, `participants`, `ratings`, `reports`) mais `alembic_version`; `alembic check` não detecta divergência entre models e migration; `python -m app.seed` popula 7 usuários (6 + sistema), 13 partidas, 43 participações, 15 mensagens, 7 avaliações e 4 denúncias, com contagens batendo exatamente com os mocks do front; `pytest` (10 passed, 94.55% cobertura, gate de 80% ok), `ruff check`, `black --check`, `mypy app` (strict) e `bandit` todos verdes.

**Branch:** `feature/fase-2-modelagem-dados`, cortada de `dev`, mergeada via PR #18.

## Fase 3 — Autenticação (concluída)

Ordem de execução (ver `roadmap.md` §5):

1. [x] `POST /auth/register` — cria usuário com senha hasheada (reaproveitando `hash_password` da Fase 2), rejeita e-mail duplicado com `409 EMAIL_ALREADY_REGISTERED`;
2. [x] `POST /auth/login` — valida e-mail/senha e retorna JWT (`python-jose`, HS256, expiração via `access_token_expire_minutes`), erro `401 INVALID_CREDENTIALS` para credenciais inválidas;
3. [x] `GET /auth/me` — retorna o usuário autenticado a partir do token (`OAuth2PasswordBearer` apontando para `/auth/login`);
4. [x] `app/core/dependencies.py::get_current_user` — dependency reutilizável para os demais routers decodificarem o JWT e carregarem o `User`;
5. [ ] Refresh token — adiado para a Fase 11, conforme já previsto no `roadmap.md`.

**Decisões tomadas:**

- `email-validator` adicionado a `requirements.txt` (dependência exigida pelo `EmailStr` do Pydantic, usado em `RegisterRequest`/`LoginRequest`), junto com `types-python-jose` para o `mypy` estrito não reclamar de stubs faltando (mesmo padrão do `types-passlib` já usado).
- Regra `B008` do `ruff` (bloqueava `Depends(...)` em default de argumento) precisou ser adicionada à lista de ignore em `pyproject.toml` — é o idiom padrão e obrigatório do FastAPI, não um bug real.
- `UserRead` nunca expõe `hashed_password`; testado explicitamente em `test_auth.py`.
- Fixture `client` adicionada em `app/tests/conftest.py`, com banco SQLite in-memory isolado por teste via `dependency_overrides` de `get_session` — necessário porque `test_health.py` usa um `TestClient` global que compartilha o banco real (`squadup.db`), o que quebraria isolamento entre testes de auth.

**Resultado alcançado:** `pytest` (18 passed, 96.60% cobertura), `ruff check`, `black --check` e `mypy app` (strict) todos verdes; fluxo validado manualmente ponta a ponta com `uvicorn` local (`register` → `login` retorna JWT → `/auth/me` com token retorna `200`, sem token retorna `401`).

**Branch:** `feature/fase-3-autenticacao`, cortada de `dev`.

## Fase 4 — Perfil de usuário (concluída)

Ordem de execução (ver `roadmap.md` §6):

1. [x] `GET /users/{id}` — perfil público (`PublicProfileRead`: sem `email`/`role`), `404 USER_NOT_FOUND` se o usuário não existir;
2. [x] `GET /users/me` / `PATCH /users/me` — perfil completo (`MyProfileRead`) e edição parcial do próprio usuário, reutilizando `Depends(get_current_user)` da Fase 3;
3. [x] `average_rating` (média de `Rating.overall`) e `matches_played` (contagem de `Participant.status == confirmed`) calculados em `app/services/user_service.py` a cada request — nunca armazenados como coluna solta.

**Decisões tomadas:**

- Dois schemas de leitura distintos (`PublicProfileRead` e `MyProfileRead`, este último estendendo o primeiro com `email`/`role`) para impedir vazamento de dados privados no perfil público — não reaproveitou `UserRead` da Fase 3 porque esse schema não tem os campos derivados.
- `UserUpdate` usa todos os campos opcionais e `model_dump(exclude_unset=True)` no service, para suportar atualização parcial via `PATCH` sem sobrescrever campos não enviados.
- Rota `/users/me` declarada antes de `/users/{user_id}` no router — ordem de registro do FastAPI, senão `"me"` seria capturado como `user_id`.

**Resultado alcançado:** `pytest` (23 passed, 97.13% cobertura), `ruff check`, `black --check` e `mypy app` (strict) todos verdes; fluxo validado manualmente ponta a ponta com `uvicorn` local (`register` → `login` → `GET /users/me` com métricas derivadas → `PATCH /users/me` aplica mudança parcial → `GET /users/{id}` de outro usuário retorna perfil público sem `email`/`role`).

**Branch:** `feature/fase-4-perfil-usuario`, cortada de `dev`.

## Fase 5 — Partidas: listagem, busca e detalhes (concluída)

Ordem de execução (ver `roadmap.md` §7):

1. [x] `GET /matches` — lista com filtros de query string: `sport`, `date`, `location` (busca parcial case-insensitive via `LOWER(...) LIKE`), `level`, `has_open_slots`;
2. [x] `GET /matches/{id}` — detalhe com `organizer` e `participants` expandidos (cada participante como `PublicProfileRead` + `status`), `404 MATCH_NOT_FOUND` se não existir;
3. [x] `confirmed_count`/`available_slots` calculados em `app/services/match_service.py` a partir de `Participant.status == confirmed` — nunca campo solto no model `Match`.

**Decisões tomadas:**

- Filtro `has_open_slots` é aplicado em memória (após calcular `available_slots` para cada partida), não em SQL — mantém o cálculo de vagas em um único lugar (`build_match_read`) em vez de duplicar a lógica de contagem numa subquery.
- `MatchDetailRead` estende `MatchRead` adicionando `organizer`/`participants`, mesmo padrão de composição de schemas usado em `PublicProfileRead`/`MyProfileRead` na Fase 4.
- Nomes dos campos de query `date`/`time` no schema colidiam com os tipos `datetime.date`/`datetime.time` na anotação — resolvido importando como `date_`/`time_` (`PydanticUserError: unevaluable-type-annotation`).

**Resultado alcançado:** `pytest` (30 passed, 97.19% cobertura), `ruff check`, `black --check` e `mypy app` (strict) todos verdes; fluxo validado manualmente com `uvicorn` local sobre o banco de seed (`GET /matches?sport=football&has_open_slots=true` e `GET /matches/match-1` retornando dados corretos, incluindo organizador e participantes expandidos).

**Branch:** `feature/fase-5-partidas`, cortada de `dev`.

## Dependabot — Atualizações de dependências (concluídas e mergeadas)

Mergeadas em `dev` via PR após Fase 1 + CI entrarem em produção:

- pip: `pydantic-settings` (PR #17), `sqlmodel` (PR #16), `ruff` (PR #15), `bandit` (PR #13), `passlib` (PR #11), `python-dotenv` (PR #14), `pip-audit` (PR #12), `httpx` (PR #10)
- GitHub Actions: `codeql-action` (PR #7), `upload-artifact` (PR #6)

**Observabilidade:** nesta etapa o projeto ainda não tem logging estruturado nem métricas em runtime (não existiam antes desta tarefa e não foram inventados agora) — fica registrado como item do roadmap técnico (ver `roadmap.md` §17, "observabilidade") para quando houver serviço rodando de fato. O que o CI garante hoje nessa frente é cobertura de teste mínima visível por PR e checagem de que `alembic` não fica fora de sincronia com os models silenciosamente.

## Fase 6 — Criação de partida (concluída e mergeada)

Ordem de execução (ver `roadmap.md` §8):

1. [x] `POST /matches` — cria partida com o usuário autenticado (`Depends(get_current_user)`, Fase 3) como `organizer_id`;
2. [x] Validação de payload via `MatchCreate` (Pydantic): `max_participants` > 0, `title`/`location` não vazios, `sport`/`level` restritos aos enums, `allow_beginners`/`requires_approval` opcionais com default.

**Decisões tomadas:**

- `create_match` em `app/services/match_service.py` reaproveita `build_match_read` (já existente da Fase 5) para retornar `confirmed_count`/`available_slots` calculados, em vez de montar a resposta manualmente — mantém o cálculo de vagas em um único lugar.
- Nenhum schema novo de leitura foi necessário: `MatchRead` (Fase 5) já cobre o retorno de `POST /matches`.

**Resultado alcançado:** `pytest` (36 passed, cobertura acima do gate de 80%), `ruff check`, `black --check` e `mypy app` (strict) todos verdes; fluxo validado manualmente com `uvicorn` local (`register` → `login` → `POST /matches` com token retorna a partida criada com `organizer_id` correto e aparece em `GET /matches` imediatamente; sem token retorna `401`; payload inválido retorna `422`).

**Branch:** `feature/fase-6-criacao-partida`, cortada de `dev`, mergeada via PR #22 (commit `fff5490`).

## Fase 7 — Participação em partida (concluída e mergeada)

Ordem de execução (ver `roadmap.md` §9):

1. [x] `POST /matches/{id}/join` — cria `Participant` como `confirmed` (partida sem `requires_approval` e com vaga) ou `pending` (partida com `requires_approval`); rejeita com `400 MATCH_NOT_JOINABLE` se a partida estiver `closed`/`cancelled`, `400 MATCH_FULL` se não houver vaga e não exigir aprovação, `400 ALREADY_PARTICIPATING` se já houver participação ativa;
2. [x] `POST /matches/{id}/leave` — cancela a participação do usuário autenticado (`400 NOT_PARTICIPATING` se não houver participação ativa);
3. [x] `POST /matches/{id}/participants/{userId}/approve` — organizador confirma uma solicitação `pending` (`403 NOT_MATCH_ORGANIZER` se o autenticado não for o organizador, `404 PENDING_PARTICIPANT_NOT_FOUND` se não houver solicitação pendente, `400 MATCH_FULL` se as vagas já tiverem sido preenchidas);
4. [x] `status` da partida (`open`/`full`) recalculado automaticamente após join/leave/approve, a partir da contagem real de `Participant.status == confirmed` (`_sync_match_status` em `app/services/match_service.py`) — nunca um campo definido manualmente.

**Bug corrigido durante a validação:** a checagem inicial de "partida cheia" no `join_match` comparava `match.status == MatchStatus.FULL` — um campo que só é sincronizado por join/leave/approve reais. Uma partida criada com vagas já esgotadas por outro caminho (fixture de teste, seed, migração de dados) nunca teria esse campo atualizado, permitindo join indevido. Corrigido para comparar a contagem real de confirmados (`get_confirmed_count(...) >= match.max_participants`) em vez do campo `status` — mesmo princípio de "nunca confiar em campo solto" já aplicado a `confirmed_count`/`available_slots` na Fase 5.

**Resultado alcançado:** `pytest` (49 passed, 96.96% cobertura), `ruff check`, `black --check` e `mypy app` (strict) todos verdes; fluxo validado manualmente com `uvicorn` local (join simples confirma e preenche a última vaga marcando `full`; leave libera a vaga e volta a `open`; join com `requires_approval=true` fica `pending`, e `approve` do organizador confirma).

**Branch:** `feature/fase-7-participacao-partida`, cortada de `dev`, mergeada via PR #23 (commit `95c13e2`).

## Fase 8 — Mensagens (chat da partida) (implementada)

Ordem de execução (ver `roadmap.md` §10):

1. [x] `GET /matches/{id}/messages` — histórico de mensagens em ordem cronológica (`ORDER BY created_at`), paginado via `skip`/`limit` (`limit` padrão `50`, teto `100`);
2. [x] `POST /matches/{id}/messages` — cria mensagem com `sender_id` do usuário autenticado e `created_at` gerado pelo servidor (`default_factory` do model `Message`, já existente desde a Fase 2);
3. [x] WebSocket não implementado — fora do escopo desta fase, conforme `roadmap.md` §10.

**Decisão tomada além do escopo literal do `vision.md` §6 (Message):** ambos os endpoints exigem que o usuário autenticado seja o organizador da partida ou um participante com `Participant.status == confirmed` (`_ensure_can_access_chat` em `app/services/message_service.py`), retornando `403 NOT_MATCH_PARTICIPANT` caso contrário — o `vision.md` não especificava essa regra de acesso, mas o chat da partida não faz sentido aberto a qualquer usuário autenticado da plataforma. `MessageRead` expande `sender` como `PublicProfileRead` (mesmo padrão de `ParticipantRead` na Fase 5), em vez de expor só `sender_id`, para o front poder renderizar nome/avatar no chat sem uma segunda chamada.

**Resultado alcançado:** `pytest` (60 passed, 97.25% cobertura), `ruff check`, `black --check` e `mypy app` (strict) todos verdes; fluxo validado manualmente com `uvicorn` local (organizador envia e lista mensagens; usuário sem participação recebe `403 NOT_MATCH_PARTICIPANT`; após `join` bem-sucedido, o mesmo usuário consegue enviar mensagem).

**Branch:** `feature/fase-8-mensagens`, cortada de `dev`, commit `4eecaa4`, aguardando revisão/merge.

**Branch:** `feature/fase-7-participacao-partida`, cortada de `dev`.
