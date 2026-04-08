from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from models.models import AgentCreation, AgentTool, LLMModel, LLMProvider, AgentUpdate
from utils.helpers import send_email, verify_password, generate_token, get_user_by_email, logger, get_current_user
from utils.responses import success_response, error_response
from database.db import users_collection, agents_collection
from bson import ObjectId
from bson.errors import InvalidId
import datetime


agent_router = APIRouter(prefix="/agent" , tags=["Auth"])

@agent_router.post("/create")
async def create_agent(agent: AgentCreation, current_user: dict = Depends(get_current_user)):
    
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
    
    return success_response(201, message="Agent Created!")
    

@agent_router.get("/all")
async def get_agents(current_user: dict = Depends(get_current_user)): 
    agents_cursor = agents_collection.find({"owner_id": ObjectId(current_user["_id"])})
    agents = await agents_cursor.to_list(length=None)

    for agent in agents:
        agent["_id"] = str(agent["_id"])
        agent["owner_id"] = str(agent["owner_id"])
        agent["created_at"] = str(agent["created_at"])
        if agent['updated_at']:
            agent["updated_at"] = str(agent["updated_at"])

    return success_response(200, data=agents, message="Agents fetched successfully!")

@agent_router.patch("/update/{agent_id}")
async def update_agent(agent_id: str, agent: AgentUpdate, current_user: dict = Depends(get_current_user)):

    update_data = agent.model_dump(exclude_none=True) #exclude_none=True < this helps with updating only what is being passed.

    if not update_data:
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
        raise HTTPException(status_code=404, detail="Agent not found")

    updated["_id"] = str(updated["_id"])
    updated["owner_id"] = str(updated["owner_id"])
    updated["created_at"] = str(updated["created_at"])
    updated["updated_at"] = str(updated["updated_at"])


    return success_response(200, data=updated, message="Agent updated successfully!")

@agent_router.delete("/delete/{agent_id}")
async def delete_agent(agent_id: str, current_user: dict = Depends(get_current_user)):

    try:
        obj_id = ObjectId(agent_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid agent ID format")

    deleted = await agents_collection.find_one_and_delete(
        {
            "_id": obj_id,
            "owner_id": ObjectId(current_user["_id"])
        }
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="Agent not found")

    await users_collection.find_one_and_update(
        {"_id": current_user["_id"]},
        {"$pull": {"agents": obj_id}}
    )

    return success_response(200, message="Agent deleted successfully!")