import datetime
from fastapi import APIRouter, Depends
from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument
from database.db import agents_collection, users_collection
from database.models import AgentCreation, AgentUpdate, LLMModel, LLMProvider, compatibility_map
from utils.general import ensure_object_id
from utils.loggers import logger
from utils.response import error_response, success_response
from utils.tool_helpers import validate_agent_tools
from utils.users import get_current_user
from utils.agent_helpers import (
    normalize_agent_reference_updates,
    serialize_agent,
    validate_data_query,
    validate_knowledge_base,
)

agent_router = APIRouter(prefix="/agent", tags=["Agent"])

def enum_value(value):
    return value.value if hasattr(value, "value") else value


def validate_llm_pair(provider, model):
    try:
        provider_enum = LLMProvider(enum_value(provider))
        model_enum = LLMModel(enum_value(model))
    except ValueError:
        return "Unsupported provider or model selected."

    allowed_models = compatibility_map.get(provider_enum, set())
    if model_enum not in allowed_models:
        return (
            f"Model '{model_enum.value}' is not supported by provider '{provider_enum.value}'. "
            f"Allowed models: {sorted(model.value for model in allowed_models)}"
        )

    return None


#- Creating agnet
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

    tool_err = await validate_agent_tools([tool.value for tool in agent.tools], current_user["_id"])
    if tool_err:
        return error_response(400, message=tool_err)

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


#- get all agents

@agent_router.get("/all")
async def get_agents(current_user: dict = Depends(get_current_user)):
    logger.info(f"Fetch all agents request from {current_user['email']}")

    agents_cursor = agents_collection.find({"owner_id": ObjectId(current_user["_id"])})
    agents = await agents_cursor.to_list(length=None)

    for agent in agents:
        serialize_agent(agent)

    logger.info(f"Fetched {len(agents)} agents for {current_user['email']}")
    return success_response(200, data=agents, message="Agents fetched successfully!")


#- get agent by id
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

#- update agent (by id)
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

    existing_agent = None

    async def get_existing_agent():
        nonlocal existing_agent
        if existing_agent is None:
            existing_agent = await agents_collection.find_one({
                "_id": obj_id,
                "owner_id": ObjectId(current_user["_id"]),
            })
        return existing_agent

    if "llm_provider" in update_data or "llm_model" in update_data:
        existing_agent = await get_existing_agent()
        if not existing_agent:
            return error_response(404, message="Agent not found.")

        next_provider = update_data.get("llm_provider", existing_agent.get("llm_provider"))
        next_model = update_data.get("llm_model", existing_agent.get("llm_model"))
        llm_err = validate_llm_pair(next_provider, next_model)
        if llm_err:
            return error_response(400, message=llm_err)

    if "knowledge_base" in update_data or "knowledge_base_id" in update_data:
        existing_agent = await get_existing_agent()
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
        existing_agent = await get_existing_agent()
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

    if "tools" in update_data:
        tool_err = await validate_agent_tools([tool.value for tool in update_data["tools"]], current_user["_id"])
        if tool_err:
            return error_response(400, message=tool_err)

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

#- delete agent (by id)
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

    logger.info(f"Agent deleted | id: {agent_id} | owner: {current_user['email']}")
    return success_response(200, message="Agent deleted successfully!")
