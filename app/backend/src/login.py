

#~ Login                                                
#: Todo:                                                
#! Bugs:                                                
#- Notes:                                               



from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from database.models import UserLogin
from utils.security import  verify_password, generate_token
from utils.loggers import logger
from utils.emails import send_email
from utils.users import get_user_by_email, get_current_user
from utils.response import success_response, error_response

login_router = APIRouter(prefix="/auth" , tags=["Auth"])

@login_router.post("/login")
async def validate_login(user: UserLogin, bt: BackgroundTasks):
    try:
        logger.info(f"Login request received from {user.email}")
        user_data = await get_user_by_email(user.email)
        if user_data:
            if not verify_password(user.password, user_data["password"]):
                logger.warning(f"Incorrect password, login rejected for {user.email}")
                return error_response(status_code=401, message="Please check your password.")
            access_token = generate_token(user_data, "access", 3)
            refresh_token = generate_token(user_data, "refresh", 24)
            logger.info(f"JWT tokens generated")
            #: beautify email later.
            bt.add_task(send_email, "QAB - Login Successful", user.email, "You have successfully logged in!")
            return success_response(
                status_code=200,
                message="You are now logged in.",
                data={
                    "user_info": {
                        "id": str(user_data["_id"]),
                        "name": user_data["name"],
                        "email": user_data["email"],
                    },
                    "jwt_tokens": {
                        "access_token": access_token,
                        "refresh_token": refresh_token
                    }
                }
            )
        else:
            logger.warning(f"Login failed, user not registered: {user.email}")
            return error_response(status_code=404, message="You have not registered yet, please register to continue.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed for {user.email} | Error: {str(e)}")
        return error_response(status_code=500, message="Internal server error")
