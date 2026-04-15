
import asyncio
import os
import wikipedia
import httpx

from tavily import TavilyClient
from datetime import datetime, timezone
from langchain_core.tools import tool, BaseTool
from database.models import AgentTool
from utils.loggers import logger
from utils.env_loaders import load_tavily_api


# #- Get Current DateTime
# @tool
# async def get_datetime() -> str:
#     """
#     Get the current UTC date and time.
#     """
#     try:
#         logger.info("Datetime tool invoked")
#         now = datetime.now(timezone.utc)
#         logger.info("Datetime tool executed successfully")
#         return (
#             f"UTC DateTime: {now.isoformat()} | "
#             f"Date: {now.date().isoformat()} | "
#             f"Time: {now.time().isoformat()}"
#         )
#     except Exception as e:
#         logger.error(f"Datetime tool execution failed | Error: {str(e)}")
#         return f"Error: {str(e)}"


# #- Get Weather
# @tool
# async def get_weather(city: str) -> str:
#     """
#     Get the current weather for a given city using Open-Meteo (free, no API key needed).

#     Args:
#         city: Name of the city to get weather for.
#     """
#     try:
#         logger.info(f"Weather tool invoked for city: {city}")
#         async with httpx.AsyncClient() as client:
#             geo = await client.get(
#                 f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
#             )
#             geo_data = geo.json()

#             if not geo_data.get("results"):
#                 logger.warning(f"Weather tool: city not found: {city}")
#                 return f"City '{city}' not found. Please check the city name."

#             location = geo_data["results"][0]

#             weather_resp = await client.get(
#                 f"https://api.open-meteo.com/v1/forecast"
#                 f"?latitude={location['latitude']}&longitude={location['longitude']}"
#                 f"&current_weather=true"
#             )

#         weather = weather_resp.json()["current_weather"]
#         logger.info(f"Weather tool executed successfully for city: {city}")
#         return (
#             f"City: {city} | "
#             f"Temperature: {weather['temperature']}°C | "
#             f"Wind Speed: {weather['windspeed']} km/h | "
#             f"Weather Code: {weather['weathercode']}"
#         )
#     except Exception as e:
#         logger.error(f"Weather tool execution failed for city: {city} | Error: {str(e)}")
#         return f"Error: {str(e)}"


#- Web Search
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

        tavily_api_key = load_tavily_api()
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
        for r in results:
            output.append(f"Title: {r['title']} | URL: {r['url']} | {r['content']}")

        logger.info(f"Web search tool executed successfully for query: {query}")
        return "\n\n".join(output)

    except Exception as e:
        logger.error(f"Web search tool execution failed for query: {query} | Error: {str(e)}")
        return f"Error: {str(e)}"


# #- Wikipedia Search
# @tool
# async def wikipedia_search(query: str) -> str:
#     """
#     Search Wikipedia and return a short summary.

#     Args:
#         query: The topic to search on Wikipedia.
#     """
#     try:
#         logger.info(f"Wikipedia tool invoked for query: {query}")

#         # wikipedia library is blocking/sync — offload to thread executor
#         # to avoid blocking the async event loop
#         loop = asyncio.get_event_loop()
#         summary = await loop.run_in_executor(
#             None, lambda: wikipedia.summary(query, sentences=3)
#         )

#         logger.info(f"Wikipedia tool executed successfully for query: {query}")
#         return f"Query: {query}\n\nSummary: {summary}"

#     except wikipedia.exceptions.DisambiguationError as e:
#         logger.warning(f"Wikipedia disambiguation for query: {query} | Options: {e.options[:5]}")
#         return f"Ambiguous query. Did you mean one of these? {', '.join(e.options[:5])}"

#     except wikipedia.exceptions.PageError:
#         logger.warning(f"Wikipedia page not found for query: {query}")
#         return f"No Wikipedia page found for '{query}'."

#     except Exception as e:
#         logger.error(f"Wikipedia tool execution failed for query: {query} | Error: {str(e)}")
#         return f"Error: {str(e)}"


#- Tool Registry
TOOL_REGISTRY: dict[AgentTool, BaseTool] = {
    AgentTool.WEB_SEARCH:  web_search,
    # AgentTool.WEATHER:     get_weather,
    # AgentTool.DATETIME:    get_datetime,
    # AgentTool.WIKIPEDIA:   wikipedia_search,
}


def normalize_agent_tool(tool: AgentTool | str) -> AgentTool:
    if isinstance(tool, AgentTool):
        return tool

    if isinstance(tool, str):
        try:
            return AgentTool(tool)
        except ValueError as exc:
            logger.error(f"Unknown tool configured for agent: {tool}")
            raise ValueError(f"Unsupported tool configured for agent: {tool}") from exc

    logger.error(f"Invalid tool type configured for agent: {type(tool).__name__}")
    raise TypeError(f"Invalid tool type configured for agent: {type(tool).__name__}")


def get_tools_for_agent(agent_tools: list[AgentTool | str]) -> list[BaseTool]:
    normalized_tools = [normalize_agent_tool(t) for t in agent_tools]
    logger.info(f"Resolving tools for agent: {[t.value for t in normalized_tools]}")
    return [TOOL_REGISTRY[t] for t in normalized_tools]