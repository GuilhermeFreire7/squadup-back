from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.core.config import get_settings
from app.core.database import create_db_and_tables, engine
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.routers import auth, health, matches, messages, observability, ratings, reports, users
from app.routers.messages import ws_router
from app.services.auth_service import purge_expired_refresh_tokens

configure_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    create_db_and_tables()
    with Session(engine) as session:
        purge_expired_refresh_tokens(session)
    yield


app = FastAPI(
    title=settings.app_name,
    description="API do SquadUp — conecta pessoas para a prática de esportes coletivos.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(observability.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(matches.router)
app.include_router(messages.router)
app.include_router(ws_router)
app.include_router(ratings.router)
app.include_router(reports.router)
