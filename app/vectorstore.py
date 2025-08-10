from __future__ import annotations

from .config import load_settings, load_vector_store_id, save_vector_store_id
from .openai_client import get_client

def ensure_vector_store() -> str:
    """Return an existing vector store id (from env or state), or create a new one and persist it."""
    settings = load_settings()
    if settings.vector_store_id:
        return settings.vector_store_id
    existing = load_vector_store_id()
    if existing:
        return existing
    client = get_client()
    vs = client.vector_stores.create(name="Hospitality Vector Store")
    save_vector_store_id(vs.id)
    return vs.id
