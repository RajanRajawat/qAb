import datetime

from bson import ObjectId
from database.db import data_query_collection, kb_collection
from utils.general import ensure_object_id


def serialize_agent(agent: dict) -> dict:
    agent["_id"] = str(agent["_id"])
    agent["owner_id"] = str(agent["owner_id"])
    if agent.get("knowledge_base_id"):
        agent["knowledge_base_id"] = str(agent["knowledge_base_id"])
    if agent.get("data_query_id"):
        agent["data_query_id"] = str(agent["data_query_id"])
    agent["created_at"] = str(agent["created_at"])
    if agent.get("updated_at"):
        agent["updated_at"] = str(agent["updated_at"])
    return agent


async def validate_knowledge_base(knowledge_base: bool, knowledge_base_id: str | None, owner_id: str) -> str | None:
    if not knowledge_base:
        return None

    if not knowledge_base_id:
        return "Please select a knowledge base."

    try:
        kb_object_id = ensure_object_id(knowledge_base_id)
    except Exception:
        return "Invalid knowledge base ID format."

    kb_entry = await kb_collection.find_one({
        "_id": kb_object_id,
        "owner_id": ObjectId(owner_id),
    })
    if not kb_entry:
        return "Knowledge base not found."

    return None


async def validate_data_query(data_query: bool, data_query_id: str | None, owner_id: str) -> str | None:
    if not data_query:
        return None

    if not data_query_id:
        return "Please select a Data Query."

    try:
        data_query_object_id = ensure_object_id(data_query_id)
    except Exception:
        return "Invalid Data Query ID format."

    data_query_entry = await data_query_collection.find_one({
        "_id": data_query_object_id,
        "owner_id": ObjectId(owner_id),
    })
    if not data_query_entry:
        return "Data Query not found."

    return None


def normalize_agent_reference_updates(update_data: dict) -> dict:
    if update_data.get("knowledge_base_id"):
        update_data["knowledge_base_id"] = ensure_object_id(update_data["knowledge_base_id"])
    if update_data.get("data_query_id"):
        update_data["data_query_id"] = ensure_object_id(update_data["data_query_id"])
    update_data["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
    return update_data
