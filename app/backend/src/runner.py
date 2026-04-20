

#~ Agent Runner                                         
#: Todo:                                                
#:  Embedding Model Inference                           
#! Bugs:                                                
#- Notes:                                               


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
from utils.env_loaders import load_groq_api, load_gemini_api, load_hf_api
from utils.loggers import logger
from utils.users import get_current_user
from utils.response import success_response, error_response
from database.db import agents_collection, users_collection, vector_collection, kb_collection, db_collection
from src.tools import get_tools_for_agent
from database.models import AgentRunRequest
from pydantic import SecretStr

from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_postgres import PGVector
from langchain_huggingface import HuggingFaceEndpointEmbeddings
# from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from pymongo import MongoClient
from src.knowledge_base import get_mongo_collection_from_entry


runner_router = APIRouter(prefix="/chat", tags=["Agent Runner"])


#- Agent Runner 


#llm selectr
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


def extract_agent_response_content(result): #extrating only msgs
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


def fetch_rag_context(query: str, owner_id: str, kb_entry: dict, db_entry: dict | None = None):
    kb_id = str(kb_entry["_id"])
    try:
        embeddings = HuggingFaceEndpointEmbeddings(
                model="sentence-transformers/all-MiniLM-L6-v2",
                huggingfacehub_api_token=(load_hf_api()),
            )

        if db_entry and db_entry.get("provider") == "postgres":
            logger.info(f"RAG: Using custom Postgres for kb {kb_id}")
            vector_store = PGVector(
                embeddings=embeddings,
                collection_name="embeddings",
                connection=db_entry["config"]["connection_string"],
                use_jsonb=True,
            )
            docs = vector_store.similarity_search(
                query,
                k=3,
                filter={
                    "owner_id": owner_id,
                    "knowledge_base_id": kb_id,
                }
            )
            if docs:
                return "\n\n".join([doc.page_content for doc in docs])
            return ""

        target_collection = None
        if db_entry and db_entry.get("provider") == "mongo":
            target_collection = get_mongo_collection_from_entry(db_entry)
            logger.info(f"RAG: Using custom MongoDB for kb {kb_id}")

        if target_collection is None:
            target_collection = vector_collection
            logger.info(f"RAG: Using default vector collection for kb {kb_id}")

        # Check if index exists or at least if we have documents
        doc_count = target_collection.count_documents({
            'owner_id': owner_id,
            'knowledge_base_id': kb_id,
        })
        if doc_count == 0:
            logger.info(f"RAG: No documents found for kb {kb_id}, skipping KB injection")
            return ""

        vector_store = MongoDBAtlasVectorSearch(
            collection=target_collection,
            embedding=embeddings,
            index_name="vector_index_qab"
        )

        # Use similarity search directly to handle possible index errors more gracefully
        docs = vector_store.similarity_search(
            query,
            k=3,
            pre_filter={
                "owner_id": {"$eq": owner_id},
                "knowledge_base_id": {"$eq": kb_id},
            }
        )
        
        if docs:
            return "\n\n".join([doc.page_content for doc in docs])

    except Exception as e:
        logger.error(f"RAG retrieval failed for kb {kb_id}: {str(e)}")
        # If it's a JSON decode error, it's likely the embedding API
        if "Expecting value" in str(e):
             logger.error("Hugging Face API returned non-JSON response. Check API status or token.")
    
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


        rag_message = request.query
        
        if agent_data.get('knowledge_base') is True:    #- RAG Inject context if kb > True
            try:
                kb_id = agent_data.get("knowledge_base_id")
                if not kb_id:
                    return error_response(status_code=400, message="Agent does not have a knowledge base selected.")

                kb_entry = await kb_collection.find_one({
                    "_id": ObjectId(kb_id),
                    "owner_id": ObjectId(current_user["_id"])
                })
                if not kb_entry:
                    return error_response(status_code=404, message="Knowledge base not found for this agent.")

                db_entry = None
                if kb_entry.get("db_id") != "default":
                    db_entry = await db_collection.find_one({
                        "_id": ObjectId(kb_entry["db_id"]),
                        "owner_id": ObjectId(current_user["_id"])
                    })
                    if not db_entry:
                        return error_response(status_code=404, message="Knowledge base DB not found.")

                context = fetch_rag_context(request.query, str(current_user['_id']), kb_entry, db_entry)

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
