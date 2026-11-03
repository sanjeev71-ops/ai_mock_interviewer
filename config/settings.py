import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


def _setting(name: str, default: str | None = None) -> str | None:
    """Cloud secrets take precedence; local .env is optional."""
    try:
        value = st.secrets.get(name)
    except FileNotFoundError:
        value = None
    if value is None:
        value = os.getenv(name, default)
    return value


GROQ_API_KEY = _setting("GROQ_API_KEY")
GROQ_BASE_URL = _setting(
    "GROQ_BASE_URL",
    "https://api.groq.com/openai/v1",
)
GROQ_MODEL = _setting("GROQ_MODEL", "qwen/qwen3.8-27b")


if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is not configured. "
        "Add it to Streamlit Community Cloud app secrets "
        "or your local .env file."
    )
