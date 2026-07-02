from sqlmodel import Session, select

from app.models import Match, Message, Participant, Rating, Report, User
from app.seed import seed


def test_seed_populates_expected_row_counts(session: Session) -> None:
    seed(session)

    assert len(session.exec(select(User)).all()) == 7
    assert len(session.exec(select(Match)).all()) == 13
    assert len(session.exec(select(Participant)).all()) == 43
    assert len(session.exec(select(Message)).all()) == 15
    assert len(session.exec(select(Rating)).all()) == 7
    assert len(session.exec(select(Report)).all()) == 4


def test_seed_match_3_is_full_when_confirmed_equals_max(session: Session) -> None:
    seed(session)

    match = session.get(Match, "match-3")
    assert match is not None
    confirmed = [p for p in match.participants if p.status.value == "confirmed"]
    assert len(confirmed) == match.max_participants
