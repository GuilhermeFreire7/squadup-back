# SquadUp — Backend

API do **SquadUp**, app mobile para conectar pessoas interessadas em praticar esportes coletivos (futebol, vôlei, basquete). Este repositório é o backend que substitui os dados mockados do front-end (React Native + Expo) por persistência e autenticação reais.

Contexto completo do produto e do roadmap técnico em [`.status/`](.status/):
- [`vision.md`](.status/vision.md) — visão do produto e modelo de dados
- [`roadmap.md`](.status/roadmap.md) — fases de desenvolvimento e status de execução
- [`queue.md`](.status/queue.md) — tarefas ativas e próximos passos

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

## Migrations

```bash
alembic revision --autogenerate -m "descrição da mudança"
alembic upgrade head
```

A URL do banco é lida de `DATABASE_URL` (`.env`), a mesma fonte de verdade usada pela aplicação — ver `alembic/env.py` e `app/core/config.py`.

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
