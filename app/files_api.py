from __future__ import annotations

from pathlib import Path
from .openai_client import get_client

def upload_file(path: str) -> str:
    """Upload a file to the Files API (purpose='assistants') and return file_id."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    client = get_client()
    with p.open("rb") as f:
        result = client.files.create(file=f, purpose="assistants")
    return result.id
