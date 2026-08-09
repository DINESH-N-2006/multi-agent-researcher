# Multi-Agent Research System

An AI research pipeline that combines **LangGraph** (workflow orchestration + human-in-the-loop) with **CrewAI** (collaborative agent crews) to research a topic, fact-check it, write a report, and require human approval before finalizing.

## Architecture

```
User submits topic
        │
        ▼
┌────────────────────────────┐
│      LangGraph graph        │
│                             │
│  research ──► calls a CrewAI Crew:
│     │            Researcher agent (web search)
│     │                  │
│     │                  ▼
│     │            Analyst agent (synthesizes findings)
│     ▼
│  fact_check   (LLM verifies claims, flags disputed ones)
│     ▼
│  write        (LLM drafts a Markdown report)
│     ▼
│  human_approval   ⏸  PAUSES — waits for a human decision
│     │  approved → finalize → END
│     │  rejected → back to write (with feedback), up to MAX_REVISIONS
└────────────────────────────┘
```

**Why two frameworks?** LangGraph is the right tool for fine-grained control flow and pausing for human input. CrewAI is the right tool for a small team of agents collaborating on one sub-task. This project shows both used for what they're each best at, nested together — a common real-world pattern.

## Project structure

```
multi-agent-research-system/
├── README.md
├── requirements.txt
├── .env.example
├── config.py              # centralized settings
├── main.py                # CLI entry point + human approval loop
├── models/
│   ├── state.py            # LangGraph shared state (TypedDict)
│   └── schemas.py          # Pydantic models for structured data
├── tools/
│   └── search_tool.py      # DuckDuckGo web search tool
├── prompts/
│   └── agent_prompts.py    # all prompts, centralized
├── agents/
│   └── research_crew.py    # CrewAI: Researcher + Analyst agents
├── graph/
│   └── workflow.py         # LangGraph: 5-node graph + interrupt
└── tests/
    └── test_workflow.py    # structural tests, no API calls
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env and add your OPENAI_API_KEY
```

## Run

```bash
python main.py "The environmental impact of lithium mining"
```

The pipeline will research, fact-check, and draft a report, then pause and print it in your terminal asking `Approve this report? (y/n)`. Reject it to send feedback back to the writer for a revision (up to 2 revision rounds).

## Run tests

```bash
pytest tests/ -v
```

## Possible extensions

- Swap `MemorySaver` for a persistent checkpointer (e.g. Postgres) so approval can happen across separate process runs / a real web UI instead of a blocking terminal prompt.
- Add a `hierarchical` CrewAI process with a manager agent for more complex research topics needing multiple specialized sub-researchers.
- Force structured LLM output (`.with_structured_output(FactCheckResult)`) in `fact_check_node` instead of the current string-matching heuristic.
- Add a PDF export step after `finalize_node`.
