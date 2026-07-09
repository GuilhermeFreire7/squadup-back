# SquadUp Backend — Queue

> Sincronizado com `vision.md` e `roadmap.md` em 2026-07-08. Repositório Git em `https://github.com/GuilhermeFreire7/squadup-back`. **Branch principal de trabalho: `dev`** (não `main` — `main` está atrasada e ainda não recebeu Fase 1/CI). Para o histórico de tarefas concluídas (Fase 1 a 10, CI, updates de dependências), ver `progress.md`.

## Em andamento

_Fase 11 (Hardening e integração final) com o essencial concluído: refresh token com rotação, `POST /matches/{id}/close`, cobertura de testes e documentação OpenAPI — tudo mergeado em `dev` (PRs #27 e #28). Fase 12 (Refinamentos de contrato): D-B, D-C, D-D (decisões de contrato) e os itens 1, 3, 5 e 6 concluídos — `feature/fase-12-contrato` mergeada em `dev` via PR #31. Itens 2 e 4 (últimos da Fase 11/12) resolvidos e **commitados** (3 commits) na branch `feature/fase-12-infra-final` (cortada de `dev` em 2026-07-08): hospedagem decidida (Railway) com `Procfile`/driver Postgres/documentação de deploy prontos, e `POST /auth/logout-all` implementado para logout de todos os dispositivos. Ainda **sem push/PR** — só quando o usuário pedir, ver "Checkpointer" abaixo. Verificado também com o repositório do front (`../front`, ver correção na seção "Bloqueios" abaixo) que a Etapa 1 do plano mestre de integração está de fato encerrada e nada bloqueia a Fase 13 de lá._

## Bloqueios

- Nenhum bloqueio técnico conhecido. Decisões de stack da Fase 1 já tomadas: `venv` + `requirements.txt`, **SQLModel**, **SQLite** em dev, **PostgreSQL via `psycopg`** em produção. Hospedagem decidida: **Railway** (Postgres gerenciado nativo, deploy automático via GitHub, custo compatível com MVP — ver README.md "Deploy" para o racional completo e alternativas consideradas).
- Compatibilidade fixada: `bcrypt` pinado em `>=4.0,<4.1` no `requirements.txt` — `passlib[bcrypt]==1.7.4` lê `bcrypt.__about__.__version__`, removido em `bcrypt>=4.1`; sem o pin, `hash_password`/`verify_password` quebram em runtime. Reavaliar se `passlib` for atualizado para uma versão que não dependa desse atributo.
- **Ambiente de trabalho — correção (2026-07-08):** uma nota de sessão anterior aqui dizia que o repositório do front estava em `c:\Users\Public\workspace-personal\squadup-app`. **Isso estava errado** — esse caminho não existe nesta máquina. O repositório real está em `../front` (pasta local `front`, remote Git `https://github.com/GuilhermeFreire7/squadup-app.git` — o nome "squadup-app" é só do repositório no GitHub, não da pasta local). Confirmado com `git -C ../front remote -v` nesta sessão. `roadmap.md`/`vision.md` deste repositório, que já referenciam `../front`, estavam certos; a nota antiga (e a referência a um commit `b149c96` "no repositório squadup-app" no histórico do checkpointer abaixo) não puderam ser confirmadas e provavelmente eram incorretas.

## Dívidas técnicas conhecidas

- **`main` está atrasada em relação a `dev`** desde a Fase 1 — nenhuma fase ainda foi promovida para `main`. Reavaliar quando/se isso importa (ex.: antes do primeiro deploy real).

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

## Próxima tarefa — Fase 12: encerramento

> Todos os 6 itens da Fase 12 estão concluídos (ver `progress.md` §"Fase 12" para o detalhe de
> cada um). Contexto completo em `roadmap.md` §18 e `../front/.status/backend-contract.md` §6.

| # | Tarefa | Status |
|---|--------|--------|
| 1 | `cors_origins` configurável via `CORS_ORIGINS` | 🟢 Concluído |
| 2 | Decidir hospedagem — **Railway** (Postgres gerenciado, deploy via GitHub) | 🟢 Concluído |
| 3 | Rotina de purge de `refresh_tokens` expirados/revogados no startup | 🟢 Concluído |
| 4 | `POST /auth/logout-all` (logout de todos os dispositivos) | 🟢 Concluído |
| 5 | `/openapi.json` regenerado e validado contra o front | 🟢 Concluído |
| 6 | Commitar e abrir PR de `feature/fase-12-contrato` para `dev` | 🟢 Concluído (PR #31, mergeado) |

Itens 2 e 4 (últimos pendentes) implementados na branch `feature/fase-12-infra-final`
(cortada de `dev`) nesta sessão: driver `psycopg` + `Procfile` + seção "Deploy" no README.md
para o item 2; `revoke_all_refresh_tokens` (`app/services/auth_service.py`) + `POST
/auth/logout-all` (`app/routers/auth.py`) para o item 4, com 3 testes novos em
`app/tests/test_auth.py`. Gate completo verde (`pytest` 113 testes/99.11%, `ruff`, `black`,
`mypy` strict, `bandit`, `alembic check`) e validado manualmente com `uvicorn` local
(`/health` 200, `/auth/logout-all` presente no `/openapi.json`).

**Com isso, a Fase 12 (e a Fase 11, que compartilhava os pendentes) está formalmente encerrada**
— sinal verde para o front iniciar sua Fase 13 (`../front/.status/roadmap.md` §19). Confirmado
nesta mesma sessão: os documentos `../front/.status/backend-contract.md`, `queue.md` e
`roadmap.md` foram lidos e atualizados para refletir que a Etapa 1 (este pré-requisito) está
concluída — ver detalhe abaixo, "Checkpointer".

## Próximo passo sugerido

Nenhuma tarefa nova do roadmap está em aberto no momento — Fases 1 a 12 concluídas. Antes de
seguir para itens de "Próxima evolução" (`roadmap.md` §17: WebSocket, push, geolocalização,
upload de imagens, observabilidade), avaliar com o usuário: (a) promover `dev` para `main` pela
primeira vez (dívida técnica registrada acima) antes do primeiro deploy real no Railway; (b)
executar de fato o primeiro deploy no Railway (criar o projeto, addon de Postgres, variáveis de
ambiente) — passos documentados no README.md "Deploy", mas não executados nesta sessão por
exigirem uma conta/credenciais que este ambiente não tem.

## Notas

- Cada fase deve ser desenvolvida em branch própria (a partir de `dev`) e mergeada só depois de consumida com sucesso por uma tela real do front (não apenas via Swagger/Postman) — ver `roadmap.md` §2.
- Regras de negócio críticas a não esquecer quando chegar a hora: vagas/`status` de partida sempre derivados da contagem de `Participant.status == confirmed` (nunca campo solto); avaliação só válida com `match.status == closed` e ambos usuários `confirmed`.
- `email`/`hashed_password`/`role` foram adicionados ao model `User` já na Fase 2 (não estavam no `vision.md` §6 original, que não previa auth) para evitar uma migration extra na Fase 3.
- `app.core.dependencies.get_current_user` (criada na Fase 3) é a dependency padrão para exigir autenticação em qualquer router novo — usar `Depends(get_current_user)` em vez de reimplementar decodificação de JWT.
- Regra `B008` do `ruff` está no ignore list (`pyproject.toml`) por causa do idiom `Depends(...)` do FastAPI — não reverter isso achando que é lint solto.

## Lições da sessão 22 (aplicar ao revisar código futuro)

- **`pydantic-settings` decodifica campos complexos (`list[str]`) como JSON antes de qualquer `field_validator` rodar** — um `CORS_ORIGINS=a,b,c` no `.env` quebra com `SettingsError`/`JSONDecodeError` a menos que o campo seja anotado com `Annotated[list[str], NoDecode]` (`pydantic_settings.NoDecode`), que desliga esse parsing automático e deixa o `field_validator(mode="before")` fazer o split manual. Usar esse padrão para qualquer settings futura que precise de uma lista vinda de env var como string separada por vírgula.
- **`mypy` (strict) não aceita `Coluna == True`/`Coluna.is_(True)` em atributos `bool` do SQLModel** — o SQLModel tipa o atributo estaticamente como `bool` do Python, não como `InstrumentedAttribute`, então `.is_()` não existe nesse tipo aos olhos do mypy. Usar `sqlmodel.col(Model.campo).is_(True)` para sinalizar explicitamente que é uma coluna SQLAlchemy. Ao combinar com `|` (or bitwise) em `where()`, colocar a expressão `col(...).is_(...)` primeiro no `|` — `bool_column < valor | col(...).is_(True)` com a comparação primeiro faz o mypy tentar resolver via `bool.__or__` e falha (`No overload variant of "__or__" of "bool"`).
- **Rotina de purge sem scheduler dedicado:** para o volume esperado do MVP, purge de linhas obsoletas (`refresh_tokens` expirados/revogados) rodando uma vez por inicialização da API, dentro do `lifespan` (mesmo padrão de `create_db_and_tables()`), é suficiente — não é necessário introduzir Celery/cron externo só para isso. Reavaliar só se o padrão de deploy (várias réplicas subindo/descendo com frequência, sem período de baixo tráfego) tornar o purge-no-startup ineficaz.

## Checkpointer — retomar aqui na próxima sessão

**Não há bug em aberto. Fase 11 e 12 100% concluídas.** Estado exato para retomar:

- **Branch atual:** `feature/fase-12-infra-final` (cortada de `dev`), **commitada, sem
  push/PR** (só quando o usuário pedir). 3 commits, nesta ordem:
  1. `d79cbe5` — feat: adiciona `POST /auth/logout-all` (item 4).
  2. `edd0761` — feat: decide hospedagem (Railway) e prepara deploy de produção (item 2).
  3. `cd272e9` — docs: sincroniza `.status/` e encerra formalmente a Fase 11/12.
- **Gate completo verde:** `pytest` (113 testes, 99.11% cobertura), `ruff check`, `black --check`,
  `mypy app` (strict), `bandit`, `pip-audit` (sem CVEs no `psycopg` novo), `alembic check`.
  Validado manualmente com `uvicorn` local: `/health` 200, `/auth/logout-all` presente no
  `/openapi.json`.
- **Item 1 (CORS, commit `4e6c1f1`):** `app/core/config.py` — `cors_origins: Annotated[list[str], NoDecode]` + `_split_cors_origins` (`field_validator(mode="before")`); `DEFAULT_CORS_ORIGINS` extraído como constante do módulo. `.env.example` e `README.md` (seção "CORS") documentados. Novo `app/tests/test_config.py`.
- **Item 3 (purge de refresh tokens, commit `041ef5a`):** `app/services/auth_service.py::purge_expired_refresh_tokens` (usa `sqlmodel.col(RefreshToken.revoked).is_(True) | (RefreshToken.expires_at < utc_now_naive())`) chamada em `app/main.py` dentro do `lifespan`, logo após `create_db_and_tables()`.
- **Item 5 (openapi.json validado contra o front):** confirmado nesta sessão que `RatingRead.rated_user`/`match` e `ReportRead.match` batem com D-B/D-C no schema real. **Correção:** um checkpointer anterior afirmava ter commitado uma nota sobre isso em `squadup-app/.status/backend-contract.md` como `b149c96` — esse commit **não existe** no histórico real de `../front` (verificado com `git -C ../front cat-file -e b149c96`, resultado: não encontrado). Provavelmente uma alucinação de sessão anterior; desconsiderar. Esta sessão (2026-07-08) fez a sincronização real: leu `../front/.status/{backend-contract,queue,roadmap}.md` e atualizou os três diretamente (D-B/D-C/D-D marcados como resolvidos, `POST /auth/logout-all` documentado, gate de "Etapa 1" removido) — **essas edições estão no working tree de `../front` (branch `dev` lá), ainda não commitadas** nesse repositório; não commitei lá por ser um repositório separado, sem pedido explícito do usuário para isso.
- **Item 2 (hospedagem) e item 4 (logout-all):** ver commits `edd0761`/`d79cbe5` acima e a seção "Itens finais da Fase 11/12" em `progress.md`.
- **Próximo passo sugerido:** ver seção "Próximo passo sugerido" acima (promoção de `main`, primeiro deploy real no Railway). Separadamente, perguntar ao usuário se as edições pendentes em `../front/.status/` devem ser commitadas naquele repositório.
- **Nada bloqueado.**
