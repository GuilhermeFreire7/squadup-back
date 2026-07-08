# SquadUp Backend — Queue

> Sincronizado com `vision.md` e `roadmap.md` em 2026-07-08. Repositório Git em `https://github.com/GuilhermeFreire7/squadup-back`. **Branch principal de trabalho: `dev`** (não `main` — `main` está atrasada e ainda não recebeu Fase 1/CI). Para o histórico de tarefas concluídas (Fase 1 a 10, CI, updates de dependências), ver `progress.md`.

## Em andamento

_Fase 11 (Hardening e integração final) parcialmente concluída: `feature/fase-11-hardening` foi mergeada em `dev` via PR #27 (commit `a794760`) — refresh token com rotação e `POST /matches/{id}/close` estão em `dev`. Os dois commits seguintes (`77da987`, `b12d0d4`) foram só correção de falso positivo do gitleaks nos docs de `.status/`, sem código novo. Itens restantes da Fase 11 (cobertura de testes, revisão de OpenAPI, CORS/variáveis de produção, hospedagem, integração com o front) ainda não iniciados — ver "Próxima tarefa" abaixo._

## Ambiente local (pré-requisito prático, sessão 19)

> Antes de implementar qualquer item da Fase 12 (`roadmap.md` §18), é preciso ter o servidor
> rodando local para validar as mudanças — não dá pra testar D-B/D-C/D-D só lendo código.

- [ ] `cp .env.example .env` e preencher `SECRET_KEY` com um valor real (o default
  `"change-me-in-.env"` em `app/core/config.py` é só placeholder — `DATABASE_URL` pode
  continuar `sqlite:///./squadup.db`, é a escolha já fechada para dev);
- [ ] criar a venv e `pip install -r requirements.txt`;
- [ ] `alembic upgrade head`;
- [ ] rodar o seed (`app/seed.py`) para ter dados espelhando os mocks do front;
- [ ] `uvicorn app.main:app --reload` e confirmar `GET /health` + `GET /docs` respondendo.

## Bloqueios

- Nenhum bloqueio técnico conhecido. Decisões de stack da Fase 1 já tomadas: `venv` + `requirements.txt`, **SQLModel**, **SQLite** em dev. Hospedagem de deploy (Fase 11 — Railway/Render/Fly.io) ainda sem escolha.
- Compatibilidade fixada: `bcrypt` pinado em `>=4.0,<4.1` no `requirements.txt` — `passlib[bcrypt]==1.7.4` lê `bcrypt.__about__.__version__`, removido em `bcrypt>=4.1`; sem o pin, `hash_password`/`verify_password` quebram em runtime. Reavaliar se `passlib` for atualizado para uma versão que não dependa desse atributo.

## Próxima tarefa — Fase 11: Hardening e integração final (continuação)

- [x] Cobertura de testes automatizados para os fluxos principais de cada fase anterior — lacunas fechadas nesta sessão (branch `feature/fase-11-cobertura-e-producao`, ainda não commitada): 105 testes, 99.07% de cobertura (de 96/97.89%). Único gap remanescente é `app/seed.py::main()`/`if __name__ == "__main__"` (linhas 687-694, 698) — script de CLI de seed que abre a conexão real com `squadup.db`, não um fluxo servido pela API; deixado sem teste de propósito.
- [x] Revisão da documentação OpenAPI (`/docs`) como contrato oficial para o front — feita nesta sessão, mesma branch: novo `app/schemas/errors.py` (`ErrorResponse`/`error_responses()`) documenta em `responses=` de cada rota todos os `SHORT_CODE` de erro que o serviço pode retornar (antes só o 200/422 padrão do FastAPI apareciam no Swagger). Ver seção "Documentação OpenAPI" em `progress.md` para o detalhamento.
- Configuração de CORS e variáveis de ambiente para produção (`app/core/config.py::cors_origins` hoje só lista origins de dev do Expo — nenhum trabalho de produção feito ainda; os commits `77da987`/`b12d0d4` foram apenas correção de falso positivo do gitleaks em texto de `.status/`, não configuração real);
- Decisão de hospedagem de deploy (Railway/Render/Fly.io — ainda sem escolha, ver "Bloqueios");
- No front: substituir cada Context mockado por hooks de React Query, um de cada vez.

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
| 1 | Expandir `rated_user: PublicProfileRead` em `RatingRead` (`app/schemas/rating.py`), mesmo padrão de `MessageRead.sender` | D-B | ⚪ |
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

**Não há bug em aberto.** Cobertura de testes e documentação OpenAPI concluídas e validadas nesta sessão, ainda não commitadas.

- **Branch atual:** `feature/fase-11-cobertura-e-producao` (cortada de `dev`, sem PR aberto ainda) — mudanças em arquivos de teste (`app/tests/test_auth.py`, `app/tests/test_matches.py`, novo `app/tests/test_database.py`), um schema novo (`app/schemas/errors.py`) e os 5 routers (`app/routers/{auth,users,matches,messages,ratings,reports}.py` ganharam `responses=` documentando erros); mais esta `queue.md`. Nenhuma mudança de comportamento de runtime — só metadados de OpenAPI e testes.
- **O que está pronto e verde:**
  - Cobertura: 105 testes pytest (eram 96), 99.07% cobertura (era 97.89%). Fechadas as lacunas de `app/core/database.py` (`get_session`), `app/core/dependencies.py` (token sem `sub`, usuário deletado), `app/services/auth_service.py` (refresh token cujo usuário foi removido) e `app/services/match_service.py` (filtro por data, filtro por nível, `leave` em partida já encerrada, reingresso após sair, aprovação com partida já cheia).
  - OpenAPI: `app/schemas/errors.py` define `ErrorResponse` (schema Pydantic do formato `{"detail": {"code", "message"}}` já usado em todo `HTTPException`) e `error_responses(*tuplas)`, que monta o `responses=` do FastAPI agrupando múltiplos `SHORT_CODE`s do mesmo status HTTP como exemplos nomeados. Toda rota que pode retornar erro (exceto validação 422, já documentada pelo FastAPI) ganhou esse `responses=`, mapeado 1:1 com os `HTTPException` de cada service. Validado manualmente: `uvicorn` local, `GET /openapi.json` (200, 19 paths) e `GET /docs` (200) responderam corretamente; inspecionado `/openapi.json` de `POST /matches/{id}/join` para confirmar que os três `SHORT_CODE`s de erro 400 (`MATCH_NOT_JOINABLE`, `ALREADY_PARTICIPATING`, `MATCH_FULL`) aparecem como exemplos distintos no mesmo status.
  - `ruff`, `black`, `mypy app` (strict) e `pytest` todos verdes.
- **Gap remanescente, deixado de propósito:** `app/seed.py::main()` (linhas 687-694, 698) — só o entrypoint de CLI do script de seed, que abre conexão real com `squadup.db`; não é um fluxo servido pela API, testar isso exigiria side-effect em arquivo real sem ganho funcional.
- **Próximo passo concreto:** (1) commitar este trabalho (testes + OpenAPI); (2) implementar CORS/variáveis de ambiente de produção de fato (hoje `cors_origins` em `app/core/config.py` só cobre origins de dev do Expo); (3) decidir hospedagem (Railway/Render/Fly.io); (4) só então abrir PR de `feature/fase-11-cobertura-e-producao` (ou dividir em branches menores) para `dev`.
- **Nada bloqueado.**
