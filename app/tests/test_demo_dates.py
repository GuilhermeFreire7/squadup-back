from collections.abc import Generator
from datetime import date, time

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.demo_dates import main, plan_shift
from app.models.enums import ExperienceLevel, MatchStatus, Sport
from app.models.match import Match
from app.models.user import User


@pytest.fixture
def engine() -> Generator[Engine, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            User(
                id="u1",
                name="Alice",
                email="u1@example.com",
                hashed_password="x",
                age=25,
                location="Rio",
            )
        )
        for id_, day, status in [
            ("open-1", date(2026, 11, 24), MatchStatus.OPEN),
            ("full-1", date(2026, 11, 26), MatchStatus.FULL),
            ("cancel-1", date(2026, 11, 22), MatchStatus.CANCELLED),
            ("open-2", date(2026, 12, 8), MatchStatus.OPEN),
            ("closed-1", date(2026, 10, 9), MatchStatus.CLOSED),
        ]:
            session.add(
                Match(
                    id=id_,
                    sport=Sport.FOOTBALL,
                    title=f"Partida {id_}",
                    location="Arena",
                    date=day,
                    time=time(9, 0),
                    max_participants=10,
                    level=ExperienceLevel.INTERMEDIATE,
                    organizer_id="u1",
                    status=status,
                )
            )
        session.commit()
    yield engine


def _dates(engine: Engine) -> dict[str, date]:
    with Session(engine) as session:
        return {match.id: match.date for match in session.exec(select(Match)).all()}


def test_plan_moves_whole_weeks_keeping_spacing_and_weekday(engine: Engine) -> None:
    with Session(engine) as session:
        shifts = {s.match_id: s for s in plan_shift(session, date(2026, 12, 19))}

    # A mais cedo das deslocáveis (cancelada, 22/11) precisa de 27 dias para chegar a 19/12;
    # arredondado para 4 semanas (28 dias), ela cai em 20/12. Todas andam os mesmos 28 dias.
    assert shifts["cancel-1"].new_date == date(2026, 12, 20)
    assert shifts["open-1"].new_date == date(2026, 12, 22)
    assert shifts["full-1"].new_date == date(2026, 12, 24)
    assert shifts["open-2"].new_date == date(2027, 1, 5)
    assert all(s.new_date.weekday() == s.old_date.weekday() for s in shifts.values())
    assert "closed-1" not in shifts


def test_main_without_apply_does_not_write(
    engine: Engine, capsys: pytest.CaptureFixture[str]
) -> None:
    before = _dates(engine)

    assert main(["--start", "2026-12-19"], engine=engine) == 0

    assert _dates(engine) == before
    assert "Simulação" in capsys.readouterr().out


def test_main_with_apply_writes_and_is_idempotent(
    engine: Engine, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--start", "2026-12-19", "--apply"], engine=engine) == 0
    after_first = _dates(engine)

    assert after_first["cancel-1"] == date(2026, 12, 20)
    assert after_first["open-2"] == date(2027, 1, 5)
    assert after_first["closed-1"] == date(2026, 10, 9)

    assert main(["--start", "2026-12-19", "--apply"], engine=engine) == 0

    assert _dates(engine) == after_first
    assert "Nada a deslocar" in capsys.readouterr().out


def test_plan_is_empty_without_shiftable_matches() -> None:
    empty = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(empty)

    with Session(empty) as session:
        assert plan_shift(session, date(2026, 12, 19)) == []


def test_main_rejects_invalid_date(engine: Engine) -> None:
    with pytest.raises(SystemExit):
        main(["--start", "19/12/2026"], engine=engine)
