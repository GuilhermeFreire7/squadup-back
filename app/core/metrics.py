from prometheus_client import Counter, Histogram

REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total de requisições HTTP recebidas, por método/rota/status.",
    ["method", "path", "status_code"],
)

REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "Duração das requisições HTTP em segundos, por método/rota.",
    ["method", "path"],
)
