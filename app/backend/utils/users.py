

#~ Users                                                
#: Todo:                                                
#! Bugs:                                                
#- Notes:                                               




import jwt
from pydantic import EmailStr
from database.db import users_collection
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import ExpiredSignatureError, InvalidTokenError
from utils.loggers import logger
from utils.env_loaders import load_jwt_secret_key
from utils.response import raise_error_response



security = HTTPBearer()
SECRET_KEY = str(load_jwt_secret_key)



#- User
async def get_user_by_email(email: EmailStr):
    logger.info(f"Fetching user by email: {email}")
    user_data = await users_collection.find_one({'email': email})
    if user_data:
        logger.info(f"User found for email: {email}")
        return user_data
    else:
        logger.warning(f"User not found for email: {email}")
        return False


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        logger.info(f"Current user token validation started")
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        logger.info(f"Current user token validated successfully for {payload['email']}")
        return payload
    except ExpiredSignatureError:
        logger.warning(f"Current user token validation failed because token expired")
        raise_error_response(status_code=401, message="Token has expired, please login again.")
    except InvalidTokenError:
        logger.warning(f"Current user token validation failed because token was invalid")
        raise_error_response(status_code=401, message="Invalid token.")
    
