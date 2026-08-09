"""
config.py
---------
Central place for all settings. Why centralize?
  - If you need to switch models later, you change ONE line, not ten files.
  - Keeps secrets (API keys) out of the actual logic files.
  - Makes the codebase easy for a reviewer (or interviewer) to understand at a glance.
"""

import os
from dotenv import load_dotenv

# load_dotenv() reads the ".env" file in this folder and loads its
# key=value pairs into the environment variables (os.environ), so we
# can read them with os.getenv().
load_dotenv()


class Config:
    """
    A plain class used as a namespace for settings.
    We use class-level attributes so we can write
    Config.GEMINI_API_KEY anywhere without creating Config() first.
    """

    # --- LLM provider settings ---
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gemini/gemini-2.5-flash")
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.3"))
    # Temperature controls randomness: 0 = very focused/deterministic,
    # 1 = very creative/random. For research + fact-checking we want
    # low temperature so answers are consistent and grounded.

    # --- Workflow settings ---
    MAX_RESEARCH_SOURCES: int = int(os.getenv("MAX_RESEARCH_SOURCES", "6"))
    REQUIRE_HUMAN_APPROVAL: bool = os.getenv("REQUIRE_HUMAN_APPROVAL", "true").lower() == "true"

    # --- Paths ---
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "outputs")

    @classmethod
    def validate(cls) -> None:
        """
        Call this once at startup. Fails loudly and immediately if a
        required secret is missing ('fail fast' pattern).
        """
        if not cls.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY is not set. Copy .env.example to .env "
                "and fill in your Gemini API key."
            )
        if cls.MAX_RESEARCH_SOURCES < 1:
            raise ValueError("MAX_RESEARCH_SOURCES must be at least 1.")


config = Config()