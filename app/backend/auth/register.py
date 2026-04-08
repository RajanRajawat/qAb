from fastapi import APIRouter, BackgroundTasks
from database.db import users_collection
from models.models import UserRegister
from utils.helpers import hash_password, get_user_by_email, send_email, logger
from utils.responses import success_response, error_response
import datetime


register_router = APIRouter(prefix="/auth", tags=["Auth"])


@register_router.post('/register')
async def register_user(user:UserRegister, bt:BackgroundTasks):

    logger.info(f"New user registration request received from {user.email}")

    if await get_user_by_email(user.email):
        logger.warning(f"Duplicate registration attempt from {user.email}")
        return error_response(status_code=409, message=f'{user.email} is already registered, please login to continue.')
    
    user_data = user.model_dump(exclude={"password"})
    user_data.update({
        'password' : hash_password(user.password),
        # 'agent_credits' : {
        #     'max' : 3,
        #     'used' : 0
        # },
        'created_at' : datetime.datetime.now(datetime.timezone.utc)

    })

    created_user = await users_collection.insert_one(user_data)

    #: beautify emails.
    bt.add_task(send_email, "QAB - Registration Successful", user.email, "You have successfully registered!")

    logger.info(f"Registration successful for {user.email} with id: {str(created_user.inserted_id)}")
    
    return success_response(status_code=201, message=f'{user.name} is now registered.')


