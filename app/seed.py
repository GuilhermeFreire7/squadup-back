"""Seed the local database with data mirroring ../squadup-app/src/mocks/*.ts.

Run with: python -m app.seed
"""

from datetime import date, datetime, time
from typing import cast

from sqlmodel import Session

from app.core.database import create_db_and_tables, engine
from app.core.security import hash_password
from app.models import Match, Message, Participant, Rating, Report, User
from app.models.enums import (
    ExperienceLevel,
    MatchStatus,
    MessageType,
    ParticipationStatus,
    ReportReason,
    ReportStatus,
    Sport,
)

# Dev/seed-only placeholder credential — never used outside local fixtures.
SEED_PASSWORD = "changeme123"  # nosec B105


def _user(
    id_: str,
    name: str,
    age: int,
    location: str,
    bio: str | None,
    favorite_sports: list[Sport],
    level: ExperienceLevel,
    is_verified: bool,
) -> User:
    local_part = name.lower().replace(" ", ".")
    return User(
        id=id_,
        name=name,
        email=f"{local_part}@squadup.dev",
        hashed_password=hash_password(SEED_PASSWORD),
        age=age,
        location=location,
        bio=bio,
        favorite_sports=favorite_sports,
        level=level,
        is_verified=is_verified,
    )


def seed(session: Session) -> None:
    system_user = User(
        id="system",
        name="Sistema",
        email="system@squadup.dev",
        hashed_password=hash_password(SEED_PASSWORD),
        age=0,
        location="—",
        favorite_sports=[],
        level=ExperienceLevel.BEGINNER,
        is_verified=True,
    )

    guilherme = _user(
        "user-1",
        "Guilherme Freire",
        28,
        "Botafogo, Rio de Janeiro",
        "Apaixonado por futebol desde criança. Jogo nas peladas do bairro toda semana.",
        [Sport.FOOTBALL, Sport.FUTSAL],
        ExperienceLevel.INTERMEDIATE,
        True,
    )
    ana = _user(
        "user-2",
        "Ana Lima",
        24,
        "Ipanema, Rio de Janeiro",
        "Jogo vôlei desde o colégio. Adoro conhecer novas pessoas pelo esporte!",
        [Sport.VOLLEYBALL, Sport.BASKETBALL],
        ExperienceLevel.INTERMEDIATE,
        True,
    )
    rafael = _user(
        "user-3",
        "Rafael Souza",
        32,
        "Leblon, Rio de Janeiro",
        "Bom de bola, melhor ainda na resenha pós-jogo.",
        [Sport.FOOTBALL],
        ExperienceLevel.ADVANCED,
        True,
    )
    juliana = _user(
        "user-4",
        "Juliana Costa",
        21,
        "Barra da Tijuca, Rio de Janeiro",
        "Iniciante no basquete, mas determinada! Aceito dicas com prazer.",
        [Sport.BASKETBALL, Sport.VOLLEYBALL],
        ExperienceLevel.BEGINNER,
        False,
    )
    thiago = _user(
        "user-5",
        "Thiago Ferreira",
        26,
        "Tijuca, Rio de Janeiro",
        "Futebol society e futsal. Pontual, comprometido e sem frescura.",
        [Sport.FUTSAL, Sport.FOOTBALL],
        ExperienceLevel.INTERMEDIATE,
        True,
    )
    beatriz = _user(
        "user-6",
        "Beatriz Rocha",
        29,
        "Flamengo, Rio de Janeiro",
        "Professora de educação física. Adoro organizar peladas e eventos esportivos.",
        [Sport.VOLLEYBALL, Sport.FOOTBALL, Sport.BASKETBALL],
        ExperienceLevel.ADVANCED,
        True,
    )

    users = [system_user, guilherme, ana, rafael, juliana, thiago, beatriz]
    session.add_all(users)
    session.flush()

    matches_data = [
        {
            "id": "match-1",
            "sport": Sport.FOOTBALL,
            "title": "Pelada de domingo na arena",
            "location": "Arena Botafogo — Rua General Polidoro, 400",
            "date": date(2026, 5, 25),
            "time": time(9, 0),
            "max_participants": 14,
            "level": ExperienceLevel.INTERMEDIATE,
            "description": "Jogo de campo gramado. Trazer chuteira e água. Colete fornecido.",
            "organizer_id": guilherme.id,
            "status": MatchStatus.OPEN,
            "allow_beginners": False,
            "requires_approval": False,
            "participants": [
                (guilherme.id, ParticipationStatus.CONFIRMED),
                (thiago.id, ParticipationStatus.CONFIRMED),
                (rafael.id, ParticipationStatus.CONFIRMED),
                (beatriz.id, ParticipationStatus.CONFIRMED),
            ],
        },
        {
            "id": "match-2",
            "sport": Sport.VOLLEYBALL,
            "title": "Vôlei misto no parque",
            "location": "Parque do Flamengo — Quadra 3",
            "date": date(2026, 5, 24),
            "time": time(10, 0),
            "max_participants": 12,
            "level": ExperienceLevel.BEGINNER,
            "description": "Jogo descontraído e animado! Iniciantes bem-vindos.",
            "organizer_id": ana.id,
            "status": MatchStatus.OPEN,
            "allow_beginners": True,
            "requires_approval": False,
            "participants": [
                (ana.id, ParticipationStatus.CONFIRMED),
                (juliana.id, ParticipationStatus.CONFIRMED),
                (guilherme.id, ParticipationStatus.PENDING),
            ],
        },
        {
            "id": "match-3",
            "sport": Sport.BASKETBALL,
            "title": "Racha de basquete — 3x3",
            "location": "Quadra Coberta Barra — Av. das Américas, 700",
            "date": date(2026, 5, 26),
            "time": time(19, 0),
            "max_participants": 6,
            "level": ExperienceLevel.INTERMEDIATE,
            "description": "Três contra três, jogo de pontos. Confirme presença com antecedência.",
            "organizer_id": beatriz.id,
            "status": MatchStatus.FULL,
            "allow_beginners": True,
            "requires_approval": True,
            "participants": [
                (beatriz.id, ParticipationStatus.CONFIRMED),
                (ana.id, ParticipationStatus.CONFIRMED),
                (juliana.id, ParticipationStatus.CONFIRMED),
                (thiago.id, ParticipationStatus.CONFIRMED),
                (guilherme.id, ParticipationStatus.CONFIRMED),
                (rafael.id, ParticipationStatus.CONFIRMED),
            ],
        },
        {
            "id": "match-4",
            "sport": Sport.FUTSAL,
            "title": "Futsal no Andaraí — quarta à noite",
            "location": "Centro Esportivo Andaraí — Quadra B",
            "date": date(2026, 5, 28),
            "time": time(20, 30),
            "max_participants": 10,
            "level": ExperienceLevel.INTERMEDIATE,
            "description": "Jogo fixo toda quarta. Galera boa. Colete azul e laranja.",
            "organizer_id": thiago.id,
            "status": MatchStatus.OPEN,
            "allow_beginners": True,
            "requires_approval": False,
            "participants": [
                (thiago.id, ParticipationStatus.CONFIRMED),
                (guilherme.id, ParticipationStatus.CONFIRMED),
            ],
        },
        {
            "id": "match-5",
            "sport": Sport.FOOTBALL,
            "title": "Society dos veteranos — sábado cedo",
            "location": "Campo do Fluminense — Laranjeiras",
            "date": date(2026, 5, 31),
            "time": time(7, 30),
            "max_participants": 16,
            "level": ExperienceLevel.ADVANCED,
            "description": "Galera experiente, jogo rápido e técnico. Chuteira obrigatória.",
            "organizer_id": rafael.id,
            "status": MatchStatus.OPEN,
            "allow_beginners": False,
            "requires_approval": True,
            "participants": [
                (rafael.id, ParticipationStatus.CONFIRMED),
                (guilherme.id, ParticipationStatus.CONFIRMED),
                (thiago.id, ParticipationStatus.CONFIRMED),
            ],
        },
        {
            "id": "match-6",
            "sport": Sport.VOLLEYBALL,
            "title": "Vôlei de praia — Barra da Tijuca",
            "location": "Praia da Barra da Tijuca — Posto 4",
            "date": date(2026, 6, 7),
            "time": time(9, 0),
            "max_participants": 8,
            "level": ExperienceLevel.INTERMEDIATE,
            "description": "Passeio e jogo combinados. Organização de transporte coletivo.",
            "organizer_id": ana.id,
            "status": MatchStatus.OPEN,
            "allow_beginners": True,
            "requires_approval": False,
            "participants": [
                (ana.id, ParticipationStatus.CONFIRMED),
                (beatriz.id, ParticipationStatus.CONFIRMED),
                (juliana.id, ParticipationStatus.CONFIRMED),
            ],
        },
        {
            "id": "match-7",
            "sport": Sport.BASKETBALL,
            "title": "Treino livre de basquete — iniciantes",
            "location": "SESC Tijuca — Quadra poliesportiva",
            "date": date(2026, 5, 27),
            "time": time(18, 0),
            "max_participants": 10,
            "level": ExperienceLevel.BEGINNER,
            "description": (
                "Espaço aberto para iniciantes aprenderem fundamentos e jogar à vontade."
            ),
            "organizer_id": beatriz.id,
            "status": MatchStatus.OPEN,
            "allow_beginners": True,
            "requires_approval": False,
            "participants": [
                (beatriz.id, ParticipationStatus.CONFIRMED),
                (juliana.id, ParticipationStatus.CONFIRMED),
            ],
        },
        {
            "id": "match-8",
            "sport": Sport.FUTSAL,
            "title": "Futsal feminino — quinta feira",
            "location": "Centro Esportivo Carioca — Quadra coberta",
            "date": date(2026, 5, 29),
            "time": time(19, 30),
            "max_participants": 10,
            "level": ExperienceLevel.INTERMEDIATE,
            "description": "Jogo exclusivo para mulheres. Ambiente seguro e descontraído.",
            "organizer_id": beatriz.id,
            "status": MatchStatus.OPEN,
            "allow_beginners": True,
            "requires_approval": False,
            "participants": [
                (beatriz.id, ParticipationStatus.CONFIRMED),
                (ana.id, ParticipationStatus.CONFIRMED),
                (juliana.id, ParticipationStatus.CONFIRMED),
            ],
        },
        {
            "id": "match-9",
            "sport": Sport.FOOTBALL,
            "title": "Pelada de aniversário — 7x7",
            "location": "Campo Sintético Leblon",
            "date": date(2026, 5, 30),
            "time": time(16, 0),
            "max_participants": 14,
            "level": ExperienceLevel.BEGINNER,
            "description": "Jogo comemorativo, todo mundo pode entrar. Churrasco depois!",
            "organizer_id": guilherme.id,
            "status": MatchStatus.OPEN,
            "allow_beginners": True,
            "requires_approval": False,
            "participants": [
                (guilherme.id, ParticipationStatus.CONFIRMED),
                (ana.id, ParticipationStatus.CONFIRMED),
                (rafael.id, ParticipationStatus.CONFIRMED),
                (juliana.id, ParticipationStatus.CONFIRMED),
                (thiago.id, ParticipationStatus.CONFIRMED),
                (beatriz.id, ParticipationStatus.CONFIRMED),
            ],
        },
        {
            "id": "match-10",
            "sport": Sport.FOOTBALL,
            "title": "Pelada cancelada — campo interditado",
            "location": "Arena da Zona Norte — Rio de Janeiro",
            "date": date(2026, 5, 22),
            "time": time(8, 0),
            "max_participants": 14,
            "level": ExperienceLevel.INTERMEDIATE,
            "description": "Campo em manutenção. Partida remarcada para próximo mês.",
            "organizer_id": rafael.id,
            "status": MatchStatus.CANCELLED,
            "allow_beginners": False,
            "requires_approval": False,
            "participants": [
                (rafael.id, ParticipationStatus.CANCELLED),
                (guilherme.id, ParticipationStatus.CANCELLED),
            ],
        },
        {
            "id": "match-11",
            "sport": Sport.TENNIS,
            "title": "Tênis casual — duplas mistas",
            "location": "Clube Fluminense — Quadra 4, Laranjeiras",
            "date": date(2026, 6, 1),
            "time": time(10, 0),
            "max_participants": 4,
            "level": ExperienceLevel.INTERMEDIATE,
            "description": "Partida de duplas. Nível moderado, foco na diversão.",
            "organizer_id": ana.id,
            "status": MatchStatus.OPEN,
            "allow_beginners": False,
            "requires_approval": False,
            "participants": [
                (ana.id, ParticipationStatus.CONFIRMED),
                (guilherme.id, ParticipationStatus.CONFIRMED),
            ],
        },
        {
            "id": "match-12",
            "sport": Sport.BASKETBALL,
            "title": "Basquete avançado — vagas esgotadas",
            "location": "Clube de Regatas Botafogo — Quadra 1",
            "date": date(2026, 6, 5),
            "time": time(7, 0),
            "max_participants": 2,
            "level": ExperienceLevel.ADVANCED,
            "description": "Partida fechada. Todas as vagas já foram preenchidas.",
            "organizer_id": rafael.id,
            "status": MatchStatus.FULL,
            "allow_beginners": False,
            "requires_approval": False,
            "participants": [
                (rafael.id, ParticipationStatus.CONFIRMED),
                (beatriz.id, ParticipationStatus.CONFIRMED),
            ],
        },
        {
            "id": "match-13",
            "sport": Sport.FOOTBALL,
            "title": "Pelada de maio — encerrada",
            "location": "Arena Botafogo — Rua General Polidoro, 400",
            "date": date(2026, 5, 10),
            "time": time(9, 0),
            "max_participants": 10,
            "level": ExperienceLevel.INTERMEDIATE,
            "description": "Partida já encerrada. Avalie os participantes!",
            "organizer_id": guilherme.id,
            "status": MatchStatus.CLOSED,
            "allow_beginners": False,
            "requires_approval": False,
            "participants": [
                (guilherme.id, ParticipationStatus.CONFIRMED),
                (thiago.id, ParticipationStatus.CONFIRMED),
                (rafael.id, ParticipationStatus.CONFIRMED),
                (beatriz.id, ParticipationStatus.CONFIRMED),
                (ana.id, ParticipationStatus.CONFIRMED),
            ],
        },
    ]

    for match_data in matches_data:
        participants_spec = cast(
            "list[tuple[str, ParticipationStatus]]", match_data.pop("participants")
        )
        match = Match.model_validate(match_data)
        session.add(match)
        session.flush()
        for user_id, status in participants_spec:
            session.add(Participant(match_id=match.id, user_id=user_id, status=status))

    session.flush()

    messages_data = [
        {
            "id": "msg-1-1",
            "match_id": "match-1",
            "sender_id": system_user.id,
            "hhmm": "09:00",
            "type": MessageType.SYSTEM,
            "text": "Partida criada por Guilherme Freire. Bem-vindos! 🎉",
        },
        {
            "id": "msg-1-2",
            "match_id": "match-1",
            "sender_id": guilherme.id,
            "hhmm": "09:10",
            "type": MessageType.MESSAGE,
            "text": "Galera, confirmem presença até amanhã!",
        },
        {
            "id": "msg-1-3",
            "match_id": "match-1",
            "sender_id": thiago.id,
            "hhmm": "09:20",
            "type": MessageType.MESSAGE,
            "text": "Confirmado! Posso levar coletes se precisar.",
        },
        {
            "id": "msg-1-4",
            "match_id": "match-1",
            "sender_id": rafael.id,
            "hhmm": "09:35",
            "type": MessageType.MESSAGE,
            "text": "Estarei lá. Chuteira society funciona no gramado?",
        },
        {
            "id": "msg-1-5",
            "match_id": "match-1",
            "sender_id": beatriz.id,
            "hhmm": "09:38",
            "type": MessageType.MESSAGE,
            "text": "Vai ser ótimo! Ansiosa.",
        },
        {
            "id": "msg-1-6",
            "match_id": "match-1",
            "sender_id": guilherme.id,
            "hhmm": "09:42",
            "type": MessageType.MESSAGE,
            "text": "Rafael, pode sim! Campo gramado aceita tudo.",
        },
        {
            "id": "msg-1-7",
            "match_id": "match-1",
            "sender_id": system_user.id,
            "hhmm": "09:45",
            "type": MessageType.SYSTEM,
            "text": "Partida amanhã às 09:00! Não esqueça de confirmar presença. ⚽",
        },
        {
            "id": "msg-3-1",
            "match_id": "match-3",
            "sender_id": system_user.id,
            "hhmm": "17:00",
            "type": MessageType.SYSTEM,
            "text": "Partida criada por Beatriz Rocha. Bem-vindos! 🏀",
        },
        {
            "id": "msg-3-2",
            "match_id": "match-3",
            "sender_id": beatriz.id,
            "hhmm": "17:15",
            "type": MessageType.MESSAGE,
            "text": "Olá pessoal! Jogo de 3x3, venham preparados.",
        },
        {
            "id": "msg-3-3",
            "match_id": "match-3",
            "sender_id": ana.id,
            "hhmm": "17:30",
            "type": MessageType.MESSAGE,
            "text": "Animada! Nunca joguei 3x3, vai ser divertido.",
        },
        {
            "id": "msg-3-4",
            "match_id": "match-3",
            "sender_id": juliana.id,
            "hhmm": "17:40",
            "type": MessageType.MESSAGE,
            "text": "Vou levar água extra pra todo mundo!",
        },
        {
            "id": "msg-3-5",
            "match_id": "match-3",
            "sender_id": thiago.id,
            "hhmm": "17:45",
            "type": MessageType.MESSAGE,
            "text": "Chegando 15min antes pra esquentar.",
        },
        {
            "id": "msg-3-6",
            "match_id": "match-3",
            "sender_id": guilherme.id,
            "hhmm": "17:50",
            "type": MessageType.MESSAGE,
            "text": "Pode ser 3x3 ou 2x2 dependendo de quantos vierem.",
        },
        {
            "id": "msg-3-7",
            "match_id": "match-3",
            "sender_id": rafael.id,
            "hhmm": "17:55",
            "type": MessageType.MESSAGE,
            "text": "Estou dentro! Essa quadra é excelente.",
        },
        {
            "id": "msg-3-8",
            "match_id": "match-3",
            "sender_id": system_user.id,
            "hhmm": "18:00",
            "type": MessageType.SYSTEM,
            "text": "Todas as vagas foram preenchidas! ✅",
        },
    ]
    for msg in messages_data:
        hhmm = str(msg.pop("hhmm"))
        hour, minute = (int(part) for part in hhmm.split(":"))
        created_at = datetime.combine(date(2026, 5, 25), time(hour, minute))
        session.add(Message.model_validate({**msg, "created_at": created_at}))

    ratings_data = [
        {
            "id": "rating-1",
            "rated_user_id": guilherme.id,
            "rater_user_id": thiago.id,
            "match_id": "match-13",
            "punctuality": 5,
            "respect": 5,
            "behavior": 5,
            "presence": 4,
            "overall": 5,
            "comment": "Guilherme é pontual demais, sempre aparece antes de todo mundo. "
            "Ótimo de jogar junto!",
            "created_at": datetime(2026, 5, 10, 14, 0, 0),
        },
        {
            "id": "rating-2",
            "rated_user_id": guilherme.id,
            "rater_user_id": beatriz.id,
            "match_id": "match-13",
            "punctuality": 4,
            "respect": 5,
            "behavior": 5,
            "presence": 5,
            "overall": 5,
            "comment": "Joga limpo e anima o time. Recomendo!",
            "created_at": datetime(2026, 5, 10, 15, 30, 0),
        },
        {
            "id": "rating-3",
            "rated_user_id": ana.id,
            "rater_user_id": guilherme.id,
            "match_id": "match-13",
            "punctuality": 5,
            "respect": 5,
            "behavior": 5,
            "presence": 5,
            "overall": 5,
            "comment": "Ana organiza tudo com muita competência. Pelada fluiu muito bem.",
            "created_at": datetime(2026, 5, 10, 16, 0, 0),
        },
        {
            "id": "rating-4",
            "rated_user_id": ana.id,
            "rater_user_id": beatriz.id,
            "match_id": "match-13",
            "punctuality": 5,
            "respect": 5,
            "behavior": 4,
            "presence": 5,
            "overall": 5,
            "comment": None,
            "created_at": datetime(2026, 5, 11, 9, 0, 0),
        },
        {
            "id": "rating-5",
            "rated_user_id": rafael.id,
            "rater_user_id": guilherme.id,
            "match_id": "match-13",
            "punctuality": 4,
            "respect": 4,
            "behavior": 5,
            "presence": 4,
            "overall": 4,
            "comment": "Bom jogador, mas às vezes chega no limite do horário. "
            "No geral, ótimo companheiro.",
            "created_at": datetime(2026, 5, 10, 14, 30, 0),
        },
        {
            "id": "rating-6",
            "rated_user_id": beatriz.id,
            "rater_user_id": ana.id,
            "match_id": "match-13",
            "punctuality": 5,
            "respect": 5,
            "behavior": 5,
            "presence": 5,
            "overall": 5,
            "comment": "Beatriz é incrível! Organiza, motiva e ainda joga muito bem.",
            "created_at": datetime(2026, 5, 11, 10, 0, 0),
        },
        {
            "id": "rating-7",
            "rated_user_id": thiago.id,
            "rater_user_id": rafael.id,
            "match_id": "match-13",
            "punctuality": 5,
            "respect": 5,
            "behavior": 5,
            "presence": 4,
            "overall": 5,
            "comment": "Thiago joga muito e ainda anima todo mundo. Vale chamar sempre.",
            "created_at": datetime(2026, 5, 11, 11, 0, 0),
        },
    ]
    for rating in ratings_data:
        session.add(Rating.model_validate(rating))

    reports_data = [
        {
            "id": "report-1",
            "reported_user_id": rafael.id,
            "reporter_user_id": guilherme.id,
            "match_id": "match-1",
            "reason": ReportReason.BAD_BEHAVIOR,
            "description": "Ficou discutindo com outros jogadores durante a pelada.",
            "created_at": datetime(2026, 5, 26, 14, 0, 0),
            "status": ReportStatus.PENDING,
        },
        {
            "id": "report-2",
            "reported_user_id": juliana.id,
            "reporter_user_id": ana.id,
            "match_id": "match-2",
            "reason": ReportReason.NO_SHOW,
            "description": "Confirmou presença e não apareceu, sem avisar ninguém.",
            "created_at": datetime(2026, 5, 25, 9, 30, 0),
            "status": ReportStatus.PENDING,
        },
        {
            "id": "report-3",
            "reported_user_id": thiago.id,
            "reporter_user_id": beatriz.id,
            "match_id": None,
            "reason": ReportReason.SPAM,
            "description": "Enviou links de propaganda no chat da partida diversas vezes.",
            "created_at": datetime(2026, 5, 20, 18, 0, 0),
            "status": ReportStatus.WARNED,
        },
        {
            "id": "report-4",
            "reported_user_id": ana.id,
            "reporter_user_id": beatriz.id,
            "match_id": "match-13",
            "reason": ReportReason.VIOLENCE,
            "description": "Empurrou outro participante após uma jogada mais dura.",
            "created_at": datetime(2026, 5, 10, 11, 30, 0),
            "status": ReportStatus.ARCHIVED,
        },
    ]
    for report in reports_data:
        session.add(Report.model_validate(report))

    session.commit()


def main() -> None:
    create_db_and_tables()
    with Session(engine) as session:
        existing = session.get(User, "user-1")
        if existing is not None:
            print("Seed skipped: database already has data.")
            return
        seed(session)
        print("Seed completed: 7 users (incl. system), 13 matches, messages, ratings, reports.")


if __name__ == "__main__":
    main()
