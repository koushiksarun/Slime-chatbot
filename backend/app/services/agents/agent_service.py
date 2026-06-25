"""
Agent Service — LangChain ReAct agent with tool use.
Tools: web search, calculator, weather, document retrieval.
Agent is only invoked when the user opts in (use_agents=True).
"""
from typing import List, Optional, AsyncIterator
import json
import ast
import operator
import math

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.tools import tool
from langchain import hub
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from app.core.config import settings


# ── Tool definitions ──────────────────────────────────────────────────────────

@tool
async def web_search(query: str) -> str:
    """Search the web for current information. Use for recent events, live data."""
    if not settings.TAVILY_API_KEY:
        return "Web search is not configured (TAVILY_API_KEY missing)."
    from tavily import TavilyClient
    client = TavilyClient(api_key=settings.TAVILY_API_KEY)
    results = client.search(query=query, max_results=5)
    formatted = []
    for r in results.get("results", []):
        formatted.append(f"**{r['title']}**\n{r['content'][:300]}\nURL: {r['url']}")
    return "\n\n".join(formatted) or "No results found."


@tool
def calculator(expression: str) -> str:
    """
    Evaluate a mathematical expression safely.
    Supports: +, -, *, /, **, sqrt, sin, cos, tan, log, abs, round.
    Example: '(2 ** 10) + sqrt(144)'
    """
    safe_globals = {
        "__builtins__": {},
        "abs": abs, "round": round, "min": min, "max": max,
        "sqrt": math.sqrt, "log": math.log, "log10": math.log10,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "pi": math.pi, "e": math.e, "pow": pow,
    }
    try:
        # Whitelist check — only allow safe characters
        allowed = set("0123456789+-*/().** ,eE")
        allowed_words = {"sqrt", "log", "log10", "sin", "cos", "tan", "pi", "abs", "round", "min", "max", "pow"}
        cleaned = expression.replace(" ", "")
        for word in allowed_words:
            cleaned = cleaned.replace(word, "")
        if not all(c in allowed for c in cleaned):
            return "Expression contains disallowed characters."
        result = eval(expression, safe_globals)
        return str(round(float(result), 10))
    except Exception as e:
        return f"Calculation error: {e}"


@tool
async def get_weather(city: str) -> str:
    """Get current weather for a city. Example: 'London' or 'New York,US'"""
    if not settings.OPENWEATHER_API_KEY:
        return "Weather service is not configured."
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "q": city,
                "appid": settings.OPENWEATHER_API_KEY,
                "units": "metric",
            },
            timeout=10,
        )
        if response.status_code != 200:
            return f"Could not fetch weather for '{city}'."
        data = response.json()
        return (
            f"Weather in {data['name']}, {data['sys']['country']}:\n"
            f"  Condition: {data['weather'][0]['description'].title()}\n"
            f"  Temperature: {data['main']['temp']}°C (feels like {data['main']['feels_like']}°C)\n"
            f"  Humidity: {data['main']['humidity']}%\n"
            f"  Wind: {data['wind']['speed']} m/s"
        )


AVAILABLE_TOOLS = [web_search, calculator, get_weather]


class AgentService:
    """
    Wraps LangChain ReAct agent for multi-tool use.
    Non-streaming — returns final answer + tool call log.
    For streaming agent responses, use LangChain's streaming callbacks.
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.2,
        )

    async def run(self, user_message: str, history: List[dict]) -> dict:
        """Execute the ReAct agent and return result with tool call trace."""
        try:
            # Build history string for context
            history_str = "\n".join(
                f"{m['role'].upper()}: {m['content'][:200]}"
                for m in history[-10:]
            )

            augmented = (
                f"Conversation history:\n{history_str}\n\n"
                f"Current request: {user_message}"
            ) if history_str else user_message

            # Use LangChain's prebuilt ReAct prompt from hub
            # Falls back to inline prompt if hub unavailable
            prompt = hub.pull("hwchase17/react")

            agent = create_react_agent(self.llm, AVAILABLE_TOOLS, prompt)
            executor = AgentExecutor(
                agent=agent,
                tools=AVAILABLE_TOOLS,
                max_iterations=6,
                early_stopping_method="generate",
                handle_parsing_errors=True,
                return_intermediate_steps=True,
            )

            result = await executor.ainvoke({"input": augmented})

            tool_calls = []
            for action, observation in result.get("intermediate_steps", []):
                tool_calls.append({
                    "tool": action.tool,
                    "input": action.tool_input,
                    "output": str(observation)[:500],
                })

            return {
                "content": result["output"],
                "tool_calls": tool_calls,
            }

        except Exception as e:
            return {
                "content": f"I encountered an error while processing your request: {str(e)}",
                "tool_calls": [],
            }
