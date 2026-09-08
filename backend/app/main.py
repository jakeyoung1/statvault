"""StatVault FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, keys, metrics, nba, nfl

app = FastAPI(
    title="StatVault API",
    version="2.0.0",
    description="Premium multi-sport advanced metrics — MLB (ERA, FIP), "
    "NFL (ANY/A), NBA (TS%). Authenticate with the 'X-API-Key' header. "
    "Premium endpoints are metered against a monthly quota.",
)

# Accept the configured origin plus the localhost/127.0.0.1 dev variants,
# which the browser treats as distinct origins for CORS.
_dev_origins = {
    settings.frontend_origin,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
}
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(_dev_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(keys.router)
app.include_router(metrics.router)
app.include_router(nfl.router)
app.include_router(nba.router)


@app.get("/", tags=["health"])
def root() -> dict:
    return {"service": "StatVault API", "version": "1.0.0", "docs": "/docs"}


@app.get("/api/v1/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}
