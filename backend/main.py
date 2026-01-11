# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.api.router import api_router
from backend.db.connect_db import connect_db
from backend.db.disconnect_db import disconnect_db
from backend.db.init_db import init_db
from backend.db.seed_demo_data import seed_demo_data
from backend.api.routers import vaults, cards, share
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from dotenv import load_dotenv
import os

# Health
from backend.api.routers.health import router as health_router
# Health

# 🔴 LOAD ENV FIRST — BEFORE ANY OTHER IMPORTS
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# sanity check (remove later)
print("ENV LOADED:", bool(os.getenv("TWELVELABS_API_KEY")), bool(os.getenv("GEMINI_API_KEY")))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    connect_db()
    seed_demo_data()
    yield
    disconnect_db()

app = FastAPI(lifespan=lifespan)

origins = [
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {"ok": True}

app.include_router(vaults.router, prefix="/api", tags=["vaults"])
app.include_router(cards.router, prefix="/api", tags=["cards"])
app.include_router(share.router, prefix="/api", tags=["share"])
app.include_router(health_router, prefix="/api")
app.include_router(api_router, prefix="/api")
app.mount("/media", StaticFiles(directory="backend/media"), name="media")