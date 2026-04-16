

#~ Custom DB Link                                       
#: Todo:                                                
#! Bugs:                                                
#- Notes:                                               




from fastapi import APIRouter, BackgroundTasks, Depends
from database.db import users_collection
from database.models import URILink
from utils.users import get_current_user
from utils.emails import send_email
from utils.response import success_response, error_response
from utils.loggers import logger
import datetime
from utils.connection import validate_mongo, validate_postgres
from bson import ObjectId


db_router = APIRouter(prefix="/custom-db", tags=["DB"])

#- Add DB
#- Mongo
@db_router.post('/add/mongo')
async def link_mongo_db(uri: URILink, bt: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    logger.info(f"DB link request received from {current_user['email']} for MongoDB")
    
    user_data = await users_collection.find_one({'_id': ObjectId(current_user['_id'])})

    if not user_data:
        return error_response(400, message="User not found") 
    
    if user_data['custom_db']['linked']:
        return error_response(405, message="A DB is already linked. Please remove the current DB before adding a new one.")

    if not validate_mongo(uri.connection_uri):
        return error_response(400, message="Invalid MongoDB connection string.")
    
    update_fields = {
        'custom_db' : {
            'linked' : True,
            'provider' : 'mongo',
            'config' : {
                "connection_string" : uri.connection_uri, #can be encrypted
                "db_name" : "qab_test",
                "collection_name" : "embeddings",
            }
        }
    }

    await users_collection.update_one(
        {'_id': ObjectId(current_user['_id'])},
        {'$set': update_fields}
    )

    bt.add_task(send_email, "QAB - DB Link Successful", current_user['email'], "You have successfully linked your MongoDB!")
    logger.info(f"MongoDB linked successfully for {current_user['email']}")

    return success_response(status_code=201, message=f"MongoDB has been linked successfully.")


#- Postgres 
@db_router.post('/add/postgres')
async def link_postgres_db(uri: URILink, bt: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    logger.info(f"DB link request received from {current_user['email']} for Postgres")
    
    user_data = await users_collection.find_one({'_id': ObjectId(current_user['_id'])})
    
    if not user_data:
        return error_response(400, message="User not found") 
    
    if user_data['custom_db']['linked']:
        return error_response(405, message="A DB is already linked. Please remove the current DB before adding a new one.")
    
    #replace standard string with my kinda string
    # if uri.connection_uri.startswith("postgres://") or uri.connection_uri.startswith("postgresql://"):
    #     connection_uri = uri.connection_uri.replace("://", "+psycopg://", 1)

    # if not validate_postgres(uri.connection_uri):
    #     return error_response(400, message="Invalid Postgres connection string.")

    update_fields = {
        'custom_db' : {
            'linked' : True,
            'provider' : 'postgres',
            'config' : {    
                "connection_string" : uri.connection_uri, #can be encrypted
            }
        }
    }

    await users_collection.update_one(
        {'_id': ObjectId(current_user['_id'])},
        {'$set': update_fields}
    )

    bt.add_task(send_email, "QAB - DB Link Successful", current_user['email'], "You have successfully linked your Postgres SupaBase!")
    logger.info(f"Postgres linked successfully for {current_user['email']}")

    return success_response(status_code=201, message=f"Postgres has been linked successfully.")


#- Delete any db
@db_router.post('/delete')
async def delete_db(bt: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    logger.info(f"DB delete request received from {current_user['email']}")
    
    user_data = await users_collection.find_one({'_id': ObjectId(current_user['_id'])})
    
    if not user_data:
        return error_response(400, message="User not found") 
    
    if not user_data['custom_db']['linked']:
        return error_response(405, message="No DB is currently linked. Nothing to delete.")
    
    update_fields = {
        'custom_db' : {
            'linked' : False,
        }
    }

    await users_collection.update_one(
        {'_id': ObjectId(current_user['_id'])},
        {'$set': update_fields}
    )


    bt.add_task(send_email, "QAB - DB Delete Successful", current_user['email'], "You have successfully deleted your linked DB!")
    logger.info(f"DB deleted successfully for {current_user['email']}")

    return success_response(status_code=201, message=f"DB has been deleted successfully.")