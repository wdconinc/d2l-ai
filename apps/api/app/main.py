from __future__ import annotations

from fastapi import FastAPI

from app.lti.routes import router as lti_router

app = FastAPI(title="d2l-ai api")
app.include_router(lti_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
