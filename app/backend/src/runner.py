import asyncio
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from database.db import agents_collection, kb_collection, db_collection, data_query_collection
from database.models import AgentRunRequest
from utils.general import ensure_object_id
from utils.loggers import logger
from utils.response import error_response, raise_error_response, success_response
from utils.runner_helpers import (
    agent_builder,
    build_history_messages,
    extract_agent_response_content,
    serialize_agent_messages,
)
from utils.tool_helpers import get_user_tool_configs, validate_agent_tools
from utils.users import get_current_user


runner_router = APIRouter(prefix="/chat", tags=["Agent Runner"])
AGENT_RUN_TIMEOUT_SECONDS = 120



#runner func
async def _run_agent(agent_id: str, request: AgentRunRequest, current_user: dict):
    logger.info(f"Agent run request received for agent id: {agent_id} from {current_user['email']}")

    try:
        obj_id = ObjectId(agent_id)
    except InvalidId:
        logger.warning(f"Agent run rejected due to invalid agent id format: {agent_id}")
        raise_error_response(status_code=400, message="Invalid agent ID format")

    agent_data = await agents_collection.find_one(
        {
            "_id": obj_id,
            "owner_id": ObjectId(current_user["_id"])
        }
    )

    if not agent_data:
        logger.warning(f"Agent not found for agent id: {agent_id} and user: {current_user['email']}")
        return error_response(status_code=404, message="Agent not found")
    
    tool_err = await validate_agent_tools(agent_data.get("tools", []), current_user["_id"])
    if tool_err:
        return error_response(status_code=400, message=tool_err)

    kb_entry = None
    kb_db_entry = None
    if agent_data.get("knowledge_base") is True:
        kb_id = agent_data.get("knowledge_base_id")
        if not kb_id:
            return error_response(status_code=400, message="Agent does not have a knowledge base selected.")

        kb_entry = await kb_collection.find_one({
            "_id": ensure_object_id(kb_id),
            "owner_id": ObjectId(current_user["_id"])
        })
        if not kb_entry:
            return error_response(status_code=404, message="Knowledge base not found for this agent.")

        if kb_entry.get("db_id") != "default":
            kb_db_entry = await db_collection.find_one({
                "_id": ensure_object_id(kb_entry["db_id"]),
                "owner_id": ObjectId(current_user["_id"])
            })
            if not kb_db_entry:
                return error_response(status_code=404, message="Knowledge base DB not found.")

    data_query_entry = None
    data_query_db_entry = None
    if agent_data.get("data_query") is True:
        data_query_id = agent_data.get("data_query_id")
        if not data_query_id:
            return error_response(status_code=400, message="Agent does not have a Data Query selected.")

        data_query_entry = await data_query_collection.find_one({
            "_id": ensure_object_id(data_query_id),
            "owner_id": ObjectId(current_user["_id"])
        })
        if not data_query_entry:
            return error_response(status_code=404, message="Data Query not found for this agent.")

        data_query_db_entry = await db_collection.find_one({
            "_id": ensure_object_id(data_query_entry["db_id"]),
            "owner_id": ObjectId(current_user["_id"])
        })
        if not data_query_db_entry:
            return error_response(status_code=404, message="Database linked to this Data Query was not found.")

    tool_configs = await get_user_tool_configs(current_user["_id"])
    agent = agent_builder(
        agent_data,
        tool_configs,
        data_query_entry,
        data_query_db_entry,
        owner_id=current_user["_id"],
        kb_entry=kb_entry,
        kb_db_entry=kb_db_entry,
    )

    history_messages = build_history_messages([item.model_dump() for item in request.history][-12:])

    logger.info(f"Running agent id: {agent_id} with session history count: {len(history_messages)}")
    result = await agent.ainvoke(
        {"messages": [*history_messages, {"role": "user", "content": request.query}]}
    )

    response = extract_agent_response_content(result)
    serialized_messages = serialize_agent_messages(result)

    logger.info(f"Agent run completed successfully for agent id: {agent_id}")
    return success_response(
        200,
        data={
            "agent_id": agent_id,
            "response": response,
            "messages": serialized_messages
        },
        message="Agent response generated successfully!"
    )


#- run agent by id
@runner_router.post("/run/{agent_id}")
async def run_agent(agent_id: str, request: AgentRunRequest, current_user: dict = Depends(get_current_user)):
    try:
        return await asyncio.wait_for(
            _run_agent(agent_id, request, current_user),
            timeout=AGENT_RUN_TIMEOUT_SECONDS,
        )

    except asyncio.TimeoutError:
        logger.warning(
            f"Agent run timed out after {AGENT_RUN_TIMEOUT_SECONDS}s for agent id: {agent_id}"
        )
        return error_response(status_code=504, message="Request timed out")

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Agent run failed for agent id: {agent_id} | Error: {str(e)}")
        return error_response(status_code=500, message="Internal server error")
