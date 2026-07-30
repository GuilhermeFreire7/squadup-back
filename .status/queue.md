# SquadUp Backend — Queue

> Sincronizado com `vision.md` e `roadmap.md` em 2026-07-30 (sessão 31 deste repositório). Repositório Git em `https://github.com/GuilhermeFreire7/squadup-back`. **Branch principal de trabalho: `dev`.** `main` foi promovida pela primeira vez em 2026-07-28 (sessão 30, fast-forward `440ef35..30eb5d9`) e está em dia com `dev`. Para o histórico de tarefas concluídas (Fase 1 a 10, CI, updates de dependências), ver `progress.md`.

## Em andamento

_Fases 1 a 12 concluídas e mergeadas em `dev` (ver `progress.md`)._

_**Fase 13 (geolocalização real + notificações push):** tarefas 1–4 (deste repositório) concluídas e mergeadas em `dev` via **PR #50** (2026-07-28) — ver "Checkpointer" abaixo e `progress.md` §"Fase 13 — tarefas 1–4 concluídas" para o detalhe completo. Do lado do front (`../squadup-front/.status/roadmap.md` §20), as etapas 5–6 (geolocalização) e 7 (push: `useNotificationRegistration`, listener de navegação, `projectId` do EAS gerado) já foram concluídas (sessões 31–33, 2026-07-28); a etapa 8 (hardening ponta a ponta em dispositivo físico) **começou** na sessão 34 do front — achou e corrigiu 7 bugs, todos do lado do front (D28–D34), confirmando o contrato deste backend como correto — mas **segue sem confirmação de teste ponta a ponta pelo usuário** na build mais recente (`fa25bd21`). **Nada bloqueado neste repositório neste momento.**_

## Bloqueios

- Nenhum bloqueio técnico conhecido. Decisões de stack da Fase 1 já tomadas: `venv` + `requirements.txt`, **SQLModel**, **SQLite** em dev, **PostgreSQL via `psycopg`** em produção. Hospedagem decidida: **Railway** (Postgres gerenciado nativo, deploy automático via GitHub, custo compatível com MVP — ver README.md "Deploy" para o racional completo e alternativas consideradas).
- Compatibilidade fixada: `bcrypt` pinado em `>=4.0,<4.1` no `requirements.txt` — `passlib[bcrypt]==1.7.4` lê `bcrypt.__about__.__version__`, removido em `bcrypt>=4.1`; sem o pin, `hash_password`/`verify_password` quebram em runtime. Reavaliar se `passlib` for atualizado para uma versão que não dependa desse atributo.
- **Ambiente de trabalho — correção (2026-07-08):** uma nota de sessão anterior aqui dizia que o repositório do front estava em `c:\Users\Public\workspace-personal\squadup-app`. **Isso estava errado** — esse caminho não existe nesta máquina. O repositório real está em `../front` (pasta local `front`, remote Git `https://github.com/GuilhermeFreire7/squadup-app.git` — o nome "squadup-app" é só do repositório no GitHub, não da pasta local). Confirmado com `git -C ../front remote -v` nesta sessão. `roadmap.md`/`vision.md` deste repositório, que já referenciam `../front`, estavam certos; a nota antiga (e a referência a um commit `b149c96` "no repositório squadup-app" no histórico do checkpointer abaixo) não puderam ser confirmadas e provavelmente eram incorretas.

## Dívidas técnicas e backlog — como tarefas ordenadas

> Reestruturado na sessão 31 (2026-07-30) a pedido do usuário — antes só a T1 estava registrada,
> como um bullet solto. Ordem = prioridade sugerida, não obrigação de sequência estrita (T1 é a
> única bloqueante; T2 é a única dívida técnica de código real; T3–T6 são evolução de escopo,
> `roadmap.md` §17, sem data prevista). Todas as etapas são independentes entre si — não há
> dependência técnica de uma tarefa sobre a anterior, exceto onde indicado.

| # | Tarefa | Tipo | Prioridade | Status |
|---|--------|------|-----------|--------|
| T1 | Confirmação de teste ponta a ponta em dispositivo físico (etapa 8 da Fase 13/14) | Bloqueio externo | 🔴 Bloqueante | ⚪ Aguardando o usuário |
| T2 | `POST /auth/logout` (single-device) não revoga o push token do dispositivo que sai | Dívida técnica | Baixa | ⚪ Aberta |
| T3 | WebSocket para chat em tempo real | Evolução de escopo | A decidir | ⚪ Não iniciada |
| T4 | Upload de imagens (avatar, fotos de partida) via storage S3-compatible | Evolução de escopo | A decidir | ⚪ Não iniciada |
| T5 | Testes de carga e observabilidade (logs estruturados, métricas) | Evolução de escopo | A decidir | ⚪ Não iniciada |
| T6 | CI/CD automatizado para deploy do backend a cada merge | Evolução de escopo | A decidir | ⚪ Não iniciada |

