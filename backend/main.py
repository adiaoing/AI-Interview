import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from api.sessions import router as sessions_router
from api.tts import router as tts_router
from api.technical import router as technical_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Friday — AI Interview Coach",
    version="1.0.0",
    lifespan=lifespan,
)

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
app.include_router(tts_router, prefix="/tts", tags=["tts"])
app.include_router(technical_router, prefix="/sessions", tags=["technical"])


@app.get("/health")
async def health():
    return {"status": "ok"}
