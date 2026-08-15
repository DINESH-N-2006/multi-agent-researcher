"""
config.py
---------
Central place for all settings.
"""

import os
from dotenv import load_dotenv

# Load .env for local development
load_dotenv()

# Try to load Streamlit Secrets when running on Streamlit Cloud
try:
    import streamlit as st
except ImportError:
    st = None


def get_setting(key: str, default=None):
    """
    Get configuration from:
    1. Streamlit Secrets (when deployed)
    2. Environment variables / .env (local)
    3. Default value
    """

    # Streamlit Cloud
    if st is not None:
        try:
            if key in st.secrets:
                return st.secrets[key]
        except Exception:
            pass

    # Local .env / environment variables
    return os.getenv(key, default)


class Config:
    """Central configuration for the application."""

    # --- LLM provider settings ---
    GROQ_API_KEY: str = get_setting("GROQ_API_KEY", "")
    GEMINI_API_KEY: str = get_setting("GEMINI_API_KEY", "")

    # Default model ID for Groq
    MODEL_NAME: str = get_setting(
        "MODEL_NAME",
        "llama-3.3-70b-versatile"
    )

    TEMPERATURE: float = float(
        get_setting("TEMPERATURE", "0.3")
    )

    # --- Expanded token limit for long, exhaustive reports ---
    MAX_TOKENS: int = int(
        get_setting("MAX_TOKENS", "4096")
    )

    # --- Workflow settings ---
    MAX_RESEARCH_SOURCES: int = int(
        get_setting("MAX_RESEARCH_SOURCES", "6")
    )

    REQUIRE_HUMAN_APPROVAL: bool = (
        str(get_setting("REQUIRE_HUMAN_APPROVAL", "true")).lower()
        == "true"
    )

    # --- Paths ---
    OUTPUT_DIR: str = get_setting("OUTPUT_DIR", "outputs")

    @classmethod
    def validate(cls) -> None:
        """Validate required configuration."""

        # Require at least one API key (preferring GROQ_API_KEY)
        if not cls.GROQ_API_KEY and not cls.GEMINI_API_KEY:
            raise ValueError(
                "Neither GROQ_API_KEY nor GEMINI_API_KEY is configured. "
                "Add GROQ_API_KEY to Streamlit Secrets or your local .env file."
            )

        if cls.MAX_RESEARCH_SOURCES < 1:
            raise ValueError(
                "MAX_RESEARCH_SOURCES must be at least 1."
            )


config = Config()