# SquadUp Backend — Queue

> Sincronizado com `vision.md` e `roadmap.md` em 2026-07-08. Repositório Git em `https://github.com/GuilhermeFreire7/squadup-back`. **Branch principal de trabalho: `dev`** (não `main` — `main` está atrasada e ainda não recebeu Fase 1/CI). Para o histórico de tarefas concluídas (Fase 1 a 10, CI, updates de dependências), ver `progress.md`.

## Em andamento

_Fases 1 a 12 concluídas (ver `progress.md`). Fase 12 encerrada e commitada (3 commits) na branch `feature/fase-12-infra-final` (cortada de `dev` em 2026-07-08) — hospedagem decidida (Railway) e `POST /auth/logout-all` implementado. Ainda **sem push/PR** dessa branch — só quando o usuário pedir. Verificado com o repositório do front (pasta local `squadup-app`, remote `squadup-app`) que a Etapa 1 do plano mestre de integração está de fato encerrada e nada bloqueia a Fase 13 de lá._

_**Fase 13 (geolocalização real + notificações push) registrada em 2026-07-08 — DESTRAVADA em 2026-07-16 (sessão 29 do front).** Era o plano original do produto, o autor confirmou que quer implementar de fato. Detalhamento completo em `roadmap.md` §19. A Fase 13 do front (integração real, pré-requisito) está 100% concluída (16/16, sessão 28) — o front avançou nesta sessão o desenho conjunto completo, consolidado em `../squadup-app/.status/backend-contract.md` §6-A (contrato de API, decisões D-Geo-3/4 e D-Push-3/4 novas, complementando as D-Geo-1/2 e D-Push-1/2 já registradas aqui). **Existe agora uma fila executável de código para este repositório** — ver "Próxima tarefa — Fase 13" abaixo, que substitui a antiga observação de "nada a fazer"._

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

## Próxima tarefa — Fase 13: geolocalização real e notificações push

> Detalhamento completo (decisões de arquitetura, contrato de API campo a campo) em `roadmap.md`
> §19 e no plano consolidado `../squadup-app/.status/backend-contract.md` §6-A. Etapas 1–4 abaixo
> são deste repositório; a numeração corresponde exatamente às etapas 1–4 do plano mestre em
> §6-A (etapas 5–8 são do front).

| # | Tarefa | Status |
|---|--------|--------|
| 1 | Migration `latitude: float \| null`, `longitude: float \| null` em `Match`; `MatchCreate`/`MatchRead`/`MatchDetailRead` atualizados | ⚪ |
| 2 | `GET /matches` ganha `lat`/`lng`/`radius_km` (query params opcionais, default `radius_km=20`); filtro por Haversine (SQL puro ou Python pós-bounding-box, sem PostGIS); ordenação por distância quando os 3 params vierem juntos; testes cobrindo partida dentro/fora do raio | ⚪ |
| 3 | Tabela `push_tokens` (`id`, `user_id → users.id`, `token` unique, `created_at`); `POST /users/me/push-token` (upsert idempotente); revogação de push tokens em `POST /auth/logout`/`logout-all` | ⚪ |
| 4 | `app/services/notification_service.py` (`send_push(user_id, title, body, data)` via `expo-server-sdk`, nunca propaga exceção — falha de entrega só loga, D-Push-4); disparo via `BackgroundTasks` nos 3 eventos: nova mensagem (`message_service`), participação aprovada (`match_service.approve_participant`), partida encerrada/cancelada (`match_service.close_match`); testes com cliente Expo mockado (nunca bater na Expo real em `pytest`) | ⚪ |

**Ordem de dependência:** etapas 1–2 (geo) e 3 (push, tabela+endpoint) são independentes entre
si e podem ser feitas em paralelo/qualquer ordem. Etapa 4 depende só da 3. Nenhuma delas depende
do front — são aditivas ao contrato existente, então podem ser desenvolvidas e testadas via
Swagger/`pytest` antes mesmo do front começar sua parte (etapas 5–8 do plano mestre).

