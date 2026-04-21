from fastapi import APIRouter, Depends
from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument

import datetime

from database.db import agents_collection, chat_history_collection, users_collection
from database.models import AgentCreation, AgentUpdate
from utils.agent_helpers import (
    normalize_agent_reference_updates,
    serialize_agent,
    validate_data_query,
    validate_knowledge_base,
)
from utils.general import ensure_object_id
from utils.loggers import logger
from utils.response import error_response, success_response
from utils.users import get_current_user


agent_router = APIRouter(prefix="/agent", tags=["Agent"])


@agent_router.post("/create")
async def create_agent(agent: AgentCreation, current_user: dict = Depends(get_current_user)):
    logger.info(f"Agent creation request from {current_user['email']}")

    user_data = await users_collection.find_one({"_id": ObjectId(current_user["_id"])})
    if not user_data:
        return error_response(404, message="User not found.")

    err = await validate_knowledge_base(agent.knowledge_base, agent.knowledge_base_id, current_user["_id"])
    if err:
        return error_response(400, message=err)

    data_query_err = await validate_data_query(agent.data_query, agent.data_query_id, current_user["_id"])
    if data_query_err:
        return error_response(400, message=data_query_err)

    agent_data = agent.model_dump()
    if agent_data.get("knowledge_base_id"):
        agent_data["knowledge_base_id"] = ensure_object_id(agent_data["knowledge_base_id"])
    if agent_data.get("data_query_id"):
        agent_data["data_query_id"] = ensure_object_id(agent_data["data_query_id"])
    agent_data.update({
        "owner_id": ObjectId(current_user["_id"]),
        "created_at": datetime.datetime.now(datetime.timezone.utc),
    })

    new_agent = await agents_collection.insert_one(agent_data)

    await users_collection.find_one_and_update(
        {"_id": ObjectId(current_user["_id"])},
        {"$push": {"agents": new_agent.inserted_id}},
    )

    logger.info(f"Agent created | id: {new_agent.inserted_id} | owner: {current_user['email']}")
    return success_response(201, message="Agent created successfully!")


@agent_router.get("/all")
async def get_agents(current_user: dict = Depends(get_current_user)):
    logger.info(f"Fetch all agents request from {current_user['email']}")

    agents_cursor = agents_collection.find({"owner_id": ObjectId(current_user["_id"])})
    agents = await agents_cursor.to_list(length=None)

    for agent in agents:
        serialize_agent(agent)

    logger.info(f"Fetched {len(agents)} agents for {current_user['email']}")
    return success_response(200, data=agents, message="Agents fetched successfully!")


@agent_router.get("/{agent_id}")
async def get_agent(agent_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"Fetch agent {agent_id} request from {current_user['email']}")

    try:
        obj_id = ObjectId(agent_id)
    except InvalidId:
        return error_response(400, message="Invalid agent ID format.")

    agent = await agents_collection.find_one({
        "_id": obj_id,
        "owner_id": ObjectId(current_user["_id"]),
    })

    if not agent:
        return error_response(404, message="Agent not found.")

    return success_response(200, data=serialize_agent(agent), message="Agent fetched successfully!")


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

    if "knowledge_base" in update_data or "knowledge_base_id" in update_data:
        existing_agent = await agents_collection.find_one({
            "_id": obj_id,
            "owner_id": ObjectId(current_user["_id"]),
        })
        if not existing_agent:
            return error_response(404, message="Agent not found.")

        next_knowledge_base = update_data.get("knowledge_base", existing_agent.get("knowledge_base", False))
        next_knowledge_base_id = update_data.get("knowledge_base_id", existing_agent.get("knowledge_base_id"))

        if next_knowledge_base is False:
            update_data["knowledge_base_id"] = None

        err = await validate_knowledge_base(
            next_knowledge_base,
            update_data.get("knowledge_base_id", next_knowledge_base_id),
            current_user["_id"],
        )
        if err:
            return error_response(400, message=err)

    if "data_query" in update_data or "data_query_id" in update_data:
        existing_agent = await agents_collection.find_one({
            "_id": obj_id,
            "owner_id": ObjectId(current_user["_id"]),
        })
        if not existing_agent:
            return error_response(404, message="Agent not found.")

        next_data_query = update_data.get("data_query", existing_agent.get("data_query", False))
        next_data_query_id = update_data.get("data_query_id", existing_agent.get("data_query_id"))

        if next_data_query is False:
            update_data["data_query_id"] = None

        data_query_err = await validate_data_query(
            next_data_query,
            update_data.get("data_query_id", next_data_query_id),
            current_user["_id"],
        )
        if data_query_err:
            return error_response(400, message=data_query_err)

    update_data = normalize_agent_reference_updates(update_data)

    updated = await agents_collection.find_one_and_update(
        {
            "_id": obj_id,
            "owner_id": ObjectId(current_user["_id"]),
        },
        {"$set": update_data},
        return_document=ReturnDocument.AFTER,
    )

    if not updated:
        return error_response(404, message="Agent not found.")

    logger.info(f"Agent updated | id: {agent_id} | owner: {current_user['email']}")
    return success_response(200, data=serialize_agent(updated), message="Agent updated successfully!")


@agent_router.delete("/delete/{agent_id}")
async def delete_agent(agent_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"Agent delete request | id: {agent_id} | owner: {current_user['email']}")

    try:
        obj_id = ObjectId(agent_id)
    except InvalidId:
        return error_response(400, message="Invalid agent ID format.")

    deleted = await agents_collection.find_one_and_delete({
        "_id": obj_id,
        "owner_id": ObjectId(current_user["_id"]),
    })

    if not deleted:
        return error_response(404, message="Agent not found.")

    await users_collection.find_one_and_update(
        {"_id": ObjectId(current_user["_id"])},
        {"$pull": {"agents": obj_id}},
    )

    await chat_history_collection.delete_many({
        "agent_id": ensure_object_id(agent_id),
        "owner_id": ObjectId(current_user["_id"]),
    })

    logger.info(f"Agent deleted | id: {agent_id} | owner: {current_user['email']}")
    return success_response(200, message="Agent deleted successfully!")
