"""Application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import auth, entries

app = FastAPI(
    title="Nutrition API",
    description="Backend for the Calorie Tracker app: accounts, food entries, daily totals.",
    version="1.0.0",
)

# The PWA is served from a different origin, so the browser needs this to call
# the API at all. Tighten allow_origins to the real domain before production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
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
