"""Desloca as datas das partidas da demonstração para que nenhuma fique no passado.

As partidas abertas, lotadas e canceladas do seed de produção têm datas fixas. Perto da defesa,
elas passariam a aparecer como "abertas" em datas que já passaram. Este script move todas
juntas, mantendo o espaçamento entre elas, para que a mais cedo caia em ``--start`` ou até 6 dias
depois. O deslocamento é sempre em semanas inteiras, porque vários títulos citam o dia da semana
("Pelada de domingo", "quarta à noite"). Partidas encerradas e o histórico (mensagens,
avaliações, denúncias) não mudam.

Roda em modo de simulação por padrão: mostra o que mudaria e não grava nada. Só grava com
``--apply``. Rodar de novo com o mesmo ``--start`` não desloca outra vez, porque a partida mais
cedo já estará nessa data ou depois dela.

Uso, com a ``DATABASE_URL`` do banco que se quer ajustar (ex.: a do Neon)::

    python -m app.demo_dates --start 2026-12-19            # simulação
    python -m app.demo_dates --start 2026-12-19 --apply    # grava
"""

import argparse
import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.engine import Engine
from sqlmodel import Session, col, select

from app.models.enums import MatchStatus
from app.models.match import Match

SHIFTABLE_STATUSES = (MatchStatus.OPEN, MatchStatus.FULL, MatchStatus.CANCELLED)


@dataclass(frozen=True)
class DateShift:
    match_id: str
    title: str
    old_date: date
    new_date: date


def plan_shift(session: Session, start: date) -> list[DateShift]:
    """Calcula o deslocamento sem gravar. Lista vazia se não houver nada a mover."""
    matches = session.exec(
        select(Match)
        .where(col(Match.status).in_(SHIFTABLE_STATUSES))
        .order_by(col(Match.date), col(Match.id))
    ).all()
    if not matches:
        return []

    days_needed = (start - min(match.date for match in matches)).days
    if days_needed <= 0:
        # A partida mais cedo já está em `start` ou depois: nada a fazer.
        return []
    # Arredonda para semanas inteiras, preservando o dia da semana de cada partida.
    offset = timedelta(weeks=math.ceil(days_needed / 7))

    return [
        DateShift(
            match_id=match.id,
            title=match.title,
            old_date=match.date,
            new_date=match.date + offset,
        )
        for match in matches
    ]


def apply_shift(session: Session, shifts: Sequence[DateShift]) -> None:
    for shift in shifts:
        match = session.get(Match, shift.match_id)
        if match is None:
            continue
        match.date = shift.new_date
        session.add(match)
    session.commit()


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m app.demo_dates",
        description="Desloca as datas das partidas abertas, lotadas e canceladas da demo.",
    )
    parser.add_argument(
        "--start",
        required=True,
        type=date.fromisoformat,
        help="Data (AAAA-MM-DD) a partir da qual deve cair a partida mais cedo.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Grava as novas datas. Sem esta opção, só mostra o que mudaria.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None, engine: Engine | None = None) -> int:
    args = _parse_args(argv)
    if engine is None:
        from app.core.database import engine as default_engine

        engine = default_engine

    with Session(engine) as session:
        shifts = plan_shift(session, args.start)
        if not shifts:
            print(
                "Nada a deslocar: nenhuma partida aberta, lotada ou cancelada "
                f"antes de {args.start}."
            )
            return 0

        offset_days = (shifts[0].new_date - shifts[0].old_date).days
        print(f"Deslocamento de {offset_days} dias em {len(shifts)} partidas:")
        for shift in shifts:
            print(f"  {shift.match_id}: {shift.old_date} -> {shift.new_date}  ({shift.title})")

        if not args.apply:
            print("Simulação: nada foi gravado. Rode de novo com --apply para gravar.")
            return 0

        apply_shift(session, shifts)
        print("Datas gravadas.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
