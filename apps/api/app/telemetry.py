from __future__ import annotations

import logging

from fastapi import FastAPI

from app.settings import Settings

logger = logging.getLogger(__name__)


def configure_telemetry(app: FastAPI, settings: Settings) -> None:
    if not settings.otel_enabled:
        logger.info("OpenTelemetry disabled")
        return

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        logger.info("OpenTelemetry FastAPI instrumentation enabled")
    except Exception:  # pragma: no cover - defensive startup logging
        logger.exception(
            "Failed to configure OpenTelemetry instrumentation; "
            "continuing startup without telemetry"
        )
