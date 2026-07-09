# SquadUp — Visão do Produto Backend

## 1. Visão geral

O SquadUp é um aplicativo mobile voltado para conectar pessoas interessadas na prática de esportes coletivos, facilitando a descoberta, criação e participação em partidas. A proposta central do produto é reduzir a dificuldade de encontrar pessoas, grupos e oportunidades para praticar esportes como futebol, vôlei e basquete.

Este repositório é o **backend** do SquadUp: a API e a camada de persistência que sustentam o front-end mobile (React Native + Expo), hoje um protótipo navegável com dados mockados. Este documento assume o mesmo papel do `vision.md` do front-end — descreve o que o backend precisa ser, por quê, e o que fica fora do escopo nesta etapa — mas do ponto de vista de serviço/API, não de tela.

## 2. Contexto: de onde este backend nasce

O front-end (`../front`) foi construído primeiro, como protótipo acadêmico, com **todos os dados mockados em memória** (`src/mocks/*.ts`) e nenhuma chamada de rede. O roadmap do front (`../front/.status/roadmap.md`, seção 18 "Próxima evolução após o protótipo") já previa esta etapa:

> refinar os casos de uso; modelar banco de dados; definir contratos da API; implementar backend com **FastAPI**; integrar frontend com backend; testar fluxos principais; preparar versão funcional do MVP.

Ou seja: este backend não parte de um design em aberto — ele precisa **replicar e servir de fonte de verdade** para os contratos de dados que o front já modelou e usa em produção de protótipo (`../front/src/types/index.ts`). O CLAUDE.md do front já declara essa expectativa: *"Maintain a single source of truth for API contracts by referencing the backend schemas"* — a partir do momento em que este backend existir, o front deve passar a referenciar os schemas daqui, e não o contrário.

## 3. Objetivo desta etapa (PG2)

Sair do protótipo com dados mockados para um **MVP funcional com persistência real**, mantendo os mesmos fluxos e telas já validados no front, mas com:

- autenticação real (hoje o `AuthContext` do front apenas simula login/cadastro em memória);
- persistência em banco de dados (hoje `MatchesContext`, `MessagesContext`, `RatingsContext`, `ReportsContext` vivem só em `useState` no cliente e se perdem a cada reload);
- contratos de API estáveis que o front possa consumir via React Query (já previsto no stack do front: *"React Query (TanStack) para estado de servidor quando houver backend"*).

O objetivo não é redesenhar os casos de uso — é dar uma camada de serviço real ao que o protótipo já provou funcionar.

## 4. Pilares do produto (herdados do front, mesma numeração)

### 4.1 Pilar Social

Conexão entre usuários, formação de grupos, confiança. O backend sustenta isso com: perfis de usuário persistentes, reputação calculada a partir de avaliações reais (não mais uma lista estática), e histórico de participação verdadeiro.

### 4.2 Pilar Logístico

Organização prática da partida: local, horário, modalidade, vagas, status. O backend sustenta isso com: o recurso de partidas como fonte única de verdade sobre vagas disponíveis e status (hoje o front tem uma dívida técnica conhecida — `MatchDetailScreen` alterava participação só em `useState` local antes de existir `MatchesContext`; a versão com backend deve eliminar qualquer duplicação de estado desse tipo).

### 4.3 Pilar Saúde

Incentivo à prática recorrente. Inicial e secundário nesta etapa também no backend — não há necessidade de dados médicos ou tracking avançado, só o suficiente para o front exibir histórico e frequência (`matchesPlayed`, participações passadas).

## 5. Stack proposta

Definida previamente no roadmap do front, não é uma escolha nova deste documento:

- **API:** Python + **FastAPI**
- **Persistência:** banco de dados relacional (o modelo abaixo é claramente relacional — usuários, partidas, participações N:N, mensagens, avaliações e denúncias todas com chaves estrangeiras bem definidas). PostgreSQL é a escolha natural para produção; SQLite é aceitável para desenvolvimento local. A escolha do ORM (SQLModel/SQLAlchemy) e da estratégia de migração (Alembic) fica em aberto para o roadmap técnico deste repositório.
- **Autenticação:** a decidir (JWT é o caminho mais direto para consumo por um app mobile via Expo); precisa cobrir cadastro, login e sessão persistente — hoje simulados no `AuthContext` do front.
- **Contratos:** os schemas Pydantic do FastAPI devem gerar a documentação OpenAPI que o front passa a usar como referência de tipos, substituindo gradualmente `src/types/index.ts` como fonte da verdade.

## 6. Modelo de dados (ponto de partida)

Extraído diretamente de `../front/src/types/index.ts` e dos mocks correspondentes (`../front/src/mocks/*.ts`), que já validam este modelo com dados de exemplo plausíveis. Nomes e tipos abaixo são o ponto de partida para os schemas Pydantic e as tabelas — ajustes são esperados ao desenhar as migrações.

