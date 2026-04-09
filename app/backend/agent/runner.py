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



def get_llm(provider: str, model: str):
    provider = provider.lower()

    if provider == "groq":
        return ChatGroq(
            model=model,  # dynamic
            temperature=0,
            api_key=load_groq_api()
        )

    elif provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=0,
            google_api_key=load_gemini_api()
        )
    
    #: Check and fix this
    # elif provider == "huggingface":
    #     return HuggingFaceEndpoint(
    #         repo_id=model,
    #         temperature=0,
    #         huggingfacehub_api_token=load_hf_api()
    #     )

    else:
        logger.error(f"Unsupported LLM provider: {provider}")
        raise ValueError(f"Unsupported provider: {provider}")

# #- .env
# load_dotenv()

# #Calling APIS
# def load_llm_api():
#     secret_key = os.getenv('SECRET_VALUE')
#     if not secret_key:
#         logger.error(f"JWT secret key not found in .env file")
#         return None
#     logger.info(f"JWT secret key loaded successfully")
#     return secret_key


# def load_groq_api():
#     api = os.getenv('GROQ_API_KEY')
#     if not api:
#         logger.error(f"GROQ API key not found in .env file")
#         return None
#     logger.info(f"GROQ API key loaded successfully")
#     return api




# #- Get LLM Functions

# def get_llm(provider: str, model: str):
    
#     if provider == 'groq':
#         groq_api = load_groq_api()

#         if groq_api:
#             llm = ChatGroq(
#             model="llama-3.1-8b-instant",  # or 70b
#             temperature=0,
#             api_key=groq_api
#         )



#     elif provider == 'gemini':
#         pass


#     elif provider == 'huggingface':
#         pass

    
#     else:
#         #incorrect llm
#         pass


#     return llm





# llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
# llm = ChatGroq(
#     model="llama-3.1-8b-instant",
#     temperature=0,
#     api_key=os.getenv("GROQ_API_KEY")
# )

# tools = [register_user, verify_user, schedule_appointment, reschedule_appointment, cancel_appointment, view_appointments]


# #- Tool Error Handler
# @wrap_tool_call
# def handle_tool_errors(request, handler):
#     """Handle tool execution errors with custom messages."""
#     try:
#         return handler(request)
#     except Exception as e:
#         return ToolMessage(
#             content=f"Tool error: Please check your input and try again. ({str(e)})",
#             tool_call_id=request.tool_call["id"]
#         )

# system_promt_instructions = """
# You are a friendly and helpful help desk assistant for WerqLabs Hospital.

# Your responsibilities:
# - Help users register and create an account
# - Authenticate users using their mobile number and date of birth only once, if the user just created the account no need to verify again
# - Assist users in booking doctor appointments
# - Help reschedule or cancel existing appointments
# - Help user get all his booked appointments
# - Share only validated user's data.
# - Answer simple, general health-related questions (basic guidance only, not medical diagnosis)

# Guidelines:
# - Always be polite, friendly, and conversational
# - Ask for missing information step-by-step instead of assuming
# - Before booking, rescheduling, or cancelling an appointment, ensure the user is verified
# - If the user is not registered, guide them to register first
# - If the user is not verified, ask them to verify their identity

# Health-related behavior:
# - Only answer general health questions (e.g., common cold, headache, basic precautions)
# - Do NOT provide medical diagnosis or advanced medical advice
# - If the user seems unwell, gently suggest booking an appointment with a doctor

# Conversation strategy:
# - Keep responses simple and clear
# - Guide the user toward scheduling an appointment when appropriate
# - Be proactive in helping but do not force actions
# - Use available tools whenever required to complete tasks

# You are not a doctor, but a smart assistant helping users connect with doctors.
# """


# memory = MemorySaver()

# agent = create_agent(llm, 
#                      tools=tools,
#                      system_prompt=system_promt_instructions,
#                      checkpointer=memory,
#                      middleware=[handle_tool_errors])