### T1 — Confirmação de teste ponta a ponta em dispositivo físico

Não é uma tarefa de código deste repositório — é a única pendência real de toda a Fase 13/14, em
ambos os repositórios. O front precisa confirmar que a build EAS `fa25bd21` (commit `3dcd0dd`)
completa o fluxo cadastro → criar partida → chat → filtro de proximidade → push numa passada só,
num Android físico. Quando isso acontecer, o próximo passo aqui é só registrar o resultado e
fechar a Fase 13 formalmente em `roadmap.md`. Ver "Checkpointer" abaixo para o estado exato.

### T2 — Push token não revogado em logout de um único dispositivo

Só `POST /auth/logout-all` remove push tokens (todos os do usuário, ver
`auth_service.revoke_all_refresh_tokens`). O contrato de `POST /users/me/push-token` (`{ token
}`) não associa o token a uma sessão/refresh token específico, então não há como saber com
segurança qual push token pertence ao dispositivo saindo sem arriscar remover o de outro
dispositivo ainda ativo do mesmo usuário. Efeito prático: um usuário que só desloga em 1 de N
dispositivos continua podendo receber push nesse dispositivo até o token expirar/falhar na Expo
(`DeviceNotRegistered`) ou até um `logout-all`. Baixa prioridade — não afeta segurança de dados,
só higiene de notificação. Se resolver: ampliar o contrato de `POST /users/me/push-token` para
receber um identificador de sessão/device — é mudança de contrato, envolve o front. Descoberto na
sessão 30 (2026-07-28) ao implementar a Fase 13, etapa 3.

### T3–T6 — Evolução de escopo pós-Fase 13/14 (`roadmap.md` §17)

Nenhuma destas quatro tem data ou decisão de "vai fazer" — são a lista de possíveis próximas
frentes depois que a Fase 13/14 fechar de vez (T1 resolvido), na mesma lista já registrada em
`roadmap.md` §17 desde a origem do repositório, sem mudança de conteúdo nesta sessão:

- **T3 — WebSocket para chat em tempo real:** hoje `GET/POST /matches/{id}/messages` é REST puro
  (poll/refetch no front); só vira prioridade se o polling atual se mostrar insuficiente para a
  demo ou para uso real.
- **T4 — Upload de imagens via storage S3-compatible:** hoje `photo_url` (usuário) é só uma URL
  externa; sem upload real de arquivo em nenhuma tela.
- **T5 — Testes de carga e observabilidade:** sem logs estruturados nem métricas hoje além do
  logging padrão do `uvicorn`/exceções — relevante só se o volume de uso real justificar.
- **T6 — CI/CD automatizado para deploy a cada merge:** hoje o deploy em produção (Railway) é
  auto-deploy simples atrelado à branch `dev` (sem pipeline de CI/CD dedicado para o deploy em
  si, distinto do CI de lint/test/security já existente); formalizar isso só se o ritmo de
  releases justificar o investimento.

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

## Próxima tarefa — T1 (Fase 13: hardening conjunto, etapa 8, único item bloqueante)

> Tarefas 1–4 (código deste repositório) **concluídas e mergeadas em `dev`** (PR #50,
> 2026-07-28) — detalhe tarefa-a-tarefa em `progress.md` §"Fase 13 — tarefas 1–4 concluídas".
> Detalhamento completo do plano mestre em `roadmap.md` §19 e no contrato consolidado
> `../squadup-front/.status/backend-contract.md` §6-A.

