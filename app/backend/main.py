from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
from contextlib import asynccontextmanager
from auth.register import register_router
from auth.login import login_router
from agent.agent import agent_router
from agent.runner import runner_router
from utils.helpers import logger
load_dotenv()



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(login_router)
app.include_router(register_router)
app.include_router(agent_router)
app.include_router(runner_router)

@app.get("/")
def root():
    logger.info(f"Root route accessed")
    return FileResponse("index.html")


@app.get("/health")
def health():
    logger.info(f"Health check route accessed")
    return {"status": "ok"}