### User

`id, name, photo_url?, age, location, bio?, favorite_sports[Sport], level (beginner|intermediate|advanced), average_rating (derivado das Ratings recebidas), matches_played (derivado das Participations confirmadas), is_verified`

### Match

`id, sport (football|volleyball|basketball|tennis|futsal|other), title, location, date, time, max_participants, level, description?, organizer_id → User, status (open|full|pending_approval|closed|cancelled), allow_beginners, requires_approval`

### Participant (tabela associativa Match↔User)

`match_id, user_id, status (confirmed|pending|cancelled)` — `full`/vagas esgotadas deve ser **calculado** a partir da contagem de `confirmed`, nunca um campo solto duplicado.

### Message

`id, match_id → Match, sender_id → User, text, created_at (timestamp real do servidor — o protótipo tem uma dívida técnica conhecida de misturar hora real com histórico mockado fixo; no backend isso deixa de ser um problema por definição), type (message|system)`

### Rating

`id, rated_user_id → User, rater_user_id → User, match_id → Match, criteria { punctuality, respect, behavior, presence, overall } (1–5 cada), comment?, created_at`

Regra de negócio a validar no backend (o protótipo não impõe isso, mas deveria): uma avaliação só é válida se `match.status == closed` e ambos os usuários estavam `confirmed` nessa partida — o protótipo mockado tinha justamente essa inconsistência (avaliações datadas antes da partida acontecer) corrigida manualmente nos dados de exemplo; no backend essa regra deve ser uma validação real, não uma convenção de dados.

### Report

`id, reported_user_id → User, reporter_user_id → User, match_id → Match?, reason (bad_behavior|violence|no_show|hate_speech|spam|fake_info|other), description, created_at, status (pending|archived|warned|banned)`

## 7. Escopo desta etapa

Endpoints mínimos para cobrir, com dados reais, os mesmos fluxos já navegáveis no protótipo do front:

- cadastro e login de usuário (com sessão real);
- CRUD de partidas (criar, listar com filtro por esporte/local/data/nível/vagas, detalhar);
- participação em partida (confirmar, cancelar, aprovar solicitação quando `requires_approval`);
- mensagens da partida (listar histórico, enviar nova mensagem — tempo real via WebSocket é uma evolução possível, não um requisito desta etapa);
- avaliação pós-partida (submeter, listar avaliações recebidas de um usuário);
- denúncia de usuário e painel de moderação básico (arquivar, advertir, banir — hoje simulado sem RBAC real no `AdminDashboardScreen` do front).

## 8. Fora do escopo nesta etapa

Herdado do front (`vision.md`, seção 14) e ainda válido do lado do backend:

- chat em tempo real via WebSocket (a v1 pode ser poll/REST);
- upload real de imagens (avatar/fotos de partida) — pode começar com URLs externas;
- pagamento ou reserva real de quadras;
- sistema de moderação sofisticado (fila com SLA, múltiplos moderadores, auditoria) — o suficiente é replicar as 3 ações já previstas no protótipo (arquivar, advertir, banir).

**Atualização (2026-07-08):** geolocalização real e notificações push reais **saíram desta
lista** — eram o plano original do produto desde o início (não escopo novo), e o autor
confirmou que serão implementadas de fato, não só citadas como trabalho futuro no TCC. Ver
`roadmap.md` §19 (Fase 13) para o detalhamento — fase registrada e **bloqueada até a Fase 13 do
front (`../front/.status/roadmap.md` §19) terminar**, para não construir sobre um contrato de
API ainda em mudança. (Mesmo número "13" nos dois lados por coincidência — cada repositório
numera suas próprias fases de forma independente, mesmo padrão já usado no projeto.)

## 9. Critérios de sucesso do MVP com backend

- o front consegue substituir cada Context mockado (`AuthContext`, `MatchesContext`, `MessagesContext`, `RatingsContext`, `ReportsContext`) por chamadas reais via React Query, sem precisar redesenhar telas;
- os mesmos fluxos hoje navegáveis no protótipo (welcome → login → home → partida → chat → avaliação → denúncia) continuam funcionando ponta a ponta, agora com dados persistidos entre sessões;
- os contratos de API (schemas Pydantic / OpenAPI) tornam-se a fonte de verdade que o front referencia, substituindo `src/types/index.ts` como a definição canônica dos tipos compartilhados.

## 10. Observações para o roadmap técnico deste repositório

Este documento é só a visão — o `roadmap.md` e o `queue.md` deste repositório (ainda não criados) devem detalhar a ordem de implementação, decisões de stack em aberto (ORM, estratégia de auth, hospedagem) e as tarefas técnicas propriamente ditas, seguindo o mesmo padrão de `.status/` já em uso no front-end (`../front/.status/`).
