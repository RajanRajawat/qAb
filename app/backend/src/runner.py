from dotenv import load_dotenv
import os
from uuid import uuid4
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call
from langchain.messages import ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langchain_huggingface import HuggingFaceEndpoint
from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from bson.errors import InvalidId
from utils.env_loaders import load_groq_api, load_gemini_api
from utils.loggers import logger
from utils.users import get_current_user
from utils.response import success_response, error_response
from database.db import agents_collection
from src.tools import get_tools_for_agent
from database.models import AgentRunRequest


runner_router = APIRouter(prefix="/chat" , tags=["Agent Runner"])


#- Agent Runner Functions
def get_llm(provider: str, model: str, temp):
    provider = provider.lower()

    if provider == "groq":
        logger.info(f"Initializing Groq LLM with model: {model}")
        return ChatGroq(
            model=model,
            temperature=temp,
            api_key=load_groq_api()
        )

    elif provider == "gemini":
        logger.info(f"Initializing Gemini LLM with model: {model}")
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temp,
            google_api_key=load_gemini_api()
        )

    else:
        logger.error(f"Unsupported LLM provider: {provider}")
        raise ValueError(f"Unsupported provider: {provider}")


def extract_agent_response_content(result):
    messages = result.get("messages", [])

    for message in reversed(messages):
        if getattr(message, "type", "") == "ai":
            content = message.content

            if isinstance(content, str):
                return content

            if isinstance(content, list):
                output = []

                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        output.append(item.get("text", ""))

                if output:
                    return "\n".join(output)

                return str(content)

            return str(content)

    return ""


def serialize_agent_messages(result):
    serialized_messages = []
    messages = result.get("messages", [])

    for message in messages:
        serialized_messages.append(
            {
                "type": getattr(message, "type", ""),
                "content": message.content
            }
        )

    return serialized_messages


def agent_builder(agent_config: dict):
    logger.info(f"Agent builder started for agent: {agent_config['name']}")

    llm = get_llm(agent_config['llm_provider'], agent_config['llm_model'], agent_config['temperature'])
    tools = get_tools_for_agent(agent_config.get('tools', []))

    #- Tool Error Handler
    @wrap_tool_call
    def handle_tool_errors(request, handler):
        try:
            return handler(request)
        except Exception as e:
            logger.error(f"Tool execution failed for agent: {agent_config['name']} | Error: {str(e)}")
            return ToolMessage(
                content=f"Tool error: Please check your input and try again. ({str(e)})",
                tool_call_id=request.tool_call["id"]
            )

    system_promt_instructions = f"""
                Your name is "{agent_config['name']}", and this is what your description is given to the user "{agent_config['description']}".
                Your Role is {agent_config['role']}

                Your instructions:
                - Be Polite, Helpful, and assist user with queries.
                - {agent_config['instruction']}
"""

    memory = MemorySaver()

    agent = create_agent(
        llm,
        tools=tools,
        system_prompt=system_promt_instructions,
        checkpointer=memory,
        middleware=[handle_tool_errors]
    )

    logger.info(f"Agent built successfully for agent: {agent_config['name']}")
    return agent


@runner_router.post("/run/{agent_id}")
async def run_agent(agent_id: str, request: AgentRunRequest, current_user: dict = Depends(get_current_user)):
    try:
        logger.info(f"Agent run request received for agent id: {agent_id} from {current_user['email']}")

        try:
            obj_id = ObjectId(agent_id)
        except InvalidId:
            logger.warning(f"Agent run rejected due to invalid agent id format: {agent_id}")
            raise HTTPException(status_code=400, detail="Invalid agent ID format")

        agent_data = await agents_collection.find_one(
            {
                "_id": obj_id,
                "owner_id": ObjectId(current_user["_id"])
            }
        )

        if not agent_data:
            logger.warning(f"Agent run failed because agent was not found for agent id: {agent_id} and user: {current_user['email']}")
            return error_response(status_code=404, message="Agent not found")

        agent = agent_builder(agent_data)
        thread_id = request.thread_id or str(uuid4())

        logger.info(f"Running agent id: {agent_id} with thread id: {thread_id}")
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": request.query}]},
            config={"configurable": {"thread_id": thread_id}}
        )

        response = extract_agent_response_content(result)
        serialized_messages = serialize_agent_messages(result)

        logger.info(f"Agent run completed successfully for agent id: {agent_id}")
        return success_response(
            200,
            data={
                "agent_id": agent_id,
                "thread_id": thread_id,
                "response": response,
                "messages": serialized_messages
            },
            message="Agent response generated successfully!"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Agent run failed for agent id: {agent_id} | Error: {str(e)}")
        return error_response(status_code=500, message="Internal server error")





