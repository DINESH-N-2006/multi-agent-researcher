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
    GEMINI_API_KEY: str = get_setting("GEMINI_API_KEY", "")

    MODEL_NAME: str = get_setting(
        "MODEL_NAME",
        "gemini/gemini-2.5-flash"
    )

    TEMPERATURE: float = float(
        get_setting("TEMPERATURE", "0.3")
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

        if not cls.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY is not configured. "
                "Add it to Streamlit Secrets or your local .env file."
            )

        if cls.MAX_RESEARCH_SOURCES < 1:
            raise ValueError(
                "MAX_RESEARCH_SOURCES must be at least 1."
            )


config = Config()