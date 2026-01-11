from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db.init_db import init_db
from backend.api.routers import vaults, cards, share

from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles

@asynccontextmanager
def lifespan(app: FastAPI):

    # initializing DB
    init_db()

    yield

    # shutdown code
    # (none for now)
app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:5173",
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
app.mount("/media", StaticFiles(directory="backend/media"), name="media")
