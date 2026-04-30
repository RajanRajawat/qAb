import asyncio, base64, requests
from email.message import EmailMessage
from typing import Literal
from langchain_core.tools import BaseTool, StructuredTool, tool
from pydantic import BaseModel, Field
from tavily import TavilyClient
from database.models import AgentTool
from utils.env_loaders import load_tavily_api
from utils.knowledge_base_helpers import search_kb_chunks
from utils.loggers import logger
from utils.tool_helpers import GMAIL_TOOL_KEY, WEB_SEARCH_TOOL_KEY, get_valid_gmail_access_token

#- tools
@tool
async def web_search(query: str) -> str:
    """
    Search the web using Tavily, returns top results.
    Input pass only string as shown below.

    Args:
        query: The search query string.
    """
    try:
        logger.info(f"Web search tool invoked for query: {query}")

        tavily_api_key = load_tavily_api
        if not tavily_api_key:
            logger.error("Web search tool: TAVILY_API_KEY not set")
            return "Error: Tavily API key is not configured."

        tavily_client = TavilyClient(api_key=tavily_api_key)
        response = tavily_client.search(query)
        results = response.get("results", [])

        if not results:
            logger.warning(f"Web search returned no results for query: {query}")
            return "No results found."

        output = []
        for result in results:
            output.append(f"Title: {result['title']} | URL: {result['url']} | {result['content']}")

        logger.info(f"Web search tool executed successfully for query: {query}")
        return "\n\n".join(output)

    except Exception as exc:
        logger.error(f"Web search tool execution failed for query: {query} | Error: {str(exc)}")
        return f"Error: {str(exc)}"

#- RAG Tools

class RagChunksInput(BaseModel):
    query: str = Field(description="Focused search query for the attached knowledge base.")
    limit: int = Field(default=3, ge=1, le=5, description="Maximum number of relevant chunks to return.")


def _format_rag_chunks(results: list) -> str:
    if not results:
        return "No relevant knowledge base chunks were found."

    formatted_chunks = []

    for index, item in enumerate(results, start=1):
        doc, score = item
        content = getattr(doc, "page_content", "").strip()
        if not content:
            continue

        metadata = getattr(doc, "metadata", {}) or {}
        source = metadata.get("file_name") or metadata.get("source") or "Unknown source"
        formatted_chunks.append(
            "\n".join([
                f"Chunk {index}",
                f"Source: {source}",
                f"Score: {score}",
                "Content:",
                content,
            ])
        )

    if not formatted_chunks:
        return "No relevant knowledge base chunks were found."

    return "\n\n".join(formatted_chunks)


def _search_rag_chunks(query: str, owner_id: str, kb_entry: dict, db_entry: dict | None, limit: int) -> str:
    kb_id = str(kb_entry["_id"])

    try:
        results = search_kb_chunks(query, owner_id, kb_entry, db_entry, limit)
        return _format_rag_chunks(results)

    except Exception as exc:
        logger.error(f"RAG tool retrieval failed for kb {kb_id}: {exc}")
        if "Expecting value" in str(exc):
            logger.error("Hugging Face API returned non-JSON response. Check API status or token.")
        return "Knowledge base retrieval failed. Try answering from available context or ask the user to retry."


def build_rag_chunks_tool(owner_id: str, kb_entry: dict, db_entry: dict | None = None) -> BaseTool:
    async def get_rag_chunks(query: str, limit: int = 3) -> str:
        clean_query = query.strip() if query else ""
        if not clean_query:
            return "get_rag_chunks requires a non-empty query."

        logger.info(f"RAG chunks tool invoked for kb {kb_entry['_id']} with query: {clean_query}")
        return await asyncio.to_thread(
            _search_rag_chunks,
            clean_query,
            owner_id,
            kb_entry,
            db_entry,
            limit,
        )

    return StructuredTool.from_function(
        coroutine=get_rag_chunks,
        name="get_rag_chunks",
        args_schema=RagChunksInput,
        description=(
            "Search the agent's attached knowledge base and return the most relevant text chunks. "
            "Use this only when the user's question likely depends on uploaded knowledge-base files "
            "or when document-specific details are needed."
        ),
    )


#-Gmail Tools   

class GmailToolInput(BaseModel):
    action: Literal["fetch_emails", "send_email", "reply_to_thread"] = Field(
        description="The Gmail action to execute."
    )
    query: str | None = Field(default=None, description="Gmail search query to use when fetching emails.")
    max_results: int = Field(default=5, ge=1, le=10, description="Maximum emails to fetch.")
    to: str | None = Field(default=None, description="Recipient email address for send or reply actions.")
    subject: str | None = Field(default=None, description="Subject line for send or reply actions.")
    body: str | None = Field(default=None, description="Email body content for send or reply actions.")
    thread_id: str | None = Field(default=None, description="Thread id required for reply_to_thread.")


def _gmail_request(access_token: str, method: str, path: str, **kwargs):
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {access_token}"
    response = requests.request(
        method,
        f"https://gmail.googleapis.com/gmail/v1/{path.lstrip('/')}",
        headers=headers,
        timeout=20,
        **kwargs,
    )
    response.raise_for_status()
    return response.json()


def _message_to_raw(to_email: str, subject: str, body: str, extra_headers: dict | None = None):
    message = EmailMessage()
    message["To"] = to_email
    message["Subject"] = subject

    for key, value in (extra_headers or {}).items():
        if value:
            message[key] = value

    message.set_content(body)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return raw


