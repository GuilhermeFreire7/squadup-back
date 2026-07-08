# SquadUp — Roadmap Inicial do Backend

## Status de execução (atualizado em 2026-07-08)

| Fase | Descrição | Status |
|------|-----------|--------|
| Fase 1 | Estrutura inicial do projeto | 🟢 Concluída |
| Fase 2 | Modelagem de dados e migrations | 🟢 Concluída |
| Fase 3 | Autenticação | 🟢 Concluída |
| Fase 4 | Perfil de usuário | 🟢 Concluída |
| Fase 5 | Partidas — listagem, busca e detalhes | 🟢 Concluída |
| Fase 6 | Criação de partida | 🟢 Concluída |
| Fase 7 | Participação em partida | 🟢 Concluída |
| Fase 8 | Mensagens (chat da partida) | 🟢 Concluída |
| Fase 9 | Avaliação pós-partida | 🟢 Concluída |
| Fase 10 | Denúncia e moderação | 🟢 Concluída |
| Fase 11 | Hardening e integração final com o front | 🟡 Em andamento |
| Fase 12 | Refinamentos de contrato para integração com o front | ⚪ Não iniciada |

**Progresso geral:** 10/11 fases concluídas e mergeadas em `dev` · Fase 1 concluída e mergeada em `dev` (branch de trabalho principal; `main` ainda está atrasada) via `feature/fase-1-estrutura-inicial` (servidor FastAPI rodando, `/health` respondendo, SQLite conectado via SQLModel, Alembic configurado, `pytest`/`ruff`/`black` verdes). CI/CD (`feature/ci-pipelines`) também mergeado em `dev`. Fase 2 concluída e mergeada em `dev` (PR #18): models, migration inicial e seed espelhando o front. Fase 3 (Autenticação) concluída e mergeada em `dev` (PR #19, commit `a2366e0`): register/login/me com JWT. Fase 4 (Perfil de usuário) concluída e mergeada em `dev` (PR #20, commit `16b5915`): `GET/PATCH /users/me`, `GET /users/{id}` com métricas derivadas. Fase 5 (Partidas) concluída e mergeada em `dev` (PR #21, commit `72de758`): `GET /matches` com filtros, `GET /matches/{id}` com participantes e organizador expandidos. Fase 6 (Criação de partida) concluída e mergeada em `dev` (PR #22, commit `fff5490`): `POST /matches` com o usuário autenticado como organizador. Fase 7 (Participação em partida) concluída e mergeada em `dev` (PR #23, commit `95c13e2`): `POST /matches/{id}/join`, `POST /matches/{id}/leave`, `POST /matches/{id}/participants/{userId}/approve`, com `status` da partida recalculado automaticamente a partir da contagem de participantes confirmados. Fase 8 (Mensagens) concluída e mergeada em `dev` (PR #24, commit `25ff076`): `GET/POST /matches/{id}/messages`, restritos ao organizador ou a participantes confirmados. Fase 9 (Avaliação pós-partida) concluída e mergeada em `dev` (PR #25, commit `ffccd58`): `POST /matches/{id}/ratings/{userId}`, `GET /users/{id}/ratings`, com validação de `match.status == closed` e ambos os usuários `confirmed`. Fase 10 (Denúncia e moderação) concluída e mergeada em `dev` (PR #26, commit `b11b834`): `POST /reports`, `GET /reports`, `PATCH /reports/{id}` (`archive`/`warn`/`ban`), com RBAC mínimo via `get_current_admin`. Após o merge, `pip-audit` no CI motivou a troca de `python-jose` por `PyJWT` (commit `ffe7fa3`) para eliminar a dependência transitiva `ecdsa==0.19.2` (`PYSEC-2026-1325`, sem fix disponível), sem mudança de comportamento (`HS256` continua sendo o único algoritmo usado). Fase 11 (Hardening e integração final) iniciada na branch `feature/fase-11-hardening`: refresh token com rotação (`POST /auth/refresh`, `POST /auth/logout`, tabela `refresh_tokens`) e `POST /matches/{id}/close` (fechamento manual de partida pelo organizador) implementados e validados localmente (96 testes, 97.89% cobertura); demais itens da fase (revisão de cobertura, OpenAPI, CORS/produção, hospedagem, integração com o front) ainda não iniciados — ver `queue.md`. Ver `vision.md` para o contexto completo e `progress.md` para o histórico detalhado.

Stack proposta (ver `vision.md`, seção 5): Python + **FastAPI** · banco de dados relacional (PostgreSQL em produção, SQLite aceitável em dev) · ORM a definir (SQLModel ou SQLAlchemy + Pydantic) · Alembic para migrations · JWT para autenticação.

---

## 1. Objetivo do roadmap

Este roadmap organiza a construção do backend do SquadUp em uma ordem lógica de desenvolvimento, replicando — do lado do serviço — a mesma sequência de maturidade que o front-end (`../front`) já percorreu como protótipo com dados mockados. A ideia é que cada fase aqui destrave a substituição de **um** Context mockado do front por dados reais, permitindo integração incremental sem quebrar o que já funciona.

## 2. Estratégia de desenvolvimento

A ordem de desenvolvimento segue a lógica:

1. estruturar o projeto (FastAPI, banco, testes, lint);
2. modelar os dados e gerar as migrations;
3. construir autenticação real;
4. expor perfil de usuário;
5. expor partidas (listagem, busca, detalhes);
6. permitir criação de partidas;
7. permitir participação em partidas;
8. expor mensagens (chat da partida);
9. expor avaliações pós-partida, com validação de regra de negócio;
10. expor denúncias e moderação básica;
11. fechar com testes, documentação e integração final com o front.

Cada fase deve ser desenvolvida em branch própria e mergeada só depois que o endpoint correspondente for consumido com sucesso por uma tela real do front (não apenas testado via Swagger/Postman) — o mesmo princípio de "protótipo navegável" que guiou o front-end vale aqui como "API navegável".

## 3. Fase 1 — Estrutura inicial do projeto

### Objetivo

Criar a base técnica do backend.

### Tarefas

- Inicializar projeto FastAPI (Poetry ou `venv` + `requirements.txt`);
- Configurar banco de dados local (Docker Compose com Postgres, ou SQLite para começar);
- Configurar ORM (SQLModel ou SQLAlchemy + Pydantic v2) e Alembic para migrations;
- Configurar testes (`pytest` + `httpx`/`TestClient`);
- Configurar lint/format (`ruff` + `black`);
- Configurar CORS liberando o origin do Expo (`npm run web`) e do app mobile;
- Configurar variáveis de ambiente (`.env` + `pydantic-settings`);
- Definir estrutura de pastas (`app/{models,schemas,routers,services,core,tests}`).

### Resultado esperado

Servidor FastAPI rodando localmente (`uvicorn app.main:app --reload`), endpoint de healthcheck (`GET /health`) respondendo, banco de dados conectado, `pytest` executando (mesmo que só com o teste do healthcheck).

## 4. Fase 2 — Modelagem de dados e migrations

### Objetivo

Traduzir o modelo de dados do `vision.md` (seção 6) em tabelas reais.

### Tarefas

- Criar os modelos `User`, `Match`, `Participant` (tabela associativa Match↔User), `Message`, `Rating`, `Report`, com as chaves estrangeiras e enums descritos no `vision.md`;
- Gerar a migration inicial via Alembic;
- Criar um seed de dados de exemplo espelhando `../front/src/mocks/*.ts` (mesmos 6 usuários, mesmas ~13 partidas) para facilitar testes de integração ponta a ponta com o front sem precisar recriar dados manualmente.

### Resultado esperado

Banco de dados criado com todas as tabelas e relacionamentos; seed roda sem erro; é possível inspecionar os dados via `psql`/DBeaver e ver o mesmo cenário narrativo que hoje só existe em memória no front.

## 5. Fase 3 — Autenticação

### Casos de uso contemplados

- Cadastrar-se no sistema;
- Realizar login;
- Manter sessão autenticada.

### Tarefas

- `POST /auth/register` (hash de senha com `bcrypt`/`argon2`);
- `POST /auth/login` (retorna JWT);
- `GET /auth/me` (usuário autenticado a partir do token);
- Dependency de autenticação reutilizável nos demais routers;
- Refresh token — opcional nesta fase, pode ficar para a Fase 11.

### Resultado esperado

O front consegue substituir o `AuthContext` mockado por chamadas reais: cadastro e login retornam um token válido, e o app consegue manter a sessão entre reinicializações (via `expo-secure-store`, já fora do escopo deste repo, mas a API precisa suportar).

## 6. Fase 4 — Perfil de usuário

### Casos de uso contemplados

- Visualizar perfil (próprio e de terceiros);
- Editar perfil.

### Tarefas

- `GET /users/{id}` (perfil público);
- `GET /users/me` / `PATCH /users/me` (editar perfil);
- `average_rating` e `matches_played` como campos **derivados** (calculados a partir de `Rating`/`Participant` — nunca armazenados como fonte de verdade solta, para não divergirem dos dados reais).

### Resultado esperado

`PublicProfileScreen`, `MyProfileScreen` e `EditProfileScreen` do front consomem dados reais em vez de `MOCK_USERS`.

## 7. Fase 5 — Partidas: listagem, busca e detalhes

### Casos de uso contemplados

- Buscar partidas;
- Filtrar partidas;
- Visualizar detalhes de uma partida.

### Tarefas

- `GET /matches` com filtros de query string (esporte, data, local, nível, "só com vagas") — espelhando exatamente os filtros já implementados em `MatchFiltersContext` no front;
- `GET /matches/{id}` com participantes e organizador expandidos;
- Contagem de vagas disponíveis calculada a partir de `Participant.status == confirmed`, nunca um campo solto.

### Resultado esperado

`HomeScreen`, `SearchScreen`, `FiltersScreen` e `MatchDetailScreen` consomem partidas reais.

## 8. Fase 6 — Criação de partida

### Casos de uso contemplados

- Criar partida.

### Tarefas

- `POST /matches`, com o usuário autenticado como `organizer`;
- Validação de payload (nível, `allow_beginners`, `requires_approval`, `max_participants` > 0).

### Resultado esperado

`CreateMatchScreen` funcional de ponta a ponta, com a partida criada aparecendo de fato na listagem.

## 9. Fase 7 — Participação em partida

### Casos de uso contemplados

- Participar de partida;
- Cancelar participação;
- Aprovar/recusar solicitação (quando `requires_approval`).

### Tarefas

- `POST /matches/{id}/join` (cria `Participant` como `confirmed` ou `pending`, dependendo de `requires_approval`);
- `POST /matches/{id}/leave`;
- `POST /matches/{id}/participants/{userId}/approve` (organizador aprova solicitação pendente);
- Atualização automática de `status` da partida para `full` quando `confirmed == max_participants`.

### Resultado esperado

`MatchDetailScreen` reflete os 5 estados de participação já mapeados no front, agora persistentes entre sessões — isso resolve, do lado do backend, a dívida técnica D8 do front (*"Participação em partida local apenas"*).

## 10. Fase 8 — Mensagens (chat da partida)

### Casos de uso contemplados

- Conversar no grupo da partida.

### Tarefas

- `GET /matches/{id}/messages` (histórico, paginado);
- `POST /matches/{id}/messages` (nova mensagem, `created_at` gerado pelo servidor);
- Real-time via WebSocket é uma evolução possível, **não um requisito desta fase** — polling ou refetch no front é aceitável para o MVP.

### Resultado esperado

`MatchChatScreen` funcional com persistência real. Como efeito colateral, isso resolve por definição a dívida técnica D12 do front (*"timestamp de mensagem usa hora real vs. histórico mockado fixo"*) — no backend não existe mais a distinção entre "histórico mockado" e "mensagem nova", é tudo dado real com timestamp do servidor.

## 11. Fase 9 — Avaliação pós-partida

### Casos de uso contemplados

- Avaliar usuário.

### Tarefas

- `POST /matches/{id}/ratings/{userId}` com os 5 critérios (`punctuality`, `respect`, `behavior`, `presence`, `overall`);
- `GET /users/{id}/ratings` (avaliações recebidas, para exibir no perfil);
- **Validação de regra de negócio no servidor:** só é possível avaliar se `match.status == closed` e tanto o avaliador quanto o avaliado estavam `confirmed` nessa partida. O protótipo mockado do front tinha justamente essa inconsistência nos dados de exemplo (avaliações datadas antes da partida acontecer, corrigida manualmente na sessão 17) — no backend essa regra deixa de depender de dados bem-comportados e vira validação de fato.

### Resultado esperado

`PostMatchRatingScreen` e `RateUserScreen` funcionais; `average_rating` do perfil passa a refletir avaliações reais.

## 12. Fase 10 — Denúncia e moderação

### Casos de uso contemplados

- Denunciar usuário;
- Moderar denúncias (arquivar, advertir, banir).

### Tarefas

- `POST /reports`;
- `GET /reports` (lista para moderação — requer role de admin);
- `PATCH /reports/{id}` (ações: `archive`, `warn`, `ban`);
- RBAC mínimo: campo `role` em `User` (`user` | `admin`). O protótipo do front expõe o painel administrativo sem controle de acesso real (*"rota oculta sem RBAC, adequado ao escopo de protótipo"*) — no backend isso precisa virar controle de acesso de verdade, ainda que simples.

### Resultado esperado

`ReportUserScreen`, `AdminDashboardScreen` e `ReportDetailScreen` funcionais com dados reais e controle de acesso mínimo real.

## 13. Fase 11 — Hardening e integração final

### Objetivo

Preparar o backend para uso real com o front, encerrando a dependência de dados mockados.

### Tarefas

- Cobertura de testes automatizados (`pytest`) para os fluxos principais de cada fase anterior;
- Revisão da documentação OpenAPI gerada automaticamente pelo FastAPI (`/docs`) como contrato oficial para o front consumir;
- Configuração de CORS e variáveis de ambiente para produção;
- Deploy (Railway, Render ou Fly.io — a decidir; nenhuma escolha foi feita ainda);
- No front: substituir cada Context mockado (`AuthContext`, `MatchesContext`, `MatchFiltersContext`, `MessagesContext`, `RatingsContext`, `ReportsContext`) por hooks de React Query consumindo esta API, um de cada vez, mantendo os testes do front verdes a cada substituição.

### Resultado esperado

MVP funcional integrado ponta a ponta; o protótipo com dados mockados do front é aposentado.

## 14. Ordem sugerida de implementação

1. Estrutura inicial do projeto;
2. Modelagem de dados e migrations (com seed espelhando os mocks do front);
3. Autenticação;
4. Perfil de usuário;
5. Partidas — listagem, busca e detalhes;
6. Criação de partida;
7. Participação em partida;
8. Mensagens (chat da partida);
9. Avaliação pós-partida;
10. Denúncia e moderação;
11. Hardening e integração final com o front.

## 15. Critérios de aceite do MVP com backend

O backend desta etapa será considerado adequado se:

- cobrir os mesmos fluxos hoje navegáveis no protótipo do front (welcome → login → home → partida → chat → avaliação → denúncia), agora com dados persistidos entre sessões;
- expuser contratos de API (schemas Pydantic / OpenAPI) claros o bastante para o front migrar `src/types/index.ts` para tipos derivados desses contratos, sem precisar redesenhar telas;
- aplicar como validação real de servidor pelo menos as duas regras de negócio que o protótipo só respeitava "por convenção" nos dados mockados: (a) avaliação só depois da partida encerrada, com ambos confirmados; (b) vagas/`status` de partida sempre derivados da contagem real de participantes confirmados, nunca um campo solto que possa divergir.

## 16. Fora do escopo inicial

Herdado do `vision.md` (seção 8):

- geolocalização real (busca por proximidade com coordenadas e raio);
- chat em tempo real via WebSocket (a v1 pode ser poll/refetch);
- notificações push reais;
- upload real de imagens (avatar/fotos de partida) — pode começar com URLs externas;
- pagamento ou reserva real de quadras;
- sistema de moderação sofisticado (fila com SLA, múltiplos moderadores, auditoria).

Esses recursos poderão ser desenvolvidos em etapas futuras, após a validação do MVP integrado.

## 17. Próxima evolução após esta etapa

Depois do MVP funcional integrado:

- WebSocket para chat em tempo real;
- notificações push (Expo Notifications);
- geolocalização real e busca por proximidade;
- upload de imagens (avatar, fotos de partida) via storage (S3-compatible);
- testes de carga e observabilidade (logs estruturados, métricas);
- CI/CD automatizado para deploy do backend a cada merge.

---

## 18. Fase 12 — Refinamentos de contrato para integração com o front

> Originada de uma comparação campo-a-campo entre este backend e `../front/src/types`,
> `src/mocks`, `src/contexts` (sessão 18–19, documentada em
> `../front/.status/backend-contract.md`). O front já é o consumidor real desta API — esta fase
> fecha as últimas inconsistências de contrato e os itens pendentes da Fase 11 antes que o
> front comece a construir a camada de integração (`../front/.status/roadmap.md`, Fase 13).
> **É bloqueante para a Fase 13 do front** — os tipos/adapters de lá serão desenhados a partir
> do contrato que sair daqui.

### Objetivo

Eliminar as últimas assimetrias de contrato encontradas na comparação com o front e fechar os
itens remanescentes da Fase 11, deixando a API estável o suficiente para o front parar de
tratá-la como alvo em movimento.

### Decisões a tomar (ver `../front/.status/backend-contract.md` §6 para o raciocínio completo)

- **D-B:** expandir `rated_user` em `RatingRead` (hoje só `rated_user_id`), por consistência
  com o padrão já usado em `MessageRead.sender`/`ParticipantRead.user` (lição da Fase 8, ver
  `queue.md`).
- **D-C:** decidir se `RatingRead`/`ReportRead` ganham um `MatchRef` leve (`id, title, sport,
  date`) em vez de só `match_id`, para o front não precisar de uma segunda chamada para exibir
  a que partida uma avaliação/denúncia se refere.
- **D-D:** decidir se o backend passa a emitir uma `Message` de `type: system` automaticamente
  ao criar uma partida (o enum `MessageType.SYSTEM` já existe, mas nada o emite hoje) ou se essa
  funcionalidade é formalmente descartada do escopo (o front hoje só a simula em
  `src/mocks/messages.ts`).

### Tarefas

- Aplicar D-B: expandir `rated_user: PublicProfileRead` em `RatingRead`
  (`app/schemas/rating.py`), reaproveitando `build_public_profile` (mesmo padrão de
  `app/services/message_service.py`);
- Aplicar D-C (se aprovado): criar `MatchRef` (schema leve) e incluí-lo em `RatingRead.match` e
  `ReportRead.match`, substituindo/complementando os `match_id` soltos;
- Aplicar D-D (se aprovado): no serviço de criação de partida (`app/services/match_service.py`),
  inserir uma `Message` com `type=MessageType.SYSTEM` e texto padrão ao criar a partida;
- Finalizar os itens já conhecidos e pendentes da Fase 11 (`queue.md`, "Próxima tarefa"):
  CORS/variáveis de ambiente de produção, decisão de hospedagem, rotina de purge de
  `refresh_tokens`, avaliar necessidade de "logout de todos os dispositivos";
- Revisar `cors_origins` (`app/core/config.py`) para incluir a URL real do app publicado
  (Expo/EAS) assim que ela existir, não só os origins de dev;
- Após fechar as decisões acima, gerar novamente o OpenAPI (`/openapi.json`) e confirmar com o
  front que os schemas batem com o que `../front/.status/backend-contract.md` documentou —
  atualizar esse documento do lado do front se algo mudar aqui.

### Resultado esperado

Contrato de API estável e consistente (mesmo padrão de expansão de relacionamento em todos os
`Read` schemas), Fase 11 formalmente encerrada, e sinal verde documentado para o front iniciar
sua Fase 13 sem risco de retrabalho por mudança de schema no meio do caminho.
