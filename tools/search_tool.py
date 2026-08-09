"""
tools/search_tool.py
---------------------
A "tool" in agent frameworks is just a function the LLM is ALLOWED to
call when it decides it needs external information. Without tools,
an LLM can only use what it memorized during training (which goes
stale and can be wrong). With a search tool, the agent can look up
current information and ground its answer in real sources.

We use DuckDuckGo here because it needs no API key (great for a
portfolio project people can run without paying for a search API).
"""

from crewai.tools import tool
from duckduckgo_search import DDGS
from config import config


@tool("Web Search")
def web_search(query: str) -> str:
    """
    Searches the web for the given query and returns a formatted list
    of results (title, snippet, and URL for each).

    The @tool decorator does two things:
      1. Wraps this plain function so CrewAI agents can call it.
      2. Uses the function's docstring (this text!) as the
         description the LLM reads to decide WHEN to use this tool.
         That's why writing a clear docstring here isn't just for
         humans — the AI agent literally reads it to make decisions.
    """
    try:
        # DDGS() opens a DuckDuckGo search session. The "with" block
        # (context manager) makes sure the session is properly closed
        # afterward, even if an error happens inside.
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=config.MAX_RESEARCH_SOURCES))

        if not results:
            return f"No search results found for: {query}"

        # Build a human-readable string the LLM can read and reason
        # over. LLMs work with text, so we format structured data
        # (a list of dicts) into a clean numbered string.
        formatted = []
        for i, r in enumerate(results, start=1):
            title = r.get("title", "No title")
            body = r.get("body", "")
            href = r.get("href", "")
            formatted.append(f"{i}. {title}\n   {body}\n   Source: {href}")

        return "\n\n".join(formatted)

    except Exception as e:
        # Never let a tool crash the whole agent run. Return a clear
        # error message the agent can react to (e.g. try rephrasing
        # the query) instead of the program stopping entirely.
        return f"Search failed: {str(e)}"
