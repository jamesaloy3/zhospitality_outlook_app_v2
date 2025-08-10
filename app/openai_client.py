from __future__ import annotations

import os
from openai import OpenAI
from .config import load_settings

_client: OpenAI | None = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        settings = load_settings()
        os.environ["OPENAI_API_KEY"] = settings.api_key
        _client = OpenAI()
    return _client
