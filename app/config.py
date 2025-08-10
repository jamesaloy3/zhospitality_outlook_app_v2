from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

APP_ROOT = Path(__file__).resolve().parent
STATE_DIR = APP_ROOT / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(dotenv_path=APP_ROOT.parent / ".env", override=False)

@dataclass
class Settings:
    api_key: str
    vector_store_id: Optional[str] = None
    model_attr_extract: str = os.getenv("MODEL_ATTR_EXTRACT", "gpt-5-mini")
    model_report: str = os.getenv("MODEL_REPORT", "gpt-5")
    file_search_max_results: int = int(os.getenv("FILE_SEARCH_MAX_RESULTS", "6"))

def load_settings() -> Settings:
    api_key = os.getenv("OPENAI_API_KEY") or ""
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set. Create .env from .env.example")
    vector_store_id = os.getenv("VECTOR_STORE_ID") or None
    return Settings(api_key=api_key, vector_store_id=vector_store_id)

VSTORE_STATE_FILE = STATE_DIR / "vector_store.json"
META_STATE_FILE = STATE_DIR / "metadata.json"

def load_vector_store_id() -> Optional[str]:
    if VSTORE_STATE_FILE.exists():
        try:
            data = json.loads(VSTORE_STATE_FILE.read_text())
            return data.get("vector_store_id")
        except Exception:
            return None
    return None

def save_vector_store_id(vsid: str) -> None:
    VSTORE_STATE_FILE.write_text(json.dumps({"vector_store_id": vsid}, indent=2))

def load_metadata_index() -> dict:
    if META_STATE_FILE.exists():
        try:
            return json.loads(META_STATE_FILE.read_text())
        except Exception:
            pass
    return {"files": {}, "by_vector_store": {}, "attribute_keys": []}

def save_metadata_index(idx: dict) -> None:
    META_STATE_FILE.write_text(json.dumps(idx, indent=2, ensure_ascii=False))
