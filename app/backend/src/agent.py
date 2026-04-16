

#~ Agent                                                
#: Todo:                                                
#! Bugs:                                                
#- Notes:                                               




from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from database.models import AgentCreation, AgentTool, LLMModel, LLMProvider, AgentUpdate
from utils.emails import send_email
from utils.response import success_response, error_response
from utils.security import verify_password, generate_token
from utils.users import get_current_user, get_user_by_email
from utils.loggers import logger
from database.db import users_collection, agents_collection
from bson import ObjectId
from bson.errors import InvalidId
import datetime



agent_router = APIRouter(prefix="/agent" , tags=["Auth"])

@agent_router.post("/create")
async def create_agent(agent: AgentCreation, current_user: dict = Depends(get_current_user)):
    logger.info(f"Agent creation request received from {current_user['email']}")
    
    agent_data = agent.model_dump()
    agent_data.update({
        'owner_id' : ObjectId(current_user['_id']),
        'created_at' : datetime.datetime.now(datetime.timezone.utc)
    })

    new_agent = await agents_collection.insert_one(agent_data)

    await users_collection.find_one_and_update(
            {"_id": ObjectId(current_user["_id"])},
            {
                "$push": {
                    "agents": new_agent.inserted_id
                }})
    
    logger.info(f"Agent created successfully for {current_user['email']} with id: {str(new_agent.inserted_id)}")
    
    return success_response(201, message="Agent Created!")
    

@agent_router.get("/all")
async def get_agents(current_user: dict = Depends(get_current_user)): 
    logger.info(f"Fetch all agents request received from {current_user['email']}")
    agents_cursor = agents_collection.find({"owner_id": ObjectId(current_user["_id"])})
    agents = await agents_cursor.to_list(length=None)

    for agent in agents:
        agent["_id"] = str(agent["_id"])
        agent["owner_id"] = str(agent["owner_id"])
        agent["created_at"] = str(agent["created_at"])
        if agent.get("updated_at"):
            agent["updated_at"] = str(agent["updated_at"])

    logger.info(f"Fetched {len(agents)} agents for {current_user['email']}")
    return success_response(200, data=agents, message="Agents fetched successfully!")

@agent_router.patch("/update/{agent_id}")
async def update_agent(agent_id: str, agent: AgentUpdate, current_user: dict = Depends(get_current_user)):
    logger.info(f"Agent update request received for agent id: {agent_id} from {current_user['email']}")

    update_data = agent.model_dump(exclude_none=True) #exclude_none=True < this helps with updating only what is being passed.

    if not update_data:
        logger.warning(f"Agent update rejected because no fields were provided for agent id: {agent_id}")
        raise HTTPException(status_code=400, detail="No fields provided to update")

    update_data["updated_at"] = datetime.datetime.now(datetime.timezone.utc)

    updated = await agents_collection.find_one_and_update(
        {
            "_id": ObjectId(agent_id),
            "owner_id": ObjectId(current_user["_id"])
        },
        {"$set": update_data},
        return_document=True
    )

    if not updated:
        logger.warning(f"Agent update failed because agent was not found for agent id: {agent_id} and user: {current_user['email']}")
        raise HTTPException(status_code=404, detail="Agent not found")

    updated["_id"] = str(updated["_id"])
    updated["owner_id"] = str(updated["owner_id"])
    updated["created_at"] = str(updated["created_at"])
    updated["updated_at"] = str(updated["updated_at"])

    logger.info(f"Agent updated successfully for agent id: {agent_id} by {current_user['email']}")

    return success_response(200, data=updated, message="Agent updated successfully!")

@agent_router.delete("/delete/{agent_id}")
async def delete_agent(agent_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"Agent delete request received for agent id: {agent_id} from {current_user['email']}")

    try:
        obj_id = ObjectId(agent_id)
    except InvalidId:
        logger.warning(f"Agent delete rejected due to invalid agent id format: {agent_id}")
        raise HTTPException(status_code=400, detail="Invalid agent ID format")

    deleted = await agents_collection.find_one_and_delete(
        {
            "_id": obj_id,
            "owner_id": str(current_user["_id"])
        }
    )

    if not deleted:
        logger.warning(f"Agent delete failed because agent was not found for agent id: {agent_id} and user: {current_user['email']}")
        raise HTTPException(status_code=404, detail="Agent not found")

    await users_collection.find_one_and_update(
        {"_id": current_user["_id"]},
        {"$pull": {"agents": obj_id}}
    )

    logger.info(f"Agent deleted successfully for agent id: {agent_id} by {current_user['email']}")
    return success_response(200, message="Agent deleted successfully!")
