# backend/main.py
from pathlib import Path
import os
from dotenv import load_dotenv

# ✅ LOAD ENV FIRST (must be before importing anything that reads os.getenv)
ROOT_DIR = Path(__file__).resolve().parent.parent  # repo root
load_dotenv(ROOT_DIR / ".env", override=True)

# optional sanity check (remove later)
print("ENV LOADED:", bool(os.getenv("TWELVELABS_API_KEY")), bool(os.getenv("GEMINI_API_KEY")))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles

from backend.api.router import api_router
from backend.db.connect_db import connect_db
from backend.db.disconnect_db import disconnect_db
from backend.db.init_db import init_db
from backend.db.seed_demo_data import seed_demo_data

# Health
from backend.api.routers.health import router as health_router


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
    "http://localhost:5174",
    "http://127.0.0.1:5174",
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


app.include_router(health_router, prefix="/api")
app.include_router(api_router, prefix="/api")

app.mount("/media", StaticFiles(directory="backend/media"), name="media")