# Back-end Development Guidelines (FastAPI)

## 0. Before Anything Else

Read these files at the start of **every session**, in this order:
1. `.status/vision.md` — what the project is and the real stack
2. `.status/roadmap.md` — technical debt and priorities
3. `.status/queue.md` — active tasks and blockers

Update `.status/queue.md` when starting or finishing a task. Run `/update-status` at the end of the session to sync `progress.md`, `roadmap.md`, and `queue.md`.

---

## 1. Context & State
- **Always consult the `.status/` folder (vision, roadmap, queue) before proposing changes.

## 2. Architecture & Patterns
- **Standard:** FastAPI with Pydantic v2 for schemas and SQLAlchemy/SQLModel for ORM.
- **Structure:** Follow a modular structure (routers, services, models, schemas, core).
- **Dependency Injection:** Use FastAPI's `Depends` for database sessions and authentication.

## 3. Data Integrity & API
- **Schemas:** Every endpoint must have explicit `response_model` and Pydantic schemas for input validation.
- **Type Hinting:** 100% type coverage is mandatory. Use `mypy` for static analysis.
- **Migrations:** All database changes must be handled via Alembic. Never update the DB manually.

## 4. Engineering Quality
- **Definition of Done:** Every feature must include Pytest unit/integration tests with high coverage.
- **Complexity:** Functions should perform a single responsibility (SOLID). Break down complex business logic into "Service" layers.
- **Performance:** Use `async/await` properly. For heavy CPU tasks, use BackgroundTasks or Celery.
- **Standardized Errors:** Every error must return a unique 'SHORT_CODE' and a clear explanation.
- **Swagger Quality:** Use Pydantic `Field(examples=[...])` and FastAPI descriptions to keep API docs production-ready.

## 5. Security & LGPD
- **Auth:** Implement OAuth2 with JWT. Password hashing must use Passlib/Bcrypt.
- **Privacy:** Implement data masking for PII in logs. Ensure GDPR/LGPD compliance (Data deletion/Anonymization endpoints).
- **Validation:** Sanitize all inputs to prevent SQL Injection and NoSQL Injection.

## 6. Workflow
- **Commits:** Follow **Conventional Commits** (feat:, fix:, docs:, chore:).
- **Documentation:** Keep Docstrings (Google/Sphinx style) updated. Ensure Swagger/Redoc UI is clean and descriptive.
- **Validation:** Run `pytest` and `ruff/flake8` before concluding any task.
- **Error Debugging Protocol: If a task fails or a bug is found, do not attempt to fix it immediately. First, gather logs (terminal output, browser console, or tailing the server logs). Explain the root cause before proposing a solution.