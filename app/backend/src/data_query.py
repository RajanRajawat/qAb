import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends
from pymongo import ReturnDocument

from database.db import data_query_collection, users_collection
from database.models import CreateDataQuery, UpdateDataQuery
from utils.data_query_helpers import (
    get_owned_data_query,
    get_owned_db_entry,
    inspect_database_sources,
    remove_data_query_reference_from_agents,
    serialize_data_query,
    validate_selected_sources,
)
from utils.loggers import logger
from utils.response import error_response, success_response
from utils.users import get_current_user


data_query_router = APIRouter(prefix="/data-query", tags=["Data Query"])


@data_query_router.post("/inspect/{db_id}")
async def inspect_sources(db_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"Data Query inspect request for db {db_id} from {current_user['email']}")

    db_entry = await get_owned_db_entry(current_user["_id"], db_id)
    if not db_entry:
        return error_response(404, message="Database not found.")

    try:
        inspection = inspect_database_sources(db_entry)
    except Exception as exc:
        logger.error(f"Data Query inspection failed for db {db_id}: {str(exc)}")
        return error_response(400, message=str(exc))

    return success_response(
        200,
        data={
            "db_id": db_id,
            "db_name": inspection["db_name"],
            "provider": db_entry.get("provider"),
            "sources": inspection["sources"],
        },
        message="Database sources fetched successfully.",
    )


@data_query_router.post("/create")
async def create_data_query(payload: CreateDataQuery, current_user: dict = Depends(get_current_user)):
    logger.info(f"Data Query creation request from {current_user['email']}")

    user_data = await users_collection.find_one({"_id": ObjectId(current_user["_id"])})
    if not user_data:
        return error_response(404, message="User not found.")

    db_entry = await get_owned_db_entry(current_user["_id"], payload.db_id)
    if not db_entry:
        return error_response(404, message="Database not found.")

    payload_data = payload.model_dump()

    try:
        validate_selected_sources(db_entry, payload_data["sources"])
    except Exception as exc:
        return error_response(400, message=str(exc))

    data = payload_data
    data.update({
        "db_name": db_entry.get("name"),
        "provider": db_entry.get("provider"),
        "db_id": db_entry["_id"],
        "owner_id": ObjectId(current_user["_id"]),
        "created_at": datetime.datetime.now(datetime.timezone.utc),
    })

    inserted = await data_query_collection.insert_one(data)
    await users_collection.update_one(
        {"_id": ObjectId(current_user["_id"])},
        {"$push": {"data_queries": inserted.inserted_id}},
    )

    return success_response(201, message="Data Query created successfully.")


@data_query_router.get("/all")
async def get_all_data_queries(current_user: dict = Depends(get_current_user)):
    logger.info(f"Fetch Data Queries request from {current_user['email']}")
    items = await data_query_collection.find({
        "owner_id": ObjectId(current_user["_id"]),
    }).to_list(length=None)

    return success_response(
        200,
        data=[serialize_data_query(item) for item in items],
        message="Data Queries fetched successfully.",
    )


@data_query_router.get("/{data_query_id}")
async def get_data_query(data_query_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"Fetch Data Query {data_query_id} request from {current_user['email']}")

    data_query = await get_owned_data_query(current_user["_id"], data_query_id)
    if not data_query:
        return error_response(404, message="Data Query not found.")

    return success_response(200, data=serialize_data_query(data_query), message="Data Query fetched successfully.")


@data_query_router.patch("/update/{data_query_id}")
async def update_data_query(data_query_id: str, payload: UpdateDataQuery, current_user: dict = Depends(get_current_user)):
    logger.info(f"Update Data Query {data_query_id} request from {current_user['email']}")

    try:
        data_query_object_id = ObjectId(data_query_id)
    except Exception:
        return error_response(400, message="Invalid Data Query ID format.")

    existing = await data_query_collection.find_one({
        "_id": data_query_object_id,
        "owner_id": ObjectId(current_user["_id"]),
    })
    if not existing:
        return error_response(404, message="Data Query not found.")

    db_entry = await get_owned_db_entry(current_user["_id"], existing["db_id"])
    if not db_entry:
        return error_response(404, message="Database linked to this Data Query was not found.")

    payload_data = payload.model_dump()

    try:
        validate_selected_sources(db_entry, payload_data["sources"])
    except Exception as exc:
        return error_response(400, message=str(exc))

    updated = await data_query_collection.find_one_and_update(
        {
            "_id": data_query_object_id,
            "owner_id": ObjectId(current_user["_id"]),
        },
        {
            "$set": {
                "name": payload_data["name"],
                "sources": payload_data["sources"],
                "updated_at": datetime.datetime.now(datetime.timezone.utc),
            }
        },
        return_document=ReturnDocument.AFTER,
    )

    if not updated:
        return error_response(404, message="Data Query not found.")

    return success_response(200, data=serialize_data_query(updated), message="Data Query updated successfully.")


@data_query_router.delete("/delete/{data_query_id}")
async def delete_data_query(data_query_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"Delete Data Query {data_query_id} request from {current_user['email']}")

    try:
        data_query_object_id = ObjectId(data_query_id)
    except Exception:
        return error_response(400, message="Invalid Data Query ID format.")

    deleted = await data_query_collection.find_one_and_delete({
        "_id": data_query_object_id,
        "owner_id": ObjectId(current_user["_id"]),
    })
    if not deleted:
        return error_response(404, message="Data Query not found.")

    await users_collection.update_one(
        {"_id": ObjectId(current_user["_id"])},
        {"$pull": {"data_queries": deleted["_id"]}},
    )
    await remove_data_query_reference_from_agents(deleted["_id"], current_user["_id"])

    return success_response(200, message="Data Query deleted successfully.")








