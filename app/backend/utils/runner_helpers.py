import json
from langchain.agents import create_agent
from langchain_core.tools import StructuredTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from pydantic import SecretStr
from src.tools import get_tools_for_agent
from utils.data_query_helpers import build_data_query_schema_text, execute_data_query_source
from utils.env_loaders import load_gemini_api, load_groq_api
from utils.knowledge_base_helpers import search_kb_chunks
from utils.loggers import logger

def get_llm(provider: str, model: str, temp):
    provider = provider.lower()

    if provider == "groq":
        logger.info(f"Initializing Groq LLM with model: {model}")
        return ChatGroq(
            model=model,
            temperature=temp,
            api_key=SecretStr(load_groq_api),
        )

    if provider == "gemini":
        logger.info(f"Initializing Gemini LLM with model: {model}")
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temp,
            google_api_key=load_gemini_api,
        )

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
        serialized_messages.append({
            "type": getattr(message, "type", ""),
            "content": message.content,
        })

    return serialized_messages

def build_history_messages(history_items: list[dict]):
    messages = []

    for item in history_items:
        if item.get("role") not in {"user", "assistant"}:
            continue

        messages.append({
            "role": item["role"],
            "content": item.get("content", ""),
        })

    return messages


def build_data_query_tool(data_query_entry: dict, db_entry: dict):
    source_names = [source["name"] for source in data_query_entry.get("sources", [])]

    def query_data_query(source_name: str, query: str) -> str:
        try:
            rows = execute_data_query_source(data_query_entry, db_entry, source_name, query) #y
            return json.dumps(rows, ensure_ascii=False, default=str)
        except ValueError as exc:
            return f"Data Query tool error: {exc}"

    description = (
        "Read-only access to the configured Data Query sources. "
        f"Allowed sources: {', '.join(source_names)}. "
        f"Provider: {data_query_entry.get('provider')}. "
        "Never write, update, delete, drop, alter, or create anything. "
        "For MongoDB, pass a JSON object like "
        '{"operation":"find","filter":{},"projection":{"field":1},"limit":20} '
        "or an aggregate payload like "
        '{"operation":"aggregate","pipeline":[{"$match":{}}]}.'
    )

    return StructuredTool.from_function(
        func=query_data_query,
        name="query_data_query",
        description=description,
    )


def agent_builder(
    agent_config: dict,
    tool_configs: dict | None = None,
    data_query_entry: dict | None = None,
    data_query_db_entry: dict | None = None,
):
    logger.info(f"Agent builder started for agent: {agent_config['name']}")

    llm = get_llm(agent_config["llm_provider"], agent_config["llm_model"], agent_config["temperature"])
    tools = get_tools_for_agent(agent_config.get("tools", []), tool_configs or {})
    data_query_schema = ""
    if data_query_entry and data_query_db_entry:
        tools.append(build_data_query_tool(data_query_entry, data_query_db_entry))
        data_query_schema = build_data_query_schema_text(data_query_entry)

    provider_specific_prompt = ""
    if agent_config["llm_provider"] == "groq":
        provider_specific_prompt = """When you are supposed to do web search please use web_search tool. The web search tool takes string as input and will give you a list of results, what you need to do is pass the user query as string input and what you get in return is a list, so based on that please give appropriate answer to the user."""

    system_promt_instructions = f"""
                Your name is "{agent_config['name']}", and this is what your description is given to the user "{agent_config['description']}".
                Your Role is {agent_config['role']}

                Your instructions:
                - Be Polite, Helpful, and assist user with queries.
                - {agent_config['instruction']}


                You are an AI assistant with access to tools.
                -{provider_specific_prompt}
                -If a Data Query is attached, only use the query_data_query tool for read-only access and only for the configured sources.

                Attached Data Query schema:
                {data_query_schema or "No Data Query attached."}

"""

    agent = create_agent(
        llm,
        tools=tools,
        system_prompt=system_promt_instructions,
    )

    logger.info(f"Agent built successfully for agent: {agent_config['name']}")
    return agent


def fetch_rag_context(query: str, owner_id: str, kb_entry: dict, db_entry: dict | None = None):
    kb_id = str(kb_entry["_id"])
    try:
        results = search_kb_chunks(query, owner_id, kb_entry, db_entry, 3)

        if results:
            return "\n\n".join([item[0].page_content for item in results])

    except Exception as e:
        logger.error(f"RAG retrieval failed for kb {kb_id}: {str(e)}")
        if "Expecting value" in str(e):
            logger.error("Hugging Face API returned non-JSON response. Check API status or token.")

    return ""
