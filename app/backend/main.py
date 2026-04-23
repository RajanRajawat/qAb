from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os, pathlib
from contextlib import asynccontextmanager
from src.register import register_router
from src.login import login_router
from src.agent import agent_router
from src.runner import runner_router
from src.custom_db import db_router
from src.knowledge_base import kb_router
from src.data_query import data_query_router
from src.tool_config import tool_config_router
from utils.loggers import logger
load_dotenv()


FRONTEND_DIR = pathlib.Path(__file__).parent.parent / "frontend"

app = FastAPI()

app.add_middleware(  
    CORSMiddleware,
    allow_origins=["*"],  #: TODO: restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(login_router)
app.include_router(register_router)
app.include_router(agent_router)
app.include_router(runner_router)
app.include_router(db_router)
app.include_router(kb_router)
app.include_router(data_query_router)
app.include_router(tool_config_router)

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
def root():
    logger.info(f"Root route accessed")
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/health")
def health():
    logger.info(f"Health check route accessed")
    return {"status": "ok"}


