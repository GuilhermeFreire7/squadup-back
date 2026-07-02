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

## Fase 2 — Modelagem de dados e migrations (concluída, aguardando merge)

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

**Branch:** `feature/fase-2-modelagem-dados`, cortada de `dev`, ainda não mergeada.

## Dependabot — Atualizações de dependências (concluídas e mergeadas)

Mergeadas em `dev` via PR após Fase 1 + CI entrarem em produção:

- pip: `pydantic-settings` (PR #17), `sqlmodel` (PR #16), `ruff` (PR #15), `bandit` (PR #13), `passlib` (PR #11), `python-dotenv` (PR #14), `pip-audit` (PR #12), `httpx` (PR #10)
- GitHub Actions: `codeql-action` (PR #7), `upload-artifact` (PR #6)

**Observabilidade:** nesta etapa o projeto ainda não tem logging estruturado nem métricas em runtime (não existiam antes desta tarefa e não foram inventados agora) — fica registrado como item do roadmap técnico (ver `roadmap.md` §17, "observabilidade") para quando houver serviço rodando de fato. O que o CI garante hoje nessa frente é cobertura de teste mínima visível por PR e checagem de que `alembic` não fica fora de sincronia com os models silenciosamente.
