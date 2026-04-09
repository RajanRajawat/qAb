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
from utils.helpers import logger, get_current_user
from utils.responses import success_response, error_response
from database.db import agents_collection
from agent.tools import get_tools_for_agent


runner_router = APIRouter(prefix="/chat" , tags=["Agent Runner"])


#- .env LOADERS
load_dotenv()


class AgentRunRequest(BaseModel):
    query: str
    thread_id: str | None = None


def load_secret_key():
    secret_key = os.getenv("SECRET_VALUE")
    if not secret_key:
        logger.error("JWT secret key not found in .env file")
        raise ValueError("Missing SECRET_VALUE in .env")
    logger.info("JWT secret key loaded successfully")
    return secret_key


def load_groq_api():
    api = os.getenv("GROQ_API_KEY")
    if not api:
        logger.error("GROQ API key not found in .env file")
        raise ValueError("Missing GROQ_API_KEY in .env")
    logger.info("GROQ API key loaded successfully")
    return api


def load_gemini_api():
    api = os.getenv("GOOGLE_API_KEY")
    if not api:
        logger.error("GOOGLE API key not found in .env file")
        raise ValueError("Missing GOOGLE_API_KEY in .env")
    logger.info("GOOGLE API key loaded successfully")
    return api


def load_hf_api():
    api = os.getenv("HUGGINGFACEHUB_API_TOKEN")
    if not api:
        logger.error("HF API key not found in .env file")
        raise ValueError("Missing HUGGINGFACEHUB_API_TOKEN in .env")
    logger.info("HF API key loaded successfully")
    return api


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

    # elif provider == "huggingface":
    #     logger.info(f"Initializing HuggingFace LLM with model: {model}")
    #     return HuggingFaceEndpoint(
    #         repo_id=model,
    #         temperature=temp,
    #         huggingfacehub_api_token=load_hf_api()
    #     )

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





