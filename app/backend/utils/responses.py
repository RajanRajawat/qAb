from fastapi.responses import JSONResponse
from fastapi import HTTPException

def success_response(status_code:int, data=None, message="Success"):
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
    raise HTTPException(
        status_code=status_code,
        detail={
            "success": False,
            "status": status_code,
            "data" : data,
            "message": message,
        }
    )
