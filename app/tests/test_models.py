from datetime import date, time

from sqlmodel import Session, select

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


def _make_user(session: Session, id_: str, name: str) -> User:
    user = User(
        id=id_,
        name=name,
        email=f"{id_}@example.com",
        hashed_password="hashed",
        age=25,
        location="Rio de Janeiro",
        favorite_sports=[Sport.FOOTBALL],
        level=ExperienceLevel.INTERMEDIATE,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _make_match(session: Session, organizer: User, max_participants: int = 4) -> Match:
    match = Match(
        sport=Sport.FOOTBALL,
        title="Pelada de teste",
        location="Campo de teste",
        date=date(2026, 1, 1),
        time=time(10, 0),
        max_participants=max_participants,
        level=ExperienceLevel.BEGINNER,
        organizer_id=organizer.id,
    )
    session.add(match)
    session.commit()
    session.refresh(match)
    return match


def test_create_user(session: Session) -> None:
    user = _make_user(session, "u1", "Alice")

    fetched = session.get(User, user.id)
    assert fetched is not None
    assert fetched.name == "Alice"
    assert fetched.level == ExperienceLevel.INTERMEDIATE
    assert fetched.favorite_sports == [Sport.FOOTBALL]


def test_match_organizer_relationship(session: Session) -> None:
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, organizer)

    session.refresh(match)
    assert match.organizer.id == organizer.id
    assert match.status == MatchStatus.OPEN


def test_participant_confirmed_count_matches_max_participants(session: Session) -> None:
    organizer = _make_user(session, "u1", "Alice")
    player = _make_user(session, "u2", "Bob")
    match = _make_match(session, organizer, max_participants=2)

    session.add(
        Participant(match_id=match.id, user_id=organizer.id, status=ParticipationStatus.CONFIRMED)
    )
    session.add(
        Participant(match_id=match.id, user_id=player.id, status=ParticipationStatus.CONFIRMED)
    )
    session.commit()
    session.refresh(match)

    confirmed = [p for p in match.participants if p.status == ParticipationStatus.CONFIRMED]
    assert len(confirmed) == match.max_participants


def test_message_belongs_to_match_and_sender(session: Session) -> None:
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, organizer)

    message = Message(
        match_id=match.id,
        sender_id=organizer.id,
        text="Bem-vindos!",
        type=MessageType.SYSTEM,
    )
    session.add(message)
    session.commit()
    session.refresh(message)

    assert message.match.id == match.id
    assert message.sender.id == organizer.id


def test_rating_requires_distinct_rater_and_rated(session: Session) -> None:
    organizer = _make_user(session, "u1", "Alice")
    player = _make_user(session, "u2", "Bob")
    match = _make_match(session, organizer)

    rating = Rating(
        rated_user_id=organizer.id,
        rater_user_id=player.id,
        match_id=match.id,
        punctuality=5,
        respect=5,
        behavior=5,
        presence=5,
        overall=5,
    )
    session.add(rating)
    session.commit()
    session.refresh(rating)

    assert rating.rated_user.id == organizer.id
    assert rating.rater_user.id == player.id
    assert rating.match.id == match.id


def test_report_can_be_created_without_match(session: Session) -> None:
    reported = _make_user(session, "u1", "Alice")
    reporter = _make_user(session, "u2", "Bob")

    report = Report(
        reported_user_id=reported.id,
        reporter_user_id=reporter.id,
        match_id=None,
        reason=ReportReason.SPAM,
        description="Spam no chat",
        status=ReportStatus.PENDING,
    )
    session.add(report)
    session.commit()
    session.refresh(report)

    assert report.match_id is None
    assert report.reported_user.id == reported.id
    assert report.reporter_user.id == reporter.id


def test_query_matches_by_sport(session: Session) -> None:
    organizer = _make_user(session, "u1", "Alice")
    _make_match(session, organizer)

    results = session.exec(select(Match).where(Match.sport == Sport.FOOTBALL)).all()
    assert len(results) == 1
