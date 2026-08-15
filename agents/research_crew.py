"""
agents/research_crew.py
------------------------
CrewAI setup using Groq integration.
"""

import os
import re
import time
import litellm
from dotenv import load_dotenv
from crewai import LLM, Agent, Crew, Process, Task
from config import config
from tools.search_tool import web_search

load_dotenv()

# Tell LiteLLM to drop unsupported parameters
litellm.drop_params = True

# Patch LiteLLM completion to strip nested 'cache_breakpoint' keys from messages
_original_completion = litellm.completion

def _cleaned_completion(*args, **kwargs):
    if "messages" in kwargs and isinstance(kwargs["messages"], list):
        for msg in kwargs["messages"]:
            if isinstance(msg, dict):
                msg.pop("cache_breakpoint", None)
    return _original_completion(*args, **kwargs)

litellm.completion = _cleaned_completion

# Clean model string dynamically from config
_clean_model = (
    str(config.MODEL_NAME)
    .replace("groq/", "")
    .replace("gemini/", "")
    .replace("openai/", "")
    .strip()
)

# Configure CrewAI LLM with max_tokens from config
crew_llm = LLM(
    model=f"groq/{_clean_model}",
    api_key=os.getenv("GROQ_API_KEY") or getattr(config, "GROQ_API_KEY", None),
    temperature=getattr(config, "TEMPERATURE", 0.3),
    max_tokens=getattr(config, "MAX_TOKENS", 4096),
    drop_params=True,
)


def build_research_crew(topic: str) -> Crew:
    researcher = Agent(
        role="Lead Tech Researcher",
        goal=f"Gather comprehensive, exhaustive, and highly detailed factual insights about: {topic}",
        backstory=(
            "You are an expert technology researcher specializing in emerging tech, "
            "optimization algorithms, and complex systems. You dig deep to find extensive data."
        ),
        llm=crew_llm,
        tools=[web_search],
        max_iter=4,
        verbose=True,
    )

    analyst = Agent(
        role="Senior Research Analyst and Technical Writer",
        goal=f"Synthesize research findings into a comprehensive, long-form publication-grade report about: {topic}",
        backstory=(
            "You are a meticulous technical writer and analyst capable of taking raw research "
            "and writing expansive, multi-page deep-dive reports complete with deep sections and analysis."
        ),
        llm=crew_llm,
        max_iter=3,
        verbose=True,
    )

    research_task = Task(
        description=(
            f"Conduct exhaustive research on the following topic:\n'{topic}'\n\n"
            "Perform multiple searches if needed to gather a massive amount of data covering "
            "technical architectures, algorithms, core metrics, trends, challenges, and real-world implementations."
        ),
        expected_output=(
            "An extensive and detailed collection of raw research findings, technical notes, "
            "metrics, concepts, and complete source attribution links."
        ),
        agent=researcher,
    )

    analysis_task = Task(
        description=(
            f"Using the research data provided, write an exhaustive, publication-grade research report on: '{topic}'.\n\n"
            "CRITICAL LENGTH & STRUCTURE MANDATES:\n"
            "1. LENGTH: Aim for a comprehensive, long-form report (at least 1,500 words). Do not summarize briefly.\n"
            "2. SECTIONS: You must include:\n"
            "   - Executive Summary\n"
            "   - Background & Core Theoretical Framework\n"
            "   - Technical Deep Dive (Mechanisms, Equations, or Workflow Architecture)\n"
            "   - Practical Applications & Use Cases\n"
            "   - Challenges, Limitations, & Technical Hurdles\n"
            "   - Future Outlook\n"
            "   - Comprehensive Conclusion\n"
            "3. FORMATTING: Use markdown headings, data tables, and bullet points to elaborate fully on every point."
        ),
        expected_output=(
            "A massive, fully fleshed-out multi-section technical research report in clean markdown format."
        ),
        agent=analyst,
    )

    crew = Crew(
        agents=[researcher, analyst],
        tasks=[research_task, analysis_task],
        process=Process.sequential,
        verbose=True,
    )
    return crew


def _extract_retry_delay(error: Exception, default: int = 30) -> int:
    match = re.search(r"retryDelay['\"]?\s*:\s*['\"](\d+)s", str(error))
    if match:
        return int(match.group(1)) + 15
    return default


def run_research_crew(topic: str, max_attempts: int = 5) -> str:
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            crew = build_research_crew(topic)
            result = crew.kickoff()
            return str(result.raw) if hasattr(result, "raw") else str(result)
        except Exception as e:
            last_error = e
            if "429" in str(e) or "RATE_LIMIT_EXCEEDED" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                if attempt < max_attempts:
                    wait_seconds = _extract_retry_delay(e)
                    print(
                        f"[run_research_crew] Rate limited, waiting {wait_seconds}s before retry {attempt+1}/{max_attempts}..."
                    )
                    time.sleep(wait_seconds)
                    continue
            raise last_error
    raise last_error