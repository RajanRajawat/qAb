# from dotenv import load_dotenv
# import os
# from uuid import uuid4
# from pydantic import BaseModel
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_groq import ChatGroq
# from langchain.agents import create_agent
# # from langchain.agents.middleware import wrap_tool_call
# # from langchain.agents.middleware import wrap_tool_call, awrap_tool_call
# # from langchain.messages import ToolMessage     #ye dekh lena
# from langchain_core.messages import ToolMessage

# from langgraph.checkpoint.memory import MemorySaver
# from fastapi import APIRouter, Depends, HTTPException
# from bson import ObjectId
# from bson.errors import InvalidId
# from utils.env_loaders import load_groq_api, load_gemini_api
# from utils.loggers import logger
# from utils.users import get_current_user
# from utils.response import success_response, error_response
# from database.db import agents_collection, users_collection, vector_collection
# from src.tools import get_tools_for_agent
# from database.models import AgentRunRequest
# from pydantic import SecretStr

# from langchain_mongodb import MongoDBAtlasVectorSearch
# from langchain_huggingface import HuggingFaceEmbeddings
# from pymongo import MongoClient


# runner_router = APIRouter(prefix="/chat" , tags=["Agent Runner"])


# #- Agent Runner Functions
# def get_llm(provider: str, model: str, temp):
#     provider = provider.lower()

#     if provider == "groq":
#         logger.info(f"Initializing Groq LLM with model: {model}")
#         return ChatGroq(
#             model=model,
#             temperature=temp,
#             api_key= SecretStr(load_groq_api())
#         )

#     elif provider == "gemini":
#         logger.info(f"Initializing Gemini LLM with model: {model}")
#         return ChatGoogleGenerativeAI(
#             model=model,
#             temperature=temp,
#             google_api_key=load_gemini_api()
#         )

#     else:
#         logger.error(f"Unsupported LLM provider: {provider}")
#         raise ValueError(f"Unsupported provider: {provider}")


# def extract_agent_response_content(result):
#     messages = result.get("messages", [])

#     for message in reversed(messages):
#         if getattr(message, "type", "") == "ai":
#             content = message.content

#             if isinstance(content, str):
#                 return content

#             if isinstance(content, list):
#                 output = []

#                 for item in content:
#                     if isinstance(item, dict) and item.get("type") == "text":
#                         output.append(item.get("text", ""))

#                 if output:
#                     return "\n".join(output)

#                 return str(content)

#             return str(content)

#     return ""


# def serialize_agent_messages(result):
#     serialized_messages = []
#     messages = result.get("messages", [])

#     for message in messages:
#         serialized_messages.append(
#             {
#                 "type": getattr(message, "type", ""),
#                 "content": message.content
#             }
#         )

#     return serialized_messages


# def agent_builder(agent_config: dict):
#     logger.info(f"Agent builder started for agent: {agent_config['name']}")

#     llm = get_llm(agent_config['llm_provider'], agent_config['llm_model'], agent_config['temperature'])
#     tools = get_tools_for_agent(agent_config.get('tools', []))

#     # #- Tool Error Handler
#     # from langchain_core.messages import ToolMessage
#     # from langchain_core.middleware import awrap_tool_call
#     # @awrap_tool_call
#     # async def handle_tool_errors(request, handler):
#     #     try:
#     #         return await handler(request)
#     #     except Exception as e:
#     #         logger.error(f"Tool execution failed for agent: {agent_config['name']} | Error: {str(e)}")
#     #         return ToolMessage(
#     #             content=f"Tool error: Please check your input and try again. ({str(e)})",
#     #             tool_call_id=request.tool_call["id"]
#     #         )


#     provider_specific_prompt = ''
#     if agent_config['llm_provider'] == 'groq':
#         provider_specific_prompt = """When you are supposed to do web search please use web_search tool. The web search tool takes string as input and will give you a list of results, what you need to do is pass the user query as string input and what you get in return is a list, so based on that please give appropriate answer to the user."""




#     system_promt_instructions = f"""
#                 Your name is "{agent_config['name']}", and this is what your description is given to the user "{agent_config['description']}".
#                 Your Role is {agent_config['role']}

#                 Your instructions:
#                 - Be Polite, Helpful, and assist user with queries.
#                 - {agent_config['instruction']}


#                 You are an AI assistant with access to tools.
#                 -{provider_specific_prompt}


# """

#     memory = MemorySaver()

#     agent = create_agent(
#         llm,
#         tools=tools,
#         system_prompt=system_promt_instructions,
#         checkpointer=memory,
#         # middleware=[handle_tool_errors]
#     )

#     logger.info(f"Agent built successfully for agent: {agent_config['name']}")
#     return agent





# #- RAG: Fetch relevant context from vector store
# def fetch_rag_context(query: str, owner_id: str, custom_db_settings: dict = None):

#     embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

#     #- Determine target collection
#     target_collection = None

#     if custom_db_settings and custom_db_settings.get('linked') is True:
#         mongo_settings = custom_db_settings.get('mongo_db', {})
#         connection_string = mongo_settings.get('connection_string')
#         db_name = mongo_settings.get('db_name')
#         collection_name = mongo_settings.get('collection_name')

