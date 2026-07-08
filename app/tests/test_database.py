from sqlmodel import Session

from app.core.database import get_session


def test_get_session_yields_a_session() -> None:
    generator = get_session()

    session = next(generator)
    assert isinstance(session, Session)

    generator.close()
