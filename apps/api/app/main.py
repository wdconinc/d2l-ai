from fastapi import FastAPI

from app.logging import configure_logging
from app.settings import settings
from app.telemetry import configure_telemetry

configure_logging(settings.log_level)

app = FastAPI(title="d2l-ai API", version="0.1.0")


@app.on_event("startup")
def startup_event() -> None:
    configure_telemetry(app, settings)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict[str, str]:
    return {"status": "ready"}