#         if connection_string and db_name and collection_name:
#             try:
#                 custom_client = MongoClient(connection_string)
#                 target_collection = custom_client[db_name][collection_name]
#                 logger.info(f"RAG: Using custom DB for owner: {owner_id}")
#             except Exception as e:
#                 logger.error(f"RAG: Failed to connect to custom DB for owner {owner_id}: {e}")
#                 target_collection = None

#     if target_collection is None:
#         target_collection = vector_collection
#         logger.info(f"RAG: Using default vector collection for owner: {owner_id}")

#     #- Check collection has data for this owner before querying
#     try:
#         doc_count = target_collection.count_documents({'owner_id': ObjectId(owner_id)})
#         if doc_count == 0:
#             logger.info(f"RAG: No documents found for owner: {owner_id}, skipping KB injection")
#             return ""
#     except Exception as e:
#         logger.error(f"RAG: Count check failed for owner {owner_id}: {e}")
#         return ""

#     vector_store = MongoDBAtlasVectorSearch(
#         collection=target_collection,
#         embedding=embeddings,
#         index_name="vector_index_qab"
#     )

#     retriever = vector_store.as_retriever(
#         search_type="similarity",
#         search_kwargs={
#             "k": 3,
#             "pre_filter": {
#                 "owner_id": {"$eq": ObjectId(owner_id)}
#             }
#         }
#     )

#     docs = retriever.invoke(query)
#     if docs:
#         return "\n\n".join([doc.page_content for doc in docs])

#     return ""


# @runner_router.post("/run/{agent_id}")
# async def run_agent(agent_id: str, request: AgentRunRequest, current_user: dict = Depends(get_current_user)):
#     try:
#         logger.info(f"Agent run request received for agent id: {agent_id} from {current_user['email']}")

#         try:
#             obj_id = ObjectId(agent_id)
#         except InvalidId:
#             logger.warning(f"Agent run rejected due to invalid agent id format: {agent_id}")
#             raise HTTPException(status_code=400, detail="Invalid agent ID format")

#         agent_data = await agents_collection.find_one(
#             {
#                 "_id": obj_id,
#                 "owner_id": ObjectId(current_user["_id"])
#             }
#         )

#         if not agent_data:
#             logger.warning(f"Agent run failed because agent was not found for agent id: {agent_id} and user: {current_user['email']}")
#             return error_response(status_code=404, message="Agent not found")

#         agent = agent_builder(agent_data)
#         thread_id = request.thread_id or str(uuid4())

#         #- RAG: Inject context if knowledge_base is enabled
#         rag_message = request.query

#         if agent_data.get('knowledge_base') is True:
#             try:
#                 user_data = await users_collection.find_one({'_id': ObjectId(current_user['_id'])})
#                 custom_db = user_data.get('custom_db', {}) if user_data else {}

#                 context = fetch_rag_context(request.query, str(current_user['_id']), custom_db)

#                 if context:
#                     rag_message = f"""Use the following context to answer if needed:
# {context}

# User question:
# {request.query}"""
#                     logger.info(f"RAG context injected for agent id: {agent_id}")
#                 else:
#                     logger.info(f"No KB context found, running agent without RAG for agent id: {agent_id}")

#             except Exception as e:
#                 logger.error(f"Knowledge base retrieval failed for agent id: {agent_id} | Error: {str(e)}")
#                 #fallback

#         logger.info(f"Running agent id: {agent_id} with thread id: {thread_id}")
#         result = await agent.ainvoke(
#             {"messages": [{"role": "user", "content": rag_message}]},
#             config={"configurable": {"thread_id": thread_id}}
#         )

#         response = extract_agent_response_content(result)
#         serialized_messages = serialize_agent_messages(result)

#         logger.info(f"Agent run completed successfully for agent id: {agent_id}")
#         return success_response(
#             200,
#             data={
#                 "agent_id": agent_id,
#                 "thread_id": thread_id,
#                 "response": response,
#                 "messages": serialized_messages
#             },
#             message="Agent response generated successfully!"
#         )

#     except HTTPException:
#         raise

#     except Exception as e:
#         logger.error(f"Agent run failed for agent id: {agent_id} | Error: {str(e)}")
#         return error_response(status_code=500, message="Internal server error")


from dotenv import load_dotenv
import os
from uuid import uuid4
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langchain_core.messages import ToolMessage

from langgraph.checkpoint.memory import MemorySaver
from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from bson.errors import InvalidId
from utils.env_loaders import load_groq_api, load_gemini_api
from utils.loggers import logger
from utils.users import get_current_user
from utils.response import success_response, error_response
from database.db import agents_collection, users_collection, vector_collection
from src.tools import get_tools_for_agent
from database.models import AgentRunRequest
from pydantic import SecretStr

from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_postgres import PGVector
from langchain_huggingface import HuggingFaceEmbeddings
from pymongo import MongoClient


runner_router = APIRouter(prefix="/chat", tags=["Agent Runner"])


