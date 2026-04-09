from datetime import datetime, timezone
from langchain_core.tools import tool
import httpx
import os
import wikipedia
from dotenv import load_dotenv
from models.models import AgentTool
from langchain_core.tools import BaseTool
from utils.helpers import logger

load_dotenv()






#- Get Current DateTime
@tool
def get_datetime() -> str:
    """
    Get the current UTC date and time.
    """
    try:
        logger.info(f"Datetime tool invoked")
        now = datetime.now(timezone.utc)
        logger.info(f"Datetime tool executed successfully")
        return f"UTC DateTime: {now.isoformat()} | Date: {now.date().isoformat()} | Time: {now.time().isoformat()}"
    except Exception as e:
        logger.error(f"Datetime tool execution failed | Error: {str(e)}")
        return f"Error: {str(e)}"


#- Get Weather
@tool
async def get_weather(city: str) -> str:
    """
    Get the current weather for a given city using Open-Meteo (free, no API key needed).

    Args:
        city: Name of the city to get weather for.
    """
    try:
        logger.info(f"Weather tool invoked for city: {city}")
        async with httpx.AsyncClient() as client:
            geo = await client.get(f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1")
            location = geo.json()["results"][0]
            weather_resp = await client.get(
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={location['latitude']}&longitude={location['longitude']}"
                f"&current_weather=true"
            )
        weather = weather_resp.json()["current_weather"]
        logger.info(f"Weather tool executed successfully for city: {city}")
        return (
            f"City: {city} | "
            f"Temperature: {weather['temperature']}°C | "
            f"Wind Speed: {weather['windspeed']} km/h | "
            f"Weather Code: {weather['weathercode']}"
        )
    except Exception as e:
        logger.error(f"Weather tool execution failed for city: {city} | Error: {str(e)}")
        return f"Error: {str(e)}"


#- Web Search
@tool
async def web_search(query: str) -> str:
    """
    Search the web using Tavily and return top results.

    Args:
        query: The search query string.
    """
    try:
        logger.info(f"Web search tool invoked for query: {query}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": os.getenv("TAVILY_API_KEY"),
                    "query": query,
                    "max_results": 5,
                }
            )
        results = response.json().get("results", [])
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


#- Wikipedia Search
@tool
def wikipedia_search(query: str) -> str:
    """
    Search Wikipedia and return a short summary.

    Args:
        query: The topic to search on Wikipedia.
    """
    try:
        logger.info(f"Wikipedia tool invoked for query: {query}")
        summary = wikipedia.summary(query, sentences=3)
        logger.info(f"Wikipedia tool executed successfully for query: {query}")
        return f"Query: {query}\n\nSummary: {summary}"
    except Exception as e:
        logger.error(f"Wikipedia tool execution failed for query: {query} | Error: {str(e)}")
        return f"Error: {str(e)}"
    

TOOL_REGISTRY: dict[AgentTool, BaseTool] = {
    AgentTool.WEB_SEARCH:  web_search,
    AgentTool.WEATHER:     get_weather,
    AgentTool.DATETIME:    get_datetime,
    AgentTool.WIKIPEDIA:   wikipedia_search,
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
    normalized_tools = [normalize_agent_tool(tool) for tool in agent_tools]
    logger.info(f"Resolving tools for agent: {[tool.value for tool in normalized_tools]}")
    return [TOOL_REGISTRY[tool] for tool in normalized_tools]