Item que falta para fechar a Fase 13 por completo: **T1 / etapa 8 — hardening ponta a ponta em
dispositivo físico**, testando geolocalização real (GPS) e push real (Expo). O front concluiu as
etapas 5–7 (geolocalização e push, sessões 31–33, 2026-07-28) e **começou** a etapa 8 na sessão
34 (achou e corrigiu 7 bugs, todos do lado do front — ver `progress.md` §"sincronização com o
hardening..."), mas a build mais recente (`fa25bd21`) segue sem confirmação de teste ponta a
ponta pelo usuário. T1 é o **único item bloqueante de toda a Fase 13/Fase 14**, em ambos os
repositórios. Nenhuma ação de código pendente neste repositório até lá — ver também T2–T6 (seção
"Dívidas técnicas e backlog") para o que existe além dessa pendência, nenhum deles bloqueante.

## Plano de entrega final (app + backend + TCC)

> Traçado em 2026-07-08 a partir da leitura de `../squadup-front/TCC.tex` (monografia do TCC do autor) e do estado real dos dois repositórios: **`../squadup-front/.status/plano-de-entrega.md`**. Cobre deploy real do backend (Railway), a integração do front, build/demo do app para a defesa, estrutura de assets do TCC e os gaps de conteúdo da monografia. Consultar antes de decidir a próxima prioridade de infraestrutura.

## Próximo passo sugerido

Fases 1 a 12 concluídas; Fase 13 (backend) com as 4 tarefas de código concluídas e mergeadas
(PR #50), `main` promovida e sincronizada com `dev` pela primeira vez, e a migration da Fase 13
confirmada rodando em produção (Railway) — ver `progress.md` §"Fase 13 — main promovida e
migration confirmada em produção" para o detalhe completo dessa continuação da sessão 30. Do
lado do front, as etapas 5–7 (geolocalização real e push real) também já foram concluídas
(sessões 31–33, `../squadup-front/.status/roadmap.md` §20), e a etapa 8 (hardening) **começou**
na sessão 34 — ver T1 acima e o Checkpointer abaixo para o estado exato.

**Nada de código, deploy ou infraestrutura está pendente neste repositório.** O único item
bloqueante de toda a Fase 13/Fase 14 (em ambos os repositórios) é **T1 — hardening ponta a ponta
em dispositivo físico** (GPS real + push real), que só pode ser feita com um device físico e
depende do usuário/front avançar, não de mais código de backend. T2–T6 (seção "Dívidas técnicas
e backlog") existem mas nenhum é bloqueante nem tem prazo — só entram em jogo se/quando o usuário
decidir priorizá-los, depois que T1 fechar.

## Notas

- Cada fase deve ser desenvolvida em branch própria (a partir de `dev`) e mergeada só depois de consumida com sucesso por uma tela real do front (não apenas via Swagger/Postman) — ver `roadmap.md` §2.
- Regras de negócio críticas a não esquecer quando chegar a hora: vagas/`status` de partida sempre derivados da contagem de `Participant.status == confirmed` (nunca campo solto); avaliação só válida com `match.status == closed` e ambos usuários `confirmed`.
- `email`/`hashed_password`/`role` foram adicionados ao model `User` já na Fase 2 (não estavam no `vision.md` §6 original, que não previa auth) para evitar uma migration extra na Fase 3.
- `app.core.dependencies.get_current_user` (criada na Fase 3) é a dependency padrão para exigir autenticação em qualquer router novo — usar `Depends(get_current_user)` em vez de reimplementar decodificação de JWT.
- Regra `B008` do `ruff` está no ignore list (`pyproject.toml`) por causa do idiom `Depends(...)` do FastAPI — não reverter isso achando que é lint solto.

## Lições das sessões 34–35 do front (aplicar ao revisar código futuro)

- **Um schema Pydantic estrito só "funciona" de ponta a ponta se quem consome sabe ler o erro que
  ele produz** — `RegisterRequest.password` (`min_length=8`) e `RegisterRequest.email` (`EmailStr`)
  sempre estiveram corretos aqui, mas o front só percebeu os dois mismatches (validava senha com
  6+, e-mail com uma checagem frouxa) porque o `422` automático do FastAPI/Pydantic (`detail` como
  lista de `{loc, msg, type}`, formato diferente do nosso `{code, message}` costumeiro) caía no
  fallback genérico de erro do cliente HTTP do front, escondendo a causa real até uma sessão de
  hardening em dispositivo físico expor o problema. Não é uma lição de mudança de código aqui — é
  um lembrete para o futuro: ao desenhar qualquer schema novo com validação estrita (`min_length`,
  `EmailStr`, `pattern`, etc.), vale checar se quem consome (front ou qualquer outro cliente) tem
  como enxergar a mensagem real do `422`, não só assumir que "o schema documenta a regra" é
  suficiente.

## Lições da sessão 22 (aplicar ao revisar código futuro)

- **`pydantic-settings` decodifica campos complexos (`list[str]`) como JSON antes de qualquer `field_validator` rodar** — um `CORS_ORIGINS=a,b,c` no `.env` quebra com `SettingsError`/`JSONDecodeError` a menos que o campo seja anotado com `Annotated[list[str], NoDecode]` (`pydantic_settings.NoDecode`), que desliga esse parsing automático e deixa o `field_validator(mode="before")` fazer o split manual. Usar esse padrão para qualquer settings futura que precise de uma lista vinda de env var como string separada por vírgula.
- **`mypy` (strict) não aceita `Coluna == True`/`Coluna.is_(True)` em atributos `bool` do SQLModel** — o SQLModel tipa o atributo estaticamente como `bool` do Python, não como `InstrumentedAttribute`, então `.is_()` não existe nesse tipo aos olhos do mypy. Usar `sqlmodel.col(Model.campo).is_(True)` para sinalizar explicitamente que é uma coluna SQLAlchemy. Ao combinar com `|` (or bitwise) em `where()`, colocar a expressão `col(...).is_(...)` primeiro no `|` — `bool_column < valor | col(...).is_(True)` com a comparação primeiro faz o mypy tentar resolver via `bool.__or__` e falha (`No overload variant of "__or__" of "bool"`).
- **Rotina de purge sem scheduler dedicado:** para o volume esperado do MVP, purge de linhas obsoletas (`refresh_tokens` expirados/revogados) rodando uma vez por inicialização da API, dentro do `lifespan` (mesmo padrão de `create_db_and_tables()`), é suficiente — não é necessário introduzir Celery/cron externo só para isso. Reavaliar só se o padrão de deploy (várias réplicas subindo/descendo com frequência, sem período de baixo tráfego) tornar o purge-no-startup ineficaz.

## Checkpointer — retomar aqui na próxima sessão (sessão 31, encerrada em 2026-07-30)

> Histórico das sessões 28/29/30 arquivado em `progress.md`. Este é o único Checkpointer ativo —
> os anteriores foram consolidados lá (§"Fase 13 — tarefas 1–4 concluídas", §"Fase 13 — main
> promovida e migration confirmada em produção" e §"Fase 13 — sincronização com o hardening e a
> limpeza de dívidas do front").

**Sessão só de documentação — nenhum código deste repositório mudou.** A pedido do usuário, esta
sessão leu o que aconteceu no front (sessões 31–35, que tinham ficado sem eco aqui) e sincronizou
`vision.md`, `roadmap.md` e `queue.md`, além de reestruturar as dívidas técnicas como a tabela
T1–T6 ordenada acima. **Não há bug em aberto, nem tarefa de código, deploy ou infraestrutura
pendente neste repositório.**

- **Estado do repositório:** branch `dev`, working tree limpo antes desta sessão (só as 4
  alterações de `.status/` desta sessão a commitar), sincronizado com `origin/dev`/`origin/main`
  no início da sessão. Nenhuma mudança de código, dependência ou infraestrutura — só os 4
  arquivos de `.status/`. Suíte completa (`pytest`/`ruff`/`black`/`mypy --strict`/`bandit`)
  reconfirmada verde ao final, sem necessidade real já que nada em `app/` mudou.
- **O que mudou do lado do front desde a última sincronização (sessão 30):** sessões 31–33 (já
  refletidas aqui antes), sessão 34 (hardening real em dispositivo físico — achou e corrigiu 7
  bugs, D28–D34, **todos do lado do front**; os dois mais próximos deste backend, D33/senha e
  D34/e-mail, **confirmaram que os schemas Pydantic aqui sempre estiveram corretos** — ver
  "Lições das sessões 34–35 do front" acima) e sessão 35 (limpeza de 5 dívidas técnicas de baixa
  prioridade do front, sem qualquer efeito neste repositório). Detalhe completo em `progress.md`
  §"Fase 13 — sincronização com o hardening e a limpeza de dívidas do front".
- **T1 (único item bloqueante, ambos os repositórios) — inalterado:** hardening ponta a ponta em
  dispositivo físico. A build EAS mais recente do front (`fa25bd21`, commit `3dcd0dd`) **segue
  sem confirmação de teste ponta a ponta pelo usuário** — mesmo estado documentado desde o fim da
  sessão 30. Não é tarefa de código: exige um device físico e não pode ser feita/simulada aqui.
- **Do lado do front, ainda não mergeada:** a branch `chore/tech-debt-cleanup` (sessão 35, front)
  está commitada mas aguardando revisão/merge em `dev` do lado de lá — não afeta este repositório
  de nenhuma forma, é só contexto para não estranhar se o front citar essa branch numa próxima
  conversa.
- **Próximo passo sugerido para a próxima sessão:** perguntar ao usuário se já rodou o
  hardening em dispositivo físico (T1); se sim, registrar o resultado e fechar a Fase 13/14
  formalmente em `roadmap.md`. Se não, não há nada mais a fazer neste repositório — sugerir T2–T6
  (seção "Dívidas técnicas e backlog" acima) como possíveis próximas frentes, a critério do
  usuário, só depois que T1 fechar.
