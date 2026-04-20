#~ Agent
#: Todo:
#! Bugs:
#- Notes:

from fastapi import APIRouter, HTTPException, Depends
from database.models import AgentCreation, AgentUpdate
from utils.response import success_response, error_response
from utils.users import get_current_user
from utils.loggers import logger
from database.db import users_collection, agents_collection, db_collection
from bson import ObjectId
from bson.errors import InvalidId
import datetime


agent_router = APIRouter(prefix="/agent", tags=["Agent"])


# ── Helper: serialize agent doc for response ───────────────────────────────────
def _serialize_agent(agent: dict) -> dict:
    agent["_id"]        = str(agent["_id"])
    agent["owner_id"]   = str(agent["owner_id"])
    agent["created_at"] = str(agent["created_at"])
    if agent.get("updated_at"):
        agent["updated_at"] = str(agent["updated_at"])
    return agent


# ── Helper: validate kb_files against user's actual DBs ───────────────────────
async def _validate_kb_files(kb_files: list, user_data: dict, owner_id: str) -> str | None:
    """Returns an error message string if invalid, else None."""
    if not kb_files:
        return None

    user_db_ids = [str(d) for d in user_data.get('custom_db', [])]

    for kb in kb_files:
        if kb.db_id == 'default':
            continue
        if kb.db_id not in user_db_ids:
            return f"DB '{kb.db_id}' does not belong to you."

        # Verify the DB doc actually exists and belongs to user
        db_entry = await db_collection.find_one({
            '_id': ObjectId(kb.db_id),
            'owner_id': ObjectId(owner_id)
        })
        if not db_entry:
            return f"DB '{kb.db_id}' not found."

    return None


# ── POST /create ───────────────────────────────────────────────────────────────
@agent_router.post("/create")
async def create_agent(agent: AgentCreation, current_user: dict = Depends(get_current_user)):
    logger.info(f"Agent creation request from {current_user['email']}")

    user_data = await users_collection.find_one({'_id': ObjectId(current_user['_id'])})
    if not user_data:
        return error_response(404, message="User not found.")

    # Validate kb_files if knowledge_base is enabled
    if agent.knowledge_base and agent.kb_files:
        err = await _validate_kb_files(agent.kb_files, user_data, current_user['_id'])
        if err:
            return error_response(400, message=err)

    agent_data = agent.model_dump()
    agent_data.update({
        'owner_id':   ObjectId(current_user['_id']),
        'created_at': datetime.datetime.now(datetime.timezone.utc),
    })

    new_agent = await agents_collection.insert_one(agent_data)

    await users_collection.find_one_and_update(
        {"_id": ObjectId(current_user["_id"])},
        {"$push": {"agents": new_agent.inserted_id}}
    )

    logger.info(f"Agent created | id: {new_agent.inserted_id} | owner: {current_user['email']}")
    return success_response(201, message="Agent created successfully!")


# ── GET /all ───────────────────────────────────────────────────────────────────
@agent_router.get("/all")
async def get_agents(current_user: dict = Depends(get_current_user)):
    logger.info(f"Fetch all agents request from {current_user['email']}")

    agents_cursor = agents_collection.find({"owner_id": ObjectId(current_user["_id"])})
    agents = await agents_cursor.to_list(length=None)

    for agent in agents:
        _serialize_agent(agent)

    logger.info(f"Fetched {len(agents)} agents for {current_user['email']}")
    return success_response(200, data=agents, message="Agents fetched successfully!")


# ── GET /{agent_id} ────────────────────────────────────────────────────────────
@agent_router.get("/{agent_id}")
async def get_agent(agent_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"Fetch agent {agent_id} request from {current_user['email']}")

    try:
        obj_id = ObjectId(agent_id)
    except InvalidId:
        return error_response(400, message="Invalid agent ID format.")

    agent = await agents_collection.find_one({
        "_id": obj_id,
        "owner_id": ObjectId(current_user["_id"])
    })

    if not agent:
        return error_response(404, message="Agent not found.")

    return success_response(200, data=_serialize_agent(agent), message="Agent fetched successfully!")


# ── PATCH /update/{agent_id} ──────────────────────────────────────────────────
@agent_router.patch("/update/{agent_id}")
async def update_agent(agent_id: str, agent: AgentUpdate, current_user: dict = Depends(get_current_user)):
    logger.info(f"Agent update request | id: {agent_id} | owner: {current_user['email']}")

    try:
        obj_id = ObjectId(agent_id)
    except InvalidId:
        return error_response(400, message="Invalid agent ID format.")

    update_data = agent.model_dump(exclude_none=True)
    if not update_data:
        return error_response(400, message="No fields provided to update.")

    # Validate kb_files if being updated
    if 'kb_files' in update_data:
        user_data = await users_collection.find_one({'_id': ObjectId(current_user['_id'])})
        if not user_data:
            return error_response(404, message="User not found.")
        err = await _validate_kb_files(agent.kb_files, user_data, current_user['_id'])
        if err:
            return error_response(400, message=err)

    update_data["updated_at"] = datetime.datetime.now(datetime.timezone.utc)

    updated = await agents_collection.find_one_and_update(
        {
            "_id": obj_id,
            "owner_id": ObjectId(current_user["_id"])
        },
        {"$set": update_data},
        return_document=True
    )

    if not updated:
        return error_response(404, message="Agent not found.")

    logger.info(f"Agent updated | id: {agent_id} | owner: {current_user['email']}")
    return success_response(200, data=_serialize_agent(updated), message="Agent updated successfully!")


# ── DELETE /delete/{agent_id} ─────────────────────────────────────────────────
@agent_router.delete("/delete/{agent_id}")
async def delete_agent(agent_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"Agent delete request | id: {agent_id} | owner: {current_user['email']}")

    try:
        obj_id = ObjectId(agent_id)
    except InvalidId:
        return error_response(400, message="Invalid agent ID format.")

    deleted = await agents_collection.find_one_and_delete({
        "_id": obj_id,
        "owner_id": ObjectId(current_user["_id"])
    })

    if not deleted:
        return error_response(404, message="Agent not found.")

    await users_collection.find_one_and_update(
        {"_id": ObjectId(current_user["_id"])},
        {"$pull": {"agents": obj_id}}
    )

    logger.info(f"Agent deleted | id: {agent_id} | owner: {current_user['email']}")
    return success_response(200, message="Agent deleted successfully!")