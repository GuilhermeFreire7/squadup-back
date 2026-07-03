# SquadUp Backend — Queue

> Sincronizado com `vision.md` e `roadmap.md` em 2026-07-03. Repositório Git em `https://github.com/GuilhermeFreire7/squadup-back`. **Branch principal de trabalho: `dev`** (não `main` — `main` está atrasada e ainda não recebeu Fase 1/CI). Para o histórico de tarefas concluídas (Fase 1 a 8, CI, updates de dependências), ver `progress.md`.

## Em andamento

_Fase 8 (Mensagens) implementada e validada localmente (60 testes pytest, ruff, black, mypy verdes + smoke test manual via uvicorn com fluxos de envio/listagem e checagem de acesso) na branch `feature/fase-8-mensagens`, commit `4eecaa4`; aguardando revisão/merge em `dev` antes de iniciar a Fase 9 (Avaliação pós-partida). Ver `progress.md` para o detalhamento completo._

## Bloqueios

- Nenhum bloqueio técnico conhecido. Decisões de stack da Fase 1 já tomadas: `venv` + `requirements.txt`, **SQLModel**, **SQLite** em dev. Hospedagem de deploy (Fase 11 — Railway/Render/Fly.io) ainda sem escolha.
- Compatibilidade fixada: `bcrypt` pinado em `>=4.0,<4.1` no `requirements.txt` — `passlib[bcrypt]==1.7.4` lê `bcrypt.__about__.__version__`, removido em `bcrypt>=4.1`; sem o pin, `hash_password`/`verify_password` quebram em runtime. Reavaliar se `passlib` for atualizado para uma versão que não dependa desse atributo.

## Próxima tarefa — Fase 9: Avaliação pós-partida

- `POST /matches/{id}/ratings/{userId}` com os 5 critérios (`punctuality`, `respect`, `behavior`, `presence`, `overall`);
- `GET /users/{id}/ratings` (avaliações recebidas, para exibir no perfil);
- Validação de regra de negócio no servidor: só é possível avaliar se `match.status == closed` e tanto o avaliador quanto o avaliado estavam `confirmed` nessa partida.
- Cuidado (ver lição da Fase 7 abaixo): `average_rating` do perfil já é derivado corretamente em `app/services/user_service.py::get_average_rating` desde a Fase 4 — não introduzir um campo solto ao adicionar a validação desta fase.

## Depois da Fase 9 (backlog, não iniciar ainda)

Seguindo a ordem do `roadmap.md` §14 — cada fase só começa depois que a anterior tiver um endpoint navegável de ponta a ponta:

- Fase 10 — Denúncia e moderação (RBAC mínimo)
- Fase 11 — Hardening e integração final com o front

## Dívidas técnicas conhecidas

- **Refresh token não implementado** (Fase 3 entregou só access token de curta duração via `access_token_expire_minutes`). Adiado para a Fase 11 conforme o roadmap original — mas fica registrado aqui para não ser esquecido: hoje, quando o token expira, o único caminho é logar de novo.
- **`main` está atrasada em relação a `dev`** desde a Fase 1 — nenhuma fase ainda foi promovida para `main`. Reavaliar quando/se isso importa (ex.: antes do primeiro deploy real na Fase 11).

## Lições da Fase 7 (aplicar ao revisar código futuro)

- **Nunca validar regra de negócio a partir de `Match.status` diretamente** — esse campo é só um cache recalculado a cada join/leave/approve (`_sync_match_status`); qualquer verificação de "a partida está cheia?" deve comparar a contagem real de `Participant.status == confirmed` contra `max_participants`, não o campo `status`. Um bug desse tipo foi pego pelos testes automatizados na própria Fase 7 antes do merge — mesma dívida técnica (D8/D12 do front) que motivou o backend a existir; não reintroduzir o padrão "campo solto que pode divergir" nas fases seguintes (Fase 9 tem risco parecido com `average_rating`).

## Lições da Fase 8 (aplicar ao revisar código futuro)

- **Chat de partida não é público para qualquer usuário autenticado** — o `vision.md` §6 não especificava regra de acesso para `Message`, mas `GET/POST /matches/{id}/messages` só fazem sentido restritos a quem participa de fato da partida. Adotado o critério "organizador OU `Participant.status == confirmed`" (`_ensure_can_access_chat` em `app/services/message_service.py`), com `403 NOT_MATCH_PARTICIPANT` caso contrário. Vale como precedente para decisões de acesso análogas nas Fases 9 (quem pode avaliar) e 10 (quem pode denunciar/ver denúncias).
- **Padrão de expansão de relacionamento em `Read` schemas** — `MessageRead.sender` reaproveita `PublicProfileRead` via `build_public_profile` (mesmo padrão de `ParticipantRead.user` na Fase 5), em vez de expor só o ID. Manter esse padrão para qualquer novo schema que referencie `User` (ex.: avaliações na Fase 9).

## Notas

- Cada fase deve ser desenvolvida em branch própria (a partir de `dev`) e mergeada só depois de consumida com sucesso por uma tela real do front (não apenas via Swagger/Postman) — ver `roadmap.md` §2.
- Regras de negócio críticas a não esquecer quando chegar a hora: vagas/`status` de partida sempre derivados da contagem de `Participant.status == confirmed` (nunca campo solto); avaliação só válida com `match.status == closed` e ambos usuários `confirmed`.
- `email`/`hashed_password`/`role` foram adicionados ao model `User` já na Fase 2 (não estavam no `vision.md` §6 original, que não previa auth) para evitar uma migration extra na Fase 3.
- `app.core.dependencies.get_current_user` (criada na Fase 3) é a dependency padrão para exigir autenticação em qualquer router novo — usar `Depends(get_current_user)` em vez de reimplementar decodificação de JWT.
- Regra `B008` do `ruff` está no ignore list (`pyproject.toml`) por causa do idiom `Depends(...)` do FastAPI — não reverter isso achando que é lint solto.
