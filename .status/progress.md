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

## Dependabot — Atualizações de dependências (concluídas e mergeadas)

Mergeadas em `dev` via PR após Fase 1 + CI entrarem em produção:

- pip: `pydantic-settings` (PR #17), `sqlmodel` (PR #16), `ruff` (PR #15), `bandit` (PR #13), `passlib` (PR #11), `python-dotenv` (PR #14), `pip-audit` (PR #12), `httpx` (PR #10)
- GitHub Actions: `codeql-action` (PR #7), `upload-artifact` (PR #6)

**Observabilidade:** nesta etapa o projeto ainda não tem logging estruturado nem métricas em runtime (não existiam antes desta tarefa e não foram inventados agora) — fica registrado como item do roadmap técnico (ver `roadmap.md` §17, "observabilidade") para quando houver serviço rodando de fato. O que o CI garante hoje nessa frente é cobertura de teste mínima visível por PR e checagem de que `alembic` não fica fora de sincronia com os models silenciosamente.
