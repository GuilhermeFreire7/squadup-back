import logging
import sys

import structlog


def configure_logging() -> None:
    """Configura logging estruturado em JSON (T5).

    O `request_id` gerado por `app.core.middleware.RequestContextMiddleware` é injetado
    automaticamente em cada linha via `structlog.contextvars` — não precisa ser passado
    explicitamente em cada chamada de log dentro de uma requisição.
    """
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )
