from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
from contextlib import asynccontextmanager
from auth.register import register_router
from auth.login import login_router
from agent.agent import agent_router
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

@app.get("/")
def root():
    return FileResponse("index.html")


@app.get("/health")
def health():
    return {"status": "ok"}