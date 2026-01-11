# backend/main.py
from pathlib import Path
from dotenv import load_dotenv

# 🔴 LOAD ENV FIRST — BEFORE ANY OTHER IMPORTS
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# sanity check (remove later)
import os
print("ENV LOADED:", bool(os.getenv("TWELVELABS_API_KEY")), bool(os.getenv("GEMINI_API_KEY")))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.api.router import api_router
from backend.db.connect_db import connect_db
from backend.db.disconnect_db import disconnect_db
from backend.db.init_db import init_db
from backend.db.seed_demo_data import seed_demo_data

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    connect_db()
    seed_demo_data()
    yield
    disconnect_db()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")