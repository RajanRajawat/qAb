
from fastapi import APIRouter, Depends
from database.db import users_collection, db_collection, data_query_collection
from database.models import AddDB, UpdateDB
from utils.users import get_current_user
from utils.response import success_response, error_response
from utils.loggers import logger
import datetime
from utils.connection import validate_mongo, validate_postgres
from bson import ObjectId
from database.models import ListDB
from pymongo import ReturnDocument
from pymongo.uri_parser import parse_uri
from utils.general import object_id_match
from utils.data_query_helpers import cleanup_data_queries_for_custom_db
from utils.knowledge_base_helpers import cleanup_kbs_for_custom_db, delete_all_embeddings_for_custom_db
import re


db_router = APIRouter(prefix="/custom-db", tags=["DB"])


def build_db_name_match_query(owner_id: str, name: str):
    return {
        "owner_id": ObjectId(owner_id),
        "name": {
            "$regex": f"^{re.escape(name)}$",
            "$options": "i",
        },
    }


#new code:
@db_router.post('/add')
async def link_db(db: AddDB, current_user: dict = Depends(get_current_user)):
    logger.info(f"DB link request received from {current_user['email']} for {db.db}")
    
    user_data = await users_collection.find_one({'_id': ObjectId(current_user['_id'])})

    if not user_data:
        return error_response(400, message="User not found") 

    existing_db = await db_collection.find_one(build_db_name_match_query(current_user["_id"], db.name))
    if existing_db:
        return error_response(409, message="A database with this name already exists.")
    
    # if user_data['custom_db']['linked']:
    #     return error_response(405, message="A DB is already linked. Please remove the current DB before adding a new one.")



    #- Verifing Connection

    if db.db == "mongo":
        if not validate_mongo(db.connection_uri):
            return error_response(400, message="Invalid MongoDB connection string.")
    elif db.db == 'postgres':
        if not validate_postgres(db.connection_uri):
            return error_response(400, message="Invalid PostgreSQL connection string.")


    database_fields = {
        'name' : db.name,
        'provider' : db.db,
        'config' : {    
                "connection_string" : db.connection_uri, #can be encrypted
            },
        'owner_id' : ObjectId(current_user['_id'])
        }

    if db.db == ListDB.MongoDB:
        query_db_name = None
        try:
            query_db_name = parse_uri(db.connection_uri).get("database")
        except Exception:
            query_db_name = None

        database_fields['config'].update({  
                'db_name' : 'qab_test',
                'collection_name' : 'embeddings',
                'query_db_name': query_db_name,
        })

    added_db = await db_collection.insert_one(database_fields)

    await users_collection.update_one(
        {'_id': ObjectId(current_user['_id'])},
        {'$push': {
            'custom_db' : added_db.inserted_id
        }}
    )

    logger.info(f"{db.db} linked successfully for {current_user['email']}")

    return success_response(status_code=201, message=f"{db.db.capitalize()} has been linked successfully.")



@db_router.delete('/delete/{db_id}')
async def unlink_db(db_id: str, current_user: dict = Depends(get_current_user)):
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

    deleted_embeddings = delete_all_embeddings_for_custom_db(str(current_user["_id"]), db_entry)
    if deleted_embeddings is None:
        return error_response(500, message="Could not remove files stored in this DB.")

    cleanup_data = await cleanup_kbs_for_custom_db(str(current_user["_id"]), db_id)
    data_query_cleanup = await cleanup_data_queries_for_custom_db(str(current_user["_id"]), db_id)

    await db_collection.delete_one({'_id': db_object_id})

    await users_collection.update_one(
        {'_id': ObjectId(current_user['_id'])},
        {'$pull': {'custom_db': db_object_id}}
    )

    logger.info(f"DB {db_id} unlinked successfully for {current_user['email']}")

    return success_response(
        status_code=200,
        message="Database has been unlinked successfully.",
        data={
            "deleted_embeddings": deleted_embeddings,
            "deleted_kbs": cleanup_data["deleted_kbs"],
            "deleted_files": cleanup_data["deleted_files"],
            "deleted_data_queries": data_query_cleanup["deleted_data_queries"],
        }
    )




@db_router.patch('/update/{db_id}')
async def update_db(db_id: str, payload: UpdateDB, current_user: dict = Depends(get_current_user)):
    logger.info(f"DB update request received from {current_user['email']} for db_id: {db_id}")

    try:
        db_object_id = ObjectId(db_id)
    except Exception:
        return error_response(400, message="Invalid DB ID format.")

    duplicate_db = await db_collection.find_one({
        **build_db_name_match_query(current_user["_id"], payload.name),
        "_id": {"$ne": db_object_id},
    })
    if duplicate_db:
        return error_response(409, message="A database with this name already exists.")

    updated_db = await db_collection.find_one_and_update(
        {
            "_id": db_object_id,
            "owner_id": ObjectId(current_user["_id"])
        },
        {
            "$set": {
                "name": payload.name,
                "updated_at": datetime.datetime.now(datetime.timezone.utc)
            }
        },
        return_document=ReturnDocument.AFTER
    )

    if not updated_db:
        return error_response(404, message="DB not found or you do not have permission to update it.")

    await data_query_collection.update_many(
        {
            "db_id": object_id_match(db_id),
            "owner_id": ObjectId(current_user["_id"])
        },
        {
            "$set": {
                "db_name": payload.name,
                "updated_at": datetime.datetime.now(datetime.timezone.utc)
            }
        }
    )

    return success_response(
        status_code=200,
        message="Database updated successfully.",
        data={
            "db_id": str(updated_db["_id"]),
            "name": updated_db.get("name"),
            "provider": updated_db.get("provider"),
        }
    )


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

















