import datetime
import os
import re
import shutil
from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from pymongo import ReturnDocument
from database.db import kb_collection
from database.models import CreateKnowledgeBase, KnowledgeBaseVectorSearchRequest, UpdateKnowledgeBase
from utils.knowledge_base_helpers import (
    EMBEDDING_MODEL_OPTIONS,
    delete_embeddings_for_kb,
    delete_kb_reference_from_agents,
    get_db_name,
    get_kb_entry,
    get_user_data,
    get_user_db_entry,
    process_file_and_embed,
    resolve_embedding_model_name,
    search_kb_chunks,
    serialize_embedding_options,
    serialize_kb,
    serialize_search_results,
)
from utils.loggers import logger
from utils.response import error_response, success_response
from utils.users import get_current_user


#check krna bhai ye lase me
#! when a custom db is deleted, all the data from that db is deleted, it should be deleted of that specific kb name data removal only.
kb_router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base"])


def build_kb_name_match_query(owner_id: str, name: str):
    return {
        "owner_id": ObjectId(owner_id),
        "name": {
            "$regex": f"^{re.escape(name)}$",
            "$options": "i",
        },
    }


#- Routes


#-get embedding options
@kb_router.get("/embedding-options")
async def get_embedding_options(current_user: dict = Depends(get_current_user)):
    logger.info(f"Embedding options requested by {current_user['email']}")

    return success_response(
        200,
        message="Embedding options fetched successfully.",
        data=serialize_embedding_options()
    )

#- create kb
@kb_router.post("/create")
async def create_knowledge_base(payload: CreateKnowledgeBase, current_user: dict = Depends(get_current_user)):
    logger.info(f"Knowledge base create request from {current_user['email']}")

    user_data = await get_user_data(current_user)
    if not user_data:
        return error_response(404, message="User not found.")

    existing_kb = await kb_collection.find_one(build_kb_name_match_query(current_user["_id"], payload.name))
    if existing_kb:
        return error_response(409, message="A knowledge base with this name already exists.")

    if payload.embedding_model not in EMBEDDING_MODEL_OPTIONS:
        return error_response(400, message="Unsupported embedding model selected.")

    db_entry = await get_user_db_entry(current_user["_id"], payload.db_id)
    if db_entry == "invalid":
        return error_response(400, message="Invalid db_id format.")
    if payload.db_id and payload.db_id != "default" and not db_entry:
        return error_response(404, message="DB not found or does not belong to you.")

    kb_data = {
        "name": payload.name,
        "owner_id": ObjectId(current_user["_id"]),
        "files": [],
        "db_id": db_entry["_id"] if db_entry else "default",
        "db_name": get_db_name(db_entry),
        "embedding_model": resolve_embedding_model_name(payload.embedding_model),
        "created_at": datetime.datetime.now(datetime.timezone.utc),
    }

    created_kb = await kb_collection.insert_one(kb_data)
    kb_data["_id"] = created_kb.inserted_id

    return success_response(
        201,
        message="Knowledge base created successfully.",
        data=serialize_kb(kb_data)
    )

#- get all kb
@kb_router.get("/all")
async def get_all_knowledge_bases(current_user: dict = Depends(get_current_user)):
    logger.info(f"Knowledge base list request from {current_user['email']}")

    kbs = []
    async for kb in kb_collection.find({"owner_id": ObjectId(current_user["_id"])}).sort("created_at", -1):
        kbs.append(serialize_kb(kb))

    return success_response(200, message="Knowledge bases fetched successfully.", data=kbs)

#- get kb by id

@kb_router.get("/{kb_id}")
async def get_knowledge_base(kb_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"Knowledge base detail request for kb {kb_id} from {current_user['email']}")

    kb_entry = await get_kb_entry(kb_id, current_user["_id"])
    if not kb_entry:
        return error_response(404, message="Knowledge base not found.")

    return success_response(200, message="Knowledge base fetched successfully.", data=serialize_kb(kb_entry))

