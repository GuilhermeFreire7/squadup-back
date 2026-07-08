# SquadUp Backend — Queue

> Sincronizado com `vision.md` e `roadmap.md` em 2026-07-08. Repositório Git em `https://github.com/GuilhermeFreire7/squadup-back`. **Branch principal de trabalho: `dev`** (não `main` — `main` está atrasada e ainda não recebeu Fase 1/CI). Para o histórico de tarefas concluídas (Fase 1 a 10, CI, updates de dependências), ver `progress.md`.

## Em andamento

_Fase 11 (Hardening e integração final) com o essencial concluído: refresh token com rotação, `POST /matches/{id}/close`, cobertura de testes (99.07%) e documentação OpenAPI — tudo mergeado em `dev` (PRs #27 e #28). Itens de infraestrutura que sobraram (CORS/produção, hospedagem) migraram para a tabela da Fase 12 abaixo, já que ambas as fases fecham juntas antes da integração com o front. Fase 12 (Refinamentos de contrato) iniciada nesta sessão (20): D-B concluído (ver `progress.md`). Ambiente local (`.env`, venv, migrations, seed, `uvicorn`) validado nesta sessão — ver `progress.md`, "Ambiente local validado (sessão 20)"._

## Bloqueios

- Nenhum bloqueio técnico conhecido. Decisões de stack da Fase 1 já tomadas: `venv` + `requirements.txt`, **SQLModel**, **SQLite** em dev. Hospedagem de deploy (Fase 11 — Railway/Render/Fly.io) ainda sem escolha.
- Compatibilidade fixada: `bcrypt` pinado em `>=4.0,<4.1` no `requirements.txt` — `passlib[bcrypt]==1.7.4` lê `bcrypt.__about__.__version__`, removido em `bcrypt>=4.1`; sem o pin, `hash_password`/`verify_password` quebram em runtime. Reavaliar se `passlib` for atualizado para uma versão que não dependa desse atributo.

## Dívidas técnicas conhecidas

- **`main` está atrasada em relação a `dev`** desde a Fase 1 — nenhuma fase ainda foi promovida para `main`. Reavaliar quando/se isso importa (ex.: antes do primeiro deploy real na Fase 11).
- **`refresh_tokens` sem rotina de limpeza** (nova, identificada na Fase 11) — linhas revogadas/expiradas nunca são removidas da tabela; ela cresce indefinidamente a cada login/refresh. Sem impacto funcional hoje (a busca é por `token_hash` indexado, não full scan), mas vale uma rotina de purge (ex.: BackgroundTask periódica ou job externo deletando `expires_at < now() OR revoked = true` com alguma margem) antes do primeiro deploy real com tráfego contínuo.
- **Sem endpoint de "logout de todos os dispositivos"** (nova, identificada na Fase 11) — `POST /auth/logout` revoga um único refresh token por vez; não há como um usuário invalidar todas as sessões ativas de uma vez (ex.: em caso de suspeita de conta comprometida). Avaliar se o front precisa disso antes de considerar a Fase 11 encerrada.

## Lições da Fase 7 (aplicar ao revisar código futuro)

- **Nunca validar regra de negócio a partir de `Match.status` diretamente** — esse campo é só um cache recalculado a cada join/leave/approve (`_sync_match_status`); qualquer verificação de "a partida está cheia?" deve comparar a contagem real de `Participant.status == confirmed` contra `max_participants`, não o campo `status`. Um bug desse tipo foi pego pelos testes automatizados na própria Fase 7 antes do merge — mesma dívida técnica (D8/D12 do front) que motivou o backend a existir; não reintroduzir o padrão "campo solto que pode divergir" nas fases seguintes (Fase 9 tem risco parecido com `average_rating`).

## Lições da Fase 8 (aplicar ao revisar código futuro)

- **Chat de partida não é público para qualquer usuário autenticado** — o `vision.md` §6 não especificava regra de acesso para `Message`, mas `GET/POST /matches/{id}/messages` só fazem sentido restritos a quem participa de fato da partida. Adotado o critério "organizador OU `Participant.status == confirmed`" (`_ensure_can_access_chat` em `app/services/message_service.py`), com `403 NOT_MATCH_PARTICIPANT` caso contrário. Vale como precedente para decisões de acesso análogas nas Fases 9 (quem pode avaliar) e 10 (quem pode denunciar/ver denúncias).
- **Padrão de expansão de relacionamento em `Read` schemas** — `MessageRead.sender` reaproveita `PublicProfileRead` via `build_public_profile` (mesmo padrão de `ParticipantRead.user` na Fase 5), em vez de expor só o ID. Manter esse padrão para qualquer novo schema que referencie `User` (ex.: avaliações na Fase 9).

## Lições da Fase 9 (aplicar ao revisar código futuro)

- **Nem toda ausência de participante confirmado é uma questão de permissão do usuário autenticado** — ao validar `POST /matches/{id}/ratings/{userId}`, o avaliador (`current_user`) sem `Participant.status == confirmed` retorna `403 NOT_MATCH_PARTICIPANT` (mesmo código/semântica do chat na Fase 8: falta de permissão de quem chama), mas o avaliado sem `confirmed` retorna `400 RATED_USER_NOT_PARTICIPANT` (o alvo da ação é que é inválido, não uma questão de acesso). Distinguir esses dois casos ao desenhar validações análogas na Fase 10 (ex.: denunciar um usuário que nunca participou da partida referenciada).
- **`average_rating` continuou 100% derivado sem nenhuma alteração** — `app/services/user_service.py::get_average_rating` já calculava a média a partir da tabela `ratings` desde a Fase 4; a Fase 9 só precisou inserir linhas reais em `ratings` para o valor passar a refletir avaliações verdadeiras. Confirma que nunca introduzir um campo solto (`average_rating`/`matches_played` como coluna) foi a decisão certa — reforça a mesma lição da Fase 7 para o `status` de partida.
- **Falta um endpoint de fechamento de partida** — a regra de negócio da Fase 9 depende de `match.status == closed`, mas nenhuma fase anterior implementou uma forma de chegar nesse estado além de manipulação direta do banco (seed/migração). Ver "Bloqueios" acima — decidir isso antes ou durante a Fase 10/11, senão o fluxo de avaliação nunca é alcançável via API pura no front.

## Lições da Fase 10 (aplicar ao revisar código futuro)

- **RBAC mínimo via dependency composta, não checagem manual em cada handler** — `get_current_admin` (`app/core/dependencies.py`) reaproveita `get_current_user` via `Depends` e adiciona só a checagem de `role == admin`, em vez de repetir `if current_user.role != UserRole.ADMIN` em cada rota. Usar o mesmo padrão para qualquer RBAC futuro em vez de checagem solta no corpo do handler.
- **`match_id` opcional em `Report` não exige validação de participação** — diferente da Fase 9 (avaliação exige `Participant.status == confirmed`), a denúncia não tem essa exigência no `vision.md`: `match_id` só é validado quanto à existência (`404 MATCH_NOT_FOUND`), sem checar se denunciante/denunciado participaram da partida. Decisão deliberada para não inventar regra de negócio não pedida — reavaliar só se o front precisar dessa restrição.
- **Ação de moderação sem efeito colateral real na conta** — `action: ban` só muda `Report.status` para `banned`; não há bloqueio de login nem campo de banimento em `User`. Escopo do `roadmap.md` §12/§16 é replicar as 3 ações do protótipo (arquivar/advertir/banir como rótulo de status), não um sistema de enforcement — não confundir com uma feature de moderação real ao estender isso no futuro.
- **Transição de estado única por denúncia** — `PATCH /reports/{id}` só aceita ação sobre denúncia `status == pending` (`400 REPORT_ALREADY_RESOLVED` caso contrário), decisão nova não coberta pelo protótipo mockado. Vale como precedente para qualquer recurso futuro que tenha estado "resolvido" sem caminho de volta.

## Lições da Fase 11 (aplicar ao revisar código futuro)

- **Refresh token nunca armazenado em texto puro** — a tabela `refresh_tokens` guarda só `token_hash` (SHA-256 do valor opaco gerado por `secrets.token_urlsafe`), nunca o token em si; ele só existe em texto puro na resposta HTTP no momento da emissão. SHA-256 (não `bcrypt`) é suficiente aqui porque o token já é aleatório e de alta entropia — o hash lento de senha existe para mitigar dicionário/força bruta contra senhas curtas, o que não se aplica a um token de 48 bytes.
- **Rotação obrigatória em todo uso de refresh token** — tanto `POST /auth/refresh` quanto `POST /auth/logout` marcam o token consultado como `revoked = True` antes de retornar, mesmo que a validação subsequente falhe. Isso significa que um refresh token só pode ser trocado por um novo par uma única vez; reuso (ex.: token roubado e usado por um atacante depois do dono legítimo já ter rotacionado) sempre retorna `401 INVALID_REFRESH_TOKEN`. Não enfraquecer essa invariante ao estender o fluxo de auth no futuro.
- **Datetime do SQLite é sempre naive** — comparar `datetime.now(UTC)` (aware) direto com uma coluna `DateTime` lida de volta do SQLite lança `TypeError`. Resolvido com `app.core.security.utc_now_naive()` (usado tanto para gravar `expires_at` quanto para comparar), que descarta o `tzinfo` de propósito. Usar essa mesma função para qualquer comparação futura de datas vindas do banco — não introduzir `datetime.now(UTC)` cru em lógica de comparação.
- **Fechamento de partida é a única transição manual de `status`** — diferente de `open`/`full` (sempre recalculados por `_sync_match_status` a partir da contagem de `Participant.status == confirmed`, lição da Fase 7), `closed` via `POST /matches/{id}/close` é setado diretamente pelo serviço porque não há como derivá-lo de nenhuma contagem — é uma decisão do organizador, não um estado calculável. Não confundir esse caso com a regra "nunca campo solto": aqui não há duplicação de fonte de verdade, só não há fonte derivável.
- **Migration gerada por `alembic revision --autogenerate` não segue o estilo do projeto por padrão** — o `alembic/script.py.mako` ainda usava `typing.Union`/`typing.Sequence` (padrão antigo do template do Alembic) em vez do estilo `X | Y` já usado na migration inicial (`70043fe6862c`) e exigido pelo resto do código (`ruff`/`black`). Corrigido o template para gerar já no formato certo; revisar/rodar `black`+`ruff` em qualquer migration nova mesmo assim, pois o autogenerate não formata o SQL gerado (linhas longas em `op.create_index`, por exemplo).

## Próxima tarefa — Fase 12: Refinamentos de contrato para integração com o front

> Só começa depois que a Fase 11 estiver de fato encerrada (itens acima). Contexto completo e
> raciocínio das decisões D-B/D-C/D-D em `roadmap.md` §18 e em
> `../front/.status/backend-contract.md` §6 — não duplicar aqui, só rastrear o "o quê".
> **Bloqueia a Fase 13 do front** (`../front/.status/roadmap.md` §19): os tipos/adapters de lá
> serão desenhados a partir do contrato que sair desta fase.

| # | Tarefa | Decisão | Status |
|---|--------|---------|--------|
| 1 | Expandir `rated_user: PublicProfileRead` em `RatingRead` (`app/schemas/rating.py`), mesmo padrão de `MessageRead.sender` | D-B | 🟢 concluído — ver `progress.md` §"Fase 12" |
| 2 | Decidir com o front se `RatingRead`/`ReportRead` ganham `MatchRef` (`id, title, sport, date`) em vez de só `match_id` | D-C | ⚪ |
| 3 | Se D-C aprovado: criar schema `MatchRef` e incluir em `RatingRead.match`/`ReportRead.match` | D-C | ⚪ |
| 4 | Decidir se o backend emite `Message(type=system)` automaticamente ao criar partida, ou se o front descarta essa simulação | D-D | ⚪ |
| 5 | Se D-D aprovado: implementar emissão da mensagem de sistema em `app/services/match_service.py::create_match` | D-D | ⚪ |
| 6 | Configurar CORS/variáveis de ambiente de produção (`app/core/config.py::cors_origins`) — item já pendente da Fase 11 | — | ⚪ |
| 7 | Decidir hospedagem (Railway/Render/Fly.io) — item já pendente da Fase 11 | — | ⚪ |
| 8 | Rotina de purge de `refresh_tokens` expirados/revogados — dívida técnica já registrada acima | — | ⚪ |
| 9 | Avaliar necessidade de "logout de todos os dispositivos" — dívida técnica já registrada acima | — | ⚪ |
| 10 | Regenerar `/openapi.json` após as mudanças e confirmar com o front que bate com `backend-contract.md` | — | ⚪ |

## Notas

- Cada fase deve ser desenvolvida em branch própria (a partir de `dev`) e mergeada só depois de consumida com sucesso por uma tela real do front (não apenas via Swagger/Postman) — ver `roadmap.md` §2.
- Regras de negócio críticas a não esquecer quando chegar a hora: vagas/`status` de partida sempre derivados da contagem de `Participant.status == confirmed` (nunca campo solto); avaliação só válida com `match.status == closed` e ambos usuários `confirmed`.
- `email`/`hashed_password`/`role` foram adicionados ao model `User` já na Fase 2 (não estavam no `vision.md` §6 original, que não previa auth) para evitar uma migration extra na Fase 3.
- `app.core.dependencies.get_current_user` (criada na Fase 3) é a dependency padrão para exigir autenticação em qualquer router novo — usar `Depends(get_current_user)` em vez de reimplementar decodificação de JWT.
- Regra `B008` do `ruff` está no ignore list (`pyproject.toml`) por causa do idiom `Depends(...)` do FastAPI — não reverter isso achando que é lint solto.

## Checkpointer — retomar aqui na próxima sessão

**Não há bug em aberto.** `feature/fase-11-cobertura-e-producao` (cobertura de testes + documentação OpenAPI, ver histórico em `progress.md`) já foi mergeada em `dev` via PR #28 (commit `90e9427`) — esta seção estava desatualizada dizendo o contrário; corrigido na sessão 20.

- **Branch atual:** `feature/fase-12-contrato` (cortada de `dev`, sem PR aberto ainda) — mudanças em `app/schemas/rating.py`, `app/services/rating_service.py`, `app/tests/test_ratings.py`, `README.md` e `.status/{queue.md,roadmap.md}`. Ainda não commitado.
- **Ambiente local validado nesta sessão (20):** ver checklist "Ambiente local" acima — `.env` criado, dependências confirmadas, `alembic upgrade head` já estava em dia (`b4fcc804c2cd`), seed rodado, `uvicorn`/`/health`/`/docs` confirmados.
- **D-B implementado e validado nesta sessão (20):** `RatingRead.rated_user_id` (str solto) substituído por `RatingRead.rated_user: PublicProfileRead`, mesmo padrão de `MessageRead.sender`/`ParticipantRead.user` — `rating_service.build_rating_read` agora chama `build_public_profile(session, rating.rated_user)`. Campo interno do model `Rating.rated_user_id` **não mudou** (é coluna real do banco; só o schema de resposta da API mudou). Teste `test_confirmed_participant_can_rate_another_after_match_closed` atualizado para checar `body["rated_user"]["id"]`. `pytest` (105 testes, 99.07% cobertura), `ruff`, `black` e `mypy app` (strict) verdes. Validado manualmente: `uvicorn` local, `/openapi.json` confirma `RatingRead.properties` com `rated_user` (não mais `rated_user_id`), e `GET /users/user-1/ratings` contra o `squadup.db` do seed retornou `rated_user` totalmente expandido.
- **Próximo passo concreto:** (1) commitar D-B; (2) decidir D-C (`MatchRef` leve em `RatingRead.match`/`ReportRead.match`) e D-D (mensagem de sistema automática ao criar partida) com o front antes de implementar — ver `roadmap.md` §18; (3) os itens de infraestrutura (CORS produção, hospedagem, purge de `refresh_tokens`, logout de todos os dispositivos) seguem pendentes na tabela da Fase 12 abaixo.
- **Nada bloqueado.**
