"""
agents/research_crew.py
------------------------
CrewAI setup using CrewAI's native LLM class for Gemini compatibility.
"""

from crewai import Agent, Crew, Process, Task, LLM
from config import config

# Initialize CrewAI native LLM wrapper for Gemini
crew_llm = LLM(
    model=config.MODEL_NAME,  # e.g., "gemini/gemini-2.5-flash"
    api_key=config.GEMINI_API_KEY,
    temperature=config.TEMPERATURE,
)


def build_research_crew(topic: str) -> Crew:
    # ── AGENT 1: Researcher ───────────────────────────────────────
    researcher = Agent(
        role="Lead Tech Researcher",
        goal=f"Gather comprehensive, factual insights about: {topic}",
        backstory=(
            "You are an expert technology researcher specializing in emerging tech, "
            "cybersecurity trends, and complex software developments."
        ),
        llm=crew_llm,
        verbose=True,
    )

    # ── AGENT 2: Analyst ─────────────────────────────────────────
    analyst = Agent(
        role="Research Analyst",
        goal=f"Synthesize, structure, and verify research finding details about: {topic}",
        backstory=(
            "You are a skilled research analyst capable of taking raw technical data "
            "and extracting key themes, actionable implications, and sources."
        ),
        llm=crew_llm,
        verbose=True,
    )

    # ── TASK 1: Conduct Research ─────────────────────────────────
    research_task = Task(
        description=(
            f"Conduct thorough research on the following topic:\n'{topic}'\n\n"
            "Identify key trends, technical challenges, future implications, "
            "and real-world examples or sources where available."
        ),
        expected_output=(
            "A detailed, structured research notes summary covering key facts, "
            "bullet points of major findings, and source links."
        ),
        agent=researcher,
    )

    # ── TASK 2: Analyze & Summarize ──────────────────────────────
    analysis_task = Task(
        description=(
            "Review the raw research findings provided by the Lead Researcher. "
            "Synthesize them into a clean, well-organized technical summary."
        ),
        expected_output=(
            "A formatted technical research summary highlighting key insights, "
            "core implications, and actionable takeaways."
        ),
        agent=analyst,
    )

    # ── CREW ASSEMBLY ────────────────────────────────────────────
    crew = Crew(
        agents=[researcher, analyst],
        tasks=[research_task, analysis_task],
        process=Process.sequential,
        verbose=True,
    )

    return crew


def run_research_crew(topic: str) -> str:
    """
    Constructs and executes the research crew, returning the output as string.
    """
    crew = build_research_crew(topic)
    result = crew.kickoff()
    return str(result)