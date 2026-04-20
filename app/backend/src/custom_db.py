


from fastapi import APIRouter, BackgroundTasks, Depends
from database.db import users_collection, db_collection
from database.models import AddDB
from utils.users import get_current_user
from utils.emails import send_email
from utils.response import success_response, error_response
from utils.loggers import logger
import datetime
from utils.connection import validate_mongo, validate_postgres
from bson import ObjectId
from database.models import ListDB


db_router = APIRouter(prefix="/custom-db", tags=["DB"])


#new code:
@db_router.post('/add')
async def link_db(db: AddDB, bt: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    logger.info(f"DB link request received from {current_user['email']} for {db.db}")
    
    user_data = await users_collection.find_one({'_id': ObjectId(current_user['_id'])})

    if not user_data:
        return error_response(400, message="User not found") 
    
    # if user_data['custom_db']['linked']:
    #     return error_response(405, message="A DB is already linked. Please remove the current DB before adding a new one.")

    # if not validate_mongo(uri.connection_uri):
    #     return error_response(400, message="Invalid MongoDB connection string.")
    #: Check and verify db here only, before adding it to the db!!! (later)

    database_fields = {
        'name' : db.name,
        'provider' : db.db,
        'config' : {    
                "connection_string" : db.connection_uri, #can be encrypted
            },
        'owner_id' : ObjectId(current_user['_id'])
        }

    if db.db == ListDB.MongoDB:
        database_fields['config'].update({  
                'db_name' : 'qab_test',
                'collection_name' : 'embeddings',       
        })

    added_db = await db_collection.insert_one(database_fields)

    await users_collection.update_one(
        {'_id': ObjectId(current_user['_id'])},
        {'$push': {
            'custom_db' : added_db.inserted_id
        }}
    )

    bt.add_task(send_email, "QAB - DB Link Successful", current_user['email'], f"You have successfully linked your {db.db}!")
    logger.info(f"{db.db} linked successfully for {current_user['email']}")

    return success_response(status_code=201, message=f"MongoDB has been linked successfully.")



@db_router.delete('/delete/{db_id}')
async def unlink_db(db_id: str, bt: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    logger.info(f"DB unlink request received from {current_user['email']} for db_id: {db_id}")

    user_data = await users_collection.find_one({'_id': ObjectId(current_user['_id'])})
    if not user_data:
        return error_response(400, message="User not found")

    try:
        db_object_id = ObjectId(db_id)
    except Exception:
        return error_response(400, message="Invalid DB ID format.")

    db_entry = await db_collection.find_one({
        '_id': db_object_id,
        'owner_id': ObjectId(current_user['_id'])
    })
    if not db_entry:
        return error_response(404, message="DB not found or you do not have permission to remove it.")

    await db_collection.delete_one({'_id': db_object_id})

    await users_collection.update_one(
        {'_id': ObjectId(current_user['_id'])},
        {'$pull': {'custom_db': db_object_id}}
    )

    bt.add_task(send_email, "QAB - DB Unlink Successful", current_user['email'], f"You have successfully unlinked your {db_entry['provider']}!")
    logger.info(f"DB {db_id} unlinked successfully for {current_user['email']}")

    return success_response(status_code=200, message="Database has been unlinked successfully.")




@db_router.get('/mydb')
async def get_my_dbs(current_user: dict = Depends(get_current_user)):
    logger.info(f"Fetching linked DBs for {current_user['email']}")

    user_data = await users_collection.find_one({'_id': ObjectId(current_user['_id'])})
    if not user_data:
        return error_response(404, message="User not found.")

    db_ids = user_data.get('custom_db', [])

    if not db_ids:
        return success_response(200, message="No custom DBs linked.", data=[])

    dbs = []
    async for db_entry in db_collection.find({'_id': {'$in': db_ids}}):
        dbs.append({
            'db_id': str(db_entry['_id']),
            'name': db_entry.get('name'),
            'provider': db_entry.get('provider'),
        })

    return success_response(200, message="Linked DBs fetched successfully.", data=dbs)

