#- Agent Runner Functions
def get_llm(provider: str, model: str, temp):
    provider = provider.lower()

    if provider == "groq":
        logger.info(f"Initializing Groq LLM with model: {model}")
        return ChatGroq(
            model=model,
            temperature=temp,
            api_key=SecretStr(load_groq_api())
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

    provider_specific_prompt = ''
    if agent_config['llm_provider'] == 'groq':
        provider_specific_prompt = """When you are supposed to do web search please use web_search tool. The web search tool takes string as input and will give you a list of results, what you need to do is pass the user query as string input and what you get in return is a list, so based on that please give appropriate answer to the user."""

    system_promt_instructions = f"""
                Your name is "{agent_config['name']}", and this is what your description is given to the user "{agent_config['description']}".
                Your Role is {agent_config['role']}

                Your instructions:
                - Be Polite, Helpful, and assist user with queries.
                - {agent_config['instruction']}


                You are an AI assistant with access to tools.
                -{provider_specific_prompt}

"""

    memory = MemorySaver()

    agent = create_agent(
        llm,
        tools=tools,
        system_prompt=system_promt_instructions,
        checkpointer=memory,
    )

    logger.info(f"Agent built successfully for agent: {agent_config['name']}")
    return agent


#- RAG: Fetch relevant context from vector store
def fetch_rag_context(query: str, owner_id: str, custom_db_settings: dict = None):

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    provider = custom_db_settings.get('provider') if custom_db_settings else None
    config = custom_db_settings.get('config', {}) if custom_db_settings else {}
    is_linked = custom_db_settings.get('linked', False) if custom_db_settings else False

    #- Postgres / Supabase (pgvector) path
    if is_linked and provider == 'postgres':
        connection_string = config.get('connection_string')
        if not connection_string:
            logger.error(f"RAG: Postgres connection string missing for owner {owner_id}. Falling back to default collection.")
        else:
            try:
                logger.info(f"RAG: Using custom Postgres (pgvector) for owner: {owner_id}")
                vector_store = PGVector(
                    embeddings=embeddings,
                    collection_name=f"embeddings",
                    connection=connection_string,
                    use_jsonb=True,
                )
                retriever = vector_store.as_retriever(
                    search_type="similarity",
                    search_kwargs={"k": 3}
                )
                docs = retriever.invoke(query)
                if docs:
                    return "\n\n".join([doc.page_content for doc in docs])
                return ""
            except Exception as e:
                logger.error(f"RAG: Postgres retrieval failed for owner {owner_id}: {e}")
                return ""

    #- MongoDB path (custom or default)
    target_collection = None

    if is_linked and provider == 'mongo':
        connection_string = config.get('connection_string')
        db_name = config.get('db_name')
        collection_name = config.get('collection_name')

        if connection_string and db_name and collection_name:
            try:
                custom_client = MongoClient(connection_string)
                target_collection = custom_client[db_name][collection_name]
                logger.info(f"RAG: Using custom MongoDB for owner: {owner_id}")
            except Exception as e:
                logger.error(f"RAG: Failed to connect to custom MongoDB for owner {owner_id}: {e}")
                target_collection = None

    if target_collection is None:
        target_collection = vector_collection
        logger.info(f"RAG: Using default vector collection for owner: {owner_id}")

    #- Check collection has data for this owner before querying
    try:
        doc_count = target_collection.count_documents({'owner_id': ObjectId(owner_id)})
        if doc_count == 0:
            logger.info(f"RAG: No documents found for owner: {owner_id}, skipping KB injection")
            return ""
    except Exception as e:
        logger.error(f"RAG: Count check failed for owner {owner_id}: {e}")
        return ""

    vector_store = MongoDBAtlasVectorSearch(
        collection=target_collection,
        embedding=embeddings,
        index_name="vector_index_qab"
    )

    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": 3,
            "pre_filter": {
                "owner_id": {"$eq": ObjectId(owner_id)}
            }
        }
    )

    docs = retriever.invoke(query)
    if docs:
        return "\n\n".join([doc.page_content for doc in docs])

    return ""


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
            logger.warning(f"Agent not found for agent id: {agent_id} and user: {current_user['email']}")
            return error_response(status_code=404, message="Agent not found")

        agent = agent_builder(agent_data)
        thread_id = request.thread_id or str(uuid4())

        #- RAG: Inject context if knowledge_base is enabled
        rag_message = request.query

        if agent_data.get('knowledge_base') is True:
            try:
                user_data = await users_collection.find_one({'_id': ObjectId(current_user['_id'])})
                custom_db = user_data.get('custom_db', {}) if user_data else {}

                context = fetch_rag_context(request.query, str(current_user['_id']), custom_db)

                if context:
                    rag_message = f"""Use the following context to answer if needed:
{context}

User question:
{request.query}"""
                    logger.info(f"RAG context injected for agent id: {agent_id}")
                else:
                    logger.info(f"No KB context found, running agent without RAG for agent id: {agent_id}")

            except Exception as e:
                logger.error(f"Knowledge base retrieval failed for agent id: {agent_id} | Error: {str(e)}")
                #fallback

        logger.info(f"Running agent id: {agent_id} with thread id: {thread_id}")
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": rag_message}]},
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