#- UPDATE KB by id
@kb_router.patch("/update/{kb_id}")
async def update_knowledge_base(kb_id: str, payload: UpdateKnowledgeBase, current_user: dict = Depends(get_current_user)):
    logger.info(f"Knowledge base update request for kb {kb_id} from {current_user['email']}")

    kb_entry = await get_kb_entry(kb_id, current_user["_id"])
    if not kb_entry:
        return error_response(404, message="Knowledge base not found.")

    duplicate_kb = await kb_collection.find_one({
        **build_kb_name_match_query(current_user["_id"], payload.name),
        "_id": {"$ne": kb_entry["_id"]},
    })
    if duplicate_kb:
        return error_response(409, message="A knowledge base with this name already exists.")

    updated_kb = await kb_collection.find_one_and_update(
        {
            "_id": kb_entry["_id"],
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

    return success_response(200, message="Knowledge base updated successfully.", data=serialize_kb(updated_kb))

#- add file to kb
@kb_router.post("/add-file/{kb_id}")
async def add_file_to_knowledge_base(
    kb_id: str,
    bt: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    logger.info(f"Add file request for kb {kb_id} from {current_user['email']}")

    if not file.filename.endswith((".txt", ".pdf")):
        return error_response(400, message="Only .txt and .pdf files are supported.")

    kb_entry = await get_kb_entry(kb_id, current_user["_id"])
    if not kb_entry:
        return error_response(404, message="Knowledge base not found.")

    if file.filename in kb_entry.get("files", []):
        return error_response(400, message="This file already exists in the knowledge base.")

    db_entry = await get_user_db_entry(current_user["_id"], kb_entry.get("db_id"))
    if kb_entry.get("db_id") != "default" and not db_entry:
        return error_response(404, message="Linked DB not found for this knowledge base.")

    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", f"{current_user['_id']}_{kb_id}_{file.filename}")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    await kb_collection.update_one(
        {"_id": kb_entry["_id"]},
        {
            "$push": {"files": file.filename},
            "$set": {"updated_at": datetime.datetime.now(datetime.timezone.utc)}
        }
    )

    bt.add_task(
        process_file_and_embed,
        file_path,
        file.filename,
        str(current_user["_id"]),
        kb_id,
        resolve_embedding_model_name(kb_entry.get("embedding_model")),
        db_entry,
    )

    return success_response(202, message="File added successfully. Processing started.")

#-delte file from kb
@kb_router.delete("/remove-file/{kb_id}")
async def remove_file_from_knowledge_base(
    kb_id: str,
    file_name: str,
    current_user: dict = Depends(get_current_user)
):
    logger.info(f"Remove file request for kb {kb_id} from {current_user['email']}")

    kb_entry = await get_kb_entry(kb_id, current_user["_id"])
    if not kb_entry:
        return error_response(404, message="Knowledge base not found.")

    if file_name not in kb_entry.get("files", []):
        return error_response(404, message="File not found in this knowledge base.")

    db_entry = await get_user_db_entry(current_user["_id"], kb_entry.get("db_id"))
    if kb_entry.get("db_id") != "default" and not db_entry:
        return error_response(404, message="Linked DB not found for this knowledge base.")

    deleted_count = delete_embeddings_for_kb(str(current_user["_id"]), kb_id, db_entry, file_name)

    if deleted_count is None:
        return error_response(500, message="Could not remove file embeddings.")

    await kb_collection.update_one(
        {"_id": kb_entry["_id"]},
        {
            "$pull": {"files": file_name},
            "$set": {"updated_at": datetime.datetime.now(datetime.timezone.utc)}
        }
    )

    return success_response(
        200,
        message=f"File removed successfully. Deleted {deleted_count} embeddings."
    )

#! bugged mongo test not working    
#~ FIXED
#- test chunks from kb
@kb_router.post("/test-search/{kb_id}")
async def test_knowledge_base_search(
    kb_id: str,
    payload: KnowledgeBaseVectorSearchRequest,
    current_user: dict = Depends(get_current_user)
):
    logger.info(f"Knowledge base vector search test requested for kb {kb_id} from {current_user['email']}")

    kb_entry = await get_kb_entry(kb_id, current_user["_id"])
    if not kb_entry:
        return error_response(404, message="Knowledge base not found.")

    db_entry = await get_user_db_entry(current_user["_id"], kb_entry.get("db_id"))
    if kb_entry.get("db_id") != "default" and not db_entry:
        return error_response(404, message="Linked DB not found for this knowledge base.")

    try:
        results = search_kb_chunks(
            payload.query,
            str(current_user["_id"]),
            kb_entry,
            db_entry,
            payload.limit
        )
        
    except Exception as e:
        logger.error(f"Knowledge base test search failed for kb {kb_id}: {str(e)}")
        return error_response(500, message="Could not search this knowledge base right now.")

    return success_response(
        200,
        message="Knowledge base search completed successfully.",
        data={
            "kb": serialize_kb(kb_entry),
            "query": payload.query,
            "limit": payload.limit,
            "results": serialize_search_results(results)
        }
    )


#- delete kb by id
@kb_router.delete("/delete/{kb_id}")
async def delete_knowledge_base(kb_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"Delete knowledge base request for kb {kb_id} from {current_user['email']}")

    kb_entry = await get_kb_entry(kb_id, current_user["_id"])
    if not kb_entry:
        return error_response(404, message="Knowledge base not found.")

    db_entry = await get_user_db_entry(current_user["_id"], kb_entry.get("db_id"))
    if kb_entry.get("db_id") != "default" and not db_entry:
        return error_response(404, message="Linked DB not found for this knowledge base.")

    deleted_count = delete_embeddings_for_kb(str(current_user["_id"]), kb_id, db_entry)

    if deleted_count is None:
        return error_response(500, message="Could not delete knowledge base embeddings.")

    await delete_kb_reference_from_agents(kb_entry["_id"], current_user["_id"])
    await kb_collection.delete_one({"_id": kb_entry["_id"]})

    return success_response(
        200,
        message=f"Knowledge base deleted successfully. Deleted {deleted_count} embeddings."
    )
