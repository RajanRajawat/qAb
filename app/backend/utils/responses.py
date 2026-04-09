from fastapi.responses import JSONResponse
from fastapi import HTTPException
from utils.helpers import logger

def success_response(status_code:int, data=None, message="Success"):
    logger.info(f"Success response generated with status code: {status_code} | Message: {message}")
    return JSONResponse(
        status_code=status_code,
            content={
                "success": True,
                "status": status_code,
                "data" : data,
                "message": message,
            }
        )

def error_response(status_code: int, data=None , message="Error"):
    logger.warning(f"Error response generated with status code: {status_code} | Message: {message}")
    raise HTTPException(
        status_code=status_code,
        detail={
            "success": False,
            "status": status_code,
            "data" : data,
            "message": message,
        }
    )
