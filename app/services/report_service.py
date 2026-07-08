from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.enums import ReportStatus
from app.models.match import Match
from app.models.report import Report
from app.models.user import User
from app.schemas.match import MatchRef
from app.schemas.report import ReportAction, ReportCreate, ReportRead, ReportUpdate
from app.services.user_service import build_public_profile

_ACTION_TO_STATUS = {
    ReportAction.ARCHIVE: ReportStatus.ARCHIVED,
    ReportAction.WARN: ReportStatus.WARNED,
    ReportAction.BAN: ReportStatus.BANNED,
}


def _get_user_or_404(session: Session, user_id: str) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "Usuário não encontrado."},
        )
    return user


def _get_report_or_404(session: Session, report_id: str) -> Report:
    report = session.get(Report, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "REPORT_NOT_FOUND", "message": "Denúncia não encontrada."},
        )
    return report


def build_report_read(session: Session, report: Report) -> ReportRead:
    return ReportRead(
        id=report.id,
        reported_user=build_public_profile(session, report.reported_user),
        reporter=build_public_profile(session, report.reporter_user),
        match=MatchRef.model_validate(report.match) if report.match_id else None,
        reason=report.reason,
        description=report.description,
        status=report.status,
        created_at=report.created_at,
    )


def create_report(session: Session, payload: ReportCreate, reporter: User) -> ReportRead:
    if payload.reported_user_id == reporter.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "CANNOT_REPORT_SELF",
                "message": "Você não pode denunciar a si mesmo.",
            },
        )

    _get_user_or_404(session, payload.reported_user_id)

    if payload.match_id is not None and session.get(Match, payload.match_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "MATCH_NOT_FOUND", "message": "Partida não encontrada."},
        )

    report = Report(
        reported_user_id=payload.reported_user_id,
        reporter_user_id=reporter.id,
        match_id=payload.match_id,
        reason=payload.reason,
        description=payload.description,
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return build_report_read(session, report)


def list_reports(session: Session) -> list[ReportRead]:
    reports = session.exec(
        select(Report).order_by(Report.created_at.desc())  # type: ignore[attr-defined]
    ).all()
    return [build_report_read(session, report) for report in reports]


def update_report_status(session: Session, report_id: str, payload: ReportUpdate) -> ReportRead:
    report = _get_report_or_404(session, report_id)

    if report.status != ReportStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "REPORT_ALREADY_RESOLVED",
                "message": "Esta denúncia já foi resolvida.",
            },
        )

    report.status = _ACTION_TO_STATUS[payload.action]
    session.add(report)
    session.commit()
    session.refresh(report)
    return build_report_read(session, report)
