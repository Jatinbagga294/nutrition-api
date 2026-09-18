"""Application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import auth, entries

app = FastAPI(
    title="Nutrition API",
    description="Backend for the Calorie Tracker app: accounts, food entries, daily totals.",
    version="1.0.0",
)

# The PWA is served from a different origin, so the browser needs this to call
# the API at all. The allowed origins come from CORS_ORIGINS, so a deployment
# lists exactly the sites it serves instead of editing code.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(entries.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness probe for Docker, CI and the host platform."""
    return {"status": "ok"}