def _extract_header(headers: list[dict], header_name: str):
    for header in headers:
        if header.get("name", "").lower() == header_name.lower():
            return header.get("value")
    return None


def build_gmail_tool(tool_config: dict):
    async def gmail_tool(
        action: str,
        query: str | None = None,
        max_results: int = 5,
        to: str | None = None,
        subject: str | None = None,
        body: str | None = None,
        thread_id: str | None = None,
    ) -> str:
        try:
            logger.info(f"Gmail tool invoked for action: {action}")
            access_token = await get_valid_gmail_access_token(tool_config)

            if action == "fetch_emails":
                payload = _gmail_request(
                    access_token,
                    "GET",
                    "users/me/messages",
                    params={"q": query or "", "maxResults": max_results},
                )
                messages = payload.get("messages", [])

                if not messages:
                    return "No emails matched that Gmail query."

                output = []
                for item in messages:
                    detail = _gmail_request(
                        access_token,
                        "GET",
                        f"users/me/messages/{item['id']}",
                        params={
                            "format": "metadata",
                            "metadataHeaders": ["From", "Subject", "Date"],
                        },
                    )
                    headers = detail.get("payload", {}).get("headers", [])
                    output.append(
                        "\n".join([
                            f"Message ID: {detail.get('id')}",
                            f"Thread ID: {detail.get('threadId')}",
                            f"From: {_extract_header(headers, 'From') or 'Unknown'}",
                            f"Subject: {_extract_header(headers, 'Subject') or '(no subject)'}",
                            f"Date: {_extract_header(headers, 'Date') or 'Unknown'}",
                            f"Snippet: {detail.get('snippet', '')}",
                        ])
                    )

                return "\n\n".join(output)

            if action == "send_email":
                if not to or not subject or not body:
                    return "send_email requires to, subject, and body."

                result = _gmail_request(
                    access_token,
                    "POST",
                    "users/me/messages/send",
                    json={"raw": _message_to_raw(to, subject, body)},
                )
                return f"Email sent successfully. Message ID: {result.get('id')}"

            if action == "reply_to_thread":
                if not thread_id or not body:
                    return "reply_to_thread requires thread_id and body."

                thread = _gmail_request(
                    access_token,
                    "GET",
                    f"users/me/threads/{thread_id}",
                    params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Message-ID", "References"]},
                )
                messages = thread.get("messages", [])
                if not messages:
                    return "Could not find that Gmail thread."

                last_message = messages[-1]
                headers = last_message.get("payload", {}).get("headers", [])
                to_email = to or _extract_header(headers, "From")
                base_subject = subject or _extract_header(headers, "Subject") or "Re:"
                message_id = _extract_header(headers, "Message-ID")
                references = _extract_header(headers, "References")

                if not to_email:
                    return "Could not determine the recipient for this thread. Pass the to field explicitly."

                reply_subject = base_subject if base_subject.lower().startswith("re:") else f"Re: {base_subject}"
                extra_headers = {
                    "In-Reply-To": message_id,
                    "References": f"{references} {message_id}".strip() if references else message_id,
                }
                result = _gmail_request(
                    access_token,
                    "POST",
                    "users/me/messages/send",
                    json={
                        "threadId": thread_id,
                        "raw": _message_to_raw(to_email, reply_subject, body, extra_headers),
                    },
                )
                return f"Reply sent successfully. Message ID: {result.get('id')}"

            return "Unsupported Gmail action. Use fetch_emails, send_email, or reply_to_thread."

        except Exception as exc:
            logger.error(f"Gmail tool execution failed | Error: {exc}")
            return f"Error: {exc}"

    return StructuredTool.from_function(
        coroutine=gmail_tool,
        name="gmail_tool",
        args_schema=GmailToolInput,
        description=(
            "Use Gmail after the user has connected Google auth. "
            "Supported actions: fetch_emails, send_email, reply_to_thread. "
            "For fetch_emails provide a Gmail search query and optional max_results. "
            "For send_email provide to, subject, and body. "
            "For reply_to_thread provide thread_id and body, plus to or subject when needed."
        ),
    )


def normalize_agent_tool(tool_value: AgentTool | str) -> str:
    if isinstance(tool_value, AgentTool):
        return tool_value.value

    if isinstance(tool_value, str):
        try:
            return AgentTool(tool_value).value
        except ValueError as exc:
            logger.error(f"Unknown tool configured for agent: {tool_value}")
            raise ValueError(f"Unsupported tool configured for agent: {tool_value}") from exc

    logger.error(f"Invalid tool type configured for agent: {type(tool_value).__name__}")
    raise TypeError(f"Invalid tool type configured for agent: {type(tool_value).__name__}")


def get_tools_for_agent(agent_tools: list[AgentTool | str], tool_configs: dict[str, dict]) -> list[BaseTool]:
    resolved_tools: list[BaseTool] = []
    normalized_tools = [normalize_agent_tool(tool_value) for tool_value in agent_tools]
    logger.info(f"Resolving tools for agent: {normalized_tools}")

    for tool_key in normalized_tools:
        if tool_key == WEB_SEARCH_TOOL_KEY:
            resolved_tools.append(web_search)
            continue

        if tool_key == GMAIL_TOOL_KEY:
            gmail_config = tool_configs.get(GMAIL_TOOL_KEY)
            if not gmail_config or gmail_config.get("status") != "connected":
                raise ValueError("Gmail is not configured for this user.")
            resolved_tools.append(build_gmail_tool(gmail_config))
            continue

        raise ValueError(f"Unsupported tool configured for agent: {tool_key}")

    return resolved_tools