**Nova dependência de runtime:** adicionar `expo-server-sdk` (ou equivalente Python — avaliar se
existe um pacote maduro, senão chamar a Expo Push API via `httpx` diretamente, já uma dependência
existente do projeto) ao `requirements.txt`.

**Lição a aplicar (do padrão já estabelecido nas Fases 7/9, ver acima):** `latitude`/`longitude`
são dados de entrada, não derivados — não há regra de "nunca campo solto" aplicável aqui (ao
contrário de `status`/`average_rating`). Mas a ordenação por distância em `GET /matches` deve ser
calculada em tempo de leitura a partir de `lat`/`lng` da query e da partida, nunca cacheada.

## Plano de entrega final (app + backend + TCC)

> Traçado em 2026-07-08 a partir da leitura de `../front/TCC.tex` (monografia do TCC do autor) e do estado real dos dois repositórios: **`../front/.status/plano-de-entrega.md`**. Cobre deploy real do backend (Railway), a Fase 13 de integração do front (maior bloco de trabalho restante — o front ainda é 100% mockado), build/demo do app para a defesa, estrutura de assets do TCC (hoje só existem no Overleaf) e os gaps de conteúdo da monografia (faltam ~7 casos de uso documentados, capítulo de resultados/testes, correção de trechos sobre geolocalização). Consultar antes de decidir a próxima prioridade de infraestrutura.

## Próximo passo sugerido

Fases 1 a 12 concluídas. **Fase 13 (`roadmap.md` §19 — geolocalização real + notificações push)
destravada em 2026-07-16** — a Fase 13 do front (pré-requisito) terminou (16/16, sessão 28), e o
front avançou nesta sessão o desenho conjunto completo (contrato de API, decisões de arquitetura)
consolidado em `../squadup-app/.status/backend-contract.md` §6-A. **Há agora uma fila executável
de código para este repositório** — ver "Próxima tarefa — Fase 13" acima (4 tarefas, etapas 1–4
do plano mestre, todas aditivas ao contrato existente e sem dependência do front para começar).

O que também não está bloqueado e pode avançar em paralelo:
(a) promover `dev` para `main` pela primeira vez (dívida técnica registrada acima) antes do
primeiro deploy real no Railway; (b) executar de fato o primeiro deploy no Railway (criar o
projeto, addon de Postgres, variáveis de ambiente) — passos documentados no README.md "Deploy",
mas não executados ainda por exigirem uma conta/credenciais que este ambiente não tem.

Recomendação de ordem: começar pela Fase 13 (código novo, maior valor) e tratar a promoção de
`main`/primeiro deploy real como está, quando o usuário tiver as credenciais. Ver "Checkpointer"
abaixo para o estado exato do repositório.

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

**Não há bug em aberto. Fases 1 a 12 100% concluídas. Fase 13 registrada, mas bloqueada
(não é para começar a implementar).** Estado exato para retomar:

- **Branch atual:** `feature/fase-12-infra-final` (cortada de `dev`), **commitada, sem
  push/PR** (só quando o usuário pedir — a última vez que o branch foi sincronizado com o
  remoto foi manualmente pelo usuário, não por mim). 4 commits, nesta ordem:
  1. `d79cbe5` — feat: adiciona `POST /auth/logout-all` (Fase 12, item 4).
  2. `edd0761` — feat: decide hospedagem (Railway) e prepara deploy de produção (Fase 12, item 2).
  3. `cd272e9` — docs: sincroniza `.status/` e encerra formalmente a Fase 11/12.
  4. `b825601` — docs: corrige referências incorretas ao repositório do front no checkpointer.
  5. `974786f` — docs: registra a Fase 13 (geolocalização real e notificações push).
- **Gate completo verde** (validado até o commit 4; nenhum código de produto mudou no commit 5,
  só docs): `pytest` (113 testes, 99.11% cobertura), `ruff check`, `black --check`, `mypy app`
  (strict), `bandit`, `pip-audit`, `alembic check`. Validado manualmente com `uvicorn` local.
