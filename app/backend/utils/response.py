from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from utils.loggers import logger


def build_response_payload(success, status_code, data=None, message="Success"):
    return {
        "success": success,
        "status": status_code,
        "data": jsonable_encoder(data),
        "message": message,
    }


def success_response(status_code: int, data=None, message="Success"):
    logger.info(f"Success response generated with status code: {status_code} | Message: {message}")
    return JSONResponse(
        status_code=status_code,
        content=build_response_payload(True, status_code, data=data, message=message),
    )


def error_response(status_code: int, data=None, message="Error"):
    logger.warning(f"Error response generated with status code: {status_code} | Message: {message}")
    return JSONResponse(
        status_code=status_code,
        content=build_response_payload(False, status_code, data=data, message=message),
    )


def raise_error_response(status_code: int, data=None, message="Error"):
    logger.warning(f"Error response raised with status code: {status_code} | Message: {message}")
    raise HTTPException(
        status_code=status_code,
        detail=build_response_payload(False, status_code, data=data, message=message),
    )


def is_response_payload(detail):
    if not isinstance(detail, dict):
        return False

    return all(key in detail for key in ["success", "status", "message"])
