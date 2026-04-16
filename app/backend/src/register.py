

#~ Register                                             
#: Todo:                                                
#! Bugs:                                                
#- Notes:                                               


#- Imports
from fastapi import APIRouter, BackgroundTasks
from database.db import users_collection
from database.models import UserRegister
from utils.security import hash_password
from utils.users import get_user_by_email
from utils.emails import send_email
from utils.loggers import logger
from utils.response import success_response, error_response
import datetime

#- Router
register_router = APIRouter(prefix="/auth", tags=["Auth"])

#- Register Endpoint
@register_router.post('/register')
async def register_user(user:UserRegister, bt:BackgroundTasks):

    logger.info(f"New user registration request received from {user.email}")

    if await get_user_by_email(user.email):
        logger.warning(f"Duplicate registration attempt from {user.email}")
        return error_response(status_code=409, message=f'{user.email} is already registered, please login to continue.')
    
    user_data = user.model_dump(exclude={"password"})
    user_data.update({
        'password' : hash_password(user.password),
        'created_at' : datetime.datetime.now(datetime.timezone.utc),
        'custom_db' : {
            'linked' : False
        }
    })

    created_user = await users_collection.insert_one(user_data)

    #: beautify emails.
    bt.add_task(send_email, "QAB - Registration Successful", user.email, "You have successfully registered!")
    logger.info(f"Registration successful for {user.email} with id: {str(created_user.inserted_id)}")
    return success_response(status_code=201, message=f'{user.name} is now registered.')


