from dotenv import load_dotenv
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call
from langchain.messages import ToolMessage
from langgraph.checkpoint.memory import MemorySaver
import itertools
from utils.helpers import logger
from langchain_huggingface import HuggingFaceEndpoint
from fastapi import APIRouter, Query
from langchain_core.output_parsers import StrOutputParser

runner_router = APIRouter(prefix="/chat" , tags=["Agent Runner"])


#- .env LOADERS 
load_dotenv()

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
        return ChatGroq(
            model=model,  # dynamic
            temperature=temp,
            api_key=load_groq_api()
        )

    elif provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temp,
            google_api_key=load_gemini_api()
        )
    
    #: Check and fix this
    # elif provider == "huggingface":
    #     return HuggingFaceEndpoint(
    #         repo_id=model,
    #         temperature=temp,
    #         huggingfacehub_api_token=load_hf_api()
    #     )

    else:
        logger.error(f"Unsupported LLM provider: {provider}")
        raise ValueError(f"Unsupported provider: {provider}")



def agent_builder(agent_config: dict):

    llm = get_llm(agent_config['llm_provider'], agent_config['llm_model'], agent_config['temprature'])
    tools = agent_config['tools']



    #- Tool Error Handler
    @wrap_tool_call
    def handle_tool_errors(request, handler):
        """Handle tool execution errors with custom messages."""
        try:
            return handler(request)
        except Exception as e:
            return ToolMessage(
                content=f"Tool error: Please check your input and try again. ({str(e)})",
                tool_call_id=request.tool_call["id"]
            )

    system_promt_instructions = f"""
                Your name is "{agent_config['name']}", and this is what your description is given to the user "{agent_config['description']}".
                Your Role is {agent_config['role']}

                Your instructions:
                - Be Polite, Helpful, and assist user with queries.
                - {agent_config['instructions']}
"""

    memory = MemorySaver()

    agent = create_agent(llm, 
                        tools=tools,
                        system_prompt=system_promt_instructions,
                        checkpointer=memory,
                        middleware=[handle_tool_errors])

    return agent





