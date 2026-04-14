#ask for Connection STR,
#DB NAME
#Collection_name
#> Create Vector Index search


from fastapi import APIRouter, BackgroundTasks, Depends
from database.db import users_collection
from database.models import MongoDBLink
from utils.users import get_current_user
from utils.emails import send_email
from utils.response import success_response, error_response
from utils.loggers import logger
import datetime
from bson import ObjectId


db_router = APIRouter(prefix="/custom-db", tags=["DB"])


@db_router.post('/add/mongo')
async def link_db(db: MongoDBLink, bt: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    logger.info(f"New DB Link registration request received from {current_user['email']}")
    
    user_data = await users_collection.find_one({'_id': ObjectId(current_user['_id'])})
    if not user_data:
        return error_response(400, message="User not found")  

    update_fields = {
        'custom_db' : {
            'linked' : True,
            'mongo_db' : {
                "connection_string" : db.connection_uri,
                "db_name" : db.db_name,
                "collection_name" : db.collection_name,
            }
        }
    }

    await users_collection.update_one(
        {'_id': ObjectId(current_user['_id'])},
        {'$set': update_fields}
    )

    # Send confirmation email
    bt.add_task(send_email, "QAB - DB Link Successful", current_user['email'], "You have successfully linked your MongoDB!")
    logger.info(f"MongoDB linked successfully for {current_user['email']}")

    return success_response(status_code=201, message=f"MongoDB has been linked successfully.")




