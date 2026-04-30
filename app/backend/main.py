import pathlib
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.register import register_router
from src.login import login_router
from src.agent import agent_router
from src.runner import runner_router
from src.custom_db import db_router
from src.knowledge_base import kb_router
from src.data_query import data_query_router
from src.tool_config import tool_config_router
from utils.loggers import logger
from utils.response import error_response, is_response_payload
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


def build_validation_error_data(exc: RequestValidationError):
    errors = []

    for item in exc.errors():
        error_item = {
            "type": item.get("type"),
            "loc": list(item.get("loc", [])),
            "msg": item.get("msg"),
            "input": item.get("input"),
        }

        if "ctx" in item:
            error_item["ctx"] = item["ctx"]

        errors.append(error_item)

    return errors


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error on {request.method} {request.url.path}: {exc.errors()}")
    return error_response(
        422,
        data=build_validation_error_data(exc),
        message="Validation error.",
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    logger.warning(f"HTTP exception on {request.method} {request.url.path}: status={exc.status_code} detail={detail}")

    if is_response_payload(detail):
        return error_response(
            detail.get("status", exc.status_code),
            data=detail.get("data"),
            message=detail.get("message", "Error"),
        )

    if isinstance(detail, list):
        return error_response(exc.status_code, data=detail, message="Request failed.")

    if isinstance(detail, dict):
        return error_response(
            exc.status_code,
            data=detail.get("data"),
            message=detail.get("message", "Request failed."),
        )

    return error_response(exc.status_code, message=str(detail) if detail else "Request failed.")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
    return error_response(500, message="Internal server error")

@app.get("/")
def root():
    logger.info(f"Root route accessed")
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/health")
def health():
    logger.info(f"Health check route accessed")
    return {"status": "ok"}
