# SquadUp Backend — Queue

> Sincronizado com `vision.md` e `roadmap.md` em 2026-07-02. Repositório Git em `https://github.com/GuilhermeFreire7/squadup-back`. **Branch principal de trabalho: `dev`** (não `main` — `main` está atrasada e ainda não recebeu Fase 1/CI). Para o histórico de tarefas concluídas (Fase 1, CI, Fase 2, updates de dependências), ver `progress.md`.

## Em andamento

_Fase 3 implementada e validada localmente (pytest, ruff, black, mypy verdes + smoke test manual via uvicorn) na branch `feature/fase-3-autenticacao`; aguardando revisão/merge em `dev` antes de iniciar a Fase 4 (Perfil de usuário)._

## Bloqueios

- Nenhum bloqueio técnico conhecido. Decisões de stack da Fase 1 já tomadas: `venv` + `requirements.txt`, **SQLModel**, **SQLite** em dev. Hospedagem de deploy (Fase 11 — Railway/Render/Fly.io) ainda sem escolha.
- Compatibilidade fixada: `bcrypt` pinado em `>=4.0,<4.1` no `requirements.txt` — `passlib[bcrypt]==1.7.4` lê `bcrypt.__about__.__version__`, removido em `bcrypt>=4.1`; sem o pin, `hash_password`/`verify_password` quebram em runtime. Reavaliar se `passlib` for atualizado para uma versão que não dependa desse atributo.

## Próxima tarefa — Fase 4: Perfil de usuário

- `GET /users/{id}` (perfil público);
- `GET /users/me` / `PATCH /users/me` (editar perfil, usando `get_current_user` já criado na Fase 3);
- `average_rating` e `matches_played` como campos **derivados** (calculados a partir de `Rating`/`Participant`, nunca armazenados soltos).

## Depois da Fase 4 (backlog, não iniciar ainda)

Seguindo a ordem do `roadmap.md` §14 — cada fase só começa depois que a anterior tiver um endpoint navegável de ponta a ponta:

- Fase 5 — Partidas: listagem, busca e detalhes
- Fase 6 — Criação de partida
- Fase 7 — Participação em partida
- Fase 8 — Mensagens (chat da partida)
- Fase 9 — Avaliação pós-partida (com validação de regra de negócio)
- Fase 10 — Denúncia e moderação (RBAC mínimo)
- Fase 11 — Hardening e integração final com o front

## Dívidas técnicas conhecidas

- **Refresh token não implementado** (Fase 3 entregou só access token de curta duração via `access_token_expire_minutes`). Adiado para a Fase 11 conforme o roadmap original — mas fica registrado aqui para não ser esquecido: hoje, quando o token expira, o único caminho é logar de novo.
- **`main` está atrasada em relação a `dev`** desde a Fase 1 — nenhuma fase ainda foi promovida para `main`. Reavaliar quando/se isso importa (ex.: antes do primeiro deploy real na Fase 11).

## Notas

- Cada fase deve ser desenvolvida em branch própria (a partir de `dev`) e mergeada só depois de consumida com sucesso por uma tela real do front (não apenas via Swagger/Postman) — ver `roadmap.md` §2.
- Regras de negócio críticas a não esquecer quando chegar a hora: vagas/`status` de partida sempre derivados da contagem de `Participant.status == confirmed` (nunca campo solto); avaliação só válida com `match.status == closed` e ambos usuários `confirmed`.
- `email`/`hashed_password`/`role` foram adicionados ao model `User` já na Fase 2 (não estavam no `vision.md` §6 original, que não previa auth) para evitar uma migration extra na Fase 3.
- `app.core.dependencies.get_current_user` (criada na Fase 3) é a dependency padrão para exigir autenticação em qualquer router novo — usar `Depends(get_current_user)` em vez de reimplementar decodificação de JWT.
- Regra `B008` do `ruff` está no ignore list (`pyproject.toml`) por causa do idiom `Depends(...)` do FastAPI — não reverter isso achando que é lint solto.