- **Fase 13 (`roadmap.md` §19) — o que muda a partir de agora:** geolocalização real e
  notificações push deixaram de ser "fora do escopo" — o usuário confirmou que sempre fizeram
  parte do plano do produto e serão implementadas de fato. Registrada com decisões de design
  (fonte das coordenadas, raio de busca, provedor de push via Expo Push API, eventos que
  disparam notificação) e tarefas detalhadas em `roadmap.md` §19.1/§19.2. **Bloqueada até a
  Fase 13 do front (integração real com esta API) terminar** — o front hoje ainda é 100%
  mockado (`../front/.status/plano-de-entrega.md`). Instrução explícita do usuário nesta
  sessão: parar de tocar no repositório do front por ora e manter o foco de trabalho aqui —
  mas como o próprio trabalho de código da Fase 13 depende do front avançar primeiro, **não há
  nenhuma tarefa de implementação a fazer no back neste momento**, só a documentação já feita.
- **Estado do front (para contexto, não é responsabilidade desta sessão):** `../front` está com
  `.status/backend-contract.md`, `queue.md`, `roadmap.md` e `plano-de-entrega.md` (novo) editados
  no working tree da branch `dev` de lá, ainda **não commitados** — deixado assim
  deliberadamente, é um repositório separado e o usuário instruiu a não continuar editando lá
  por ora. Também já foi criada a estrutura `front/tcc/` (TCC.tex, references.bib, assets/logo.png,
  assets/concorrentes/*) pelo próprio usuário, com os caminhos do `.tex` já ajustados nesta sessão.
- **Próximo passo sugerido:** ver seção "Próximo passo sugerido" acima — só os itens não
  bloqueados (promoção de `main`, primeiro deploy real no Railway) podem avançar agora; o resto
  espera o front.
- **Nada bloqueado no sentido de "trabalho parado por erro"** — só a ordem de dependência entre
  repositórios definida pelo próprio usuário.

## Checkpointer — sessão 29 (2026-07-16), atualiza o estado acima

**O bloqueio registrado no checkpointer da sessão anterior (acima) foi resolvido.** A Fase 13 do
front terminou (16/16, sessão 28, 2026-07-16) e, na mesma data, o front conduziu o desenho
conjunto completo desta Fase 13 do backend — escopo confirmado com o usuário (geolocalização com
coordenadas reais via GPS do dispositivo; notificações push no conjunto essencial de eventos),
contrato de API fechado campo a campo, e etapas numeradas por repositório. Consolidado em
`../squadup-app/.status/backend-contract.md` §6-A (também referenciado aqui em `roadmap.md` §19
e na fila executável acima, "Próxima tarefa — Fase 13").

- **Nomes de pasta corrigidos nesta sessão:** o front é acessível como `../squadup-app` (não
  mais `../front` — o caminho usado nos checkpointers anteriores). O usuário confirmou que usa
  este backend em duas máquinas com nomes de pasta diferentes; os caminhos relativos citados
  neste documento a partir de agora devem ser tratados como referência de conteúdo, não
  literalmente resolvíveis em toda máquina — confirmar o nome real da pasta irmã antes de seguir
  um link relativo se ele não resolver.
- **Há agora 4 tarefas de código concretas e não bloqueadas neste repositório** (ver "Próxima
  tarefa — Fase 13" acima): migration de `latitude`/`longitude` + filtro de proximidade em
  `GET /matches`; tabela `push_tokens` + endpoint de registro; serviço de notificação + disparo
  nos 3 eventos. Nenhuma delas depende de código novo do front para começar — são aditivas ao
  contrato já estável desde a Fase 12.
- **Risco de cronograma:** esta é uma adição de escopo fora do plano original do TCC — ver
  `../squadup-app/.status/plano-de-entrega.md` §9 para a avaliação de risco completa e o plano de
  contingência (cortar push antes de cortar geo, se o prazo até a defesa apertar).
- **Próximo passo sugerido:** iniciar pelas etapas 1–2 (geolocalização, `roadmap.md` §19.1) ou
  3–4 (push, §19.2) — são trilhas independentes entre si, ordem livre. Recomendação: geo primeiro
  (menor superfície de mudança, sem dependência de biblioteca externa de push), depois push.
