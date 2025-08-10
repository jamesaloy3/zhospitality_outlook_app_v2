from __future__ import annotations

import json
from .config import load_metadata_index, load_vector_store_id, load_settings

def file_list_handler(vector_store_id: str) -> dict:
    idx = load_metadata_index()
    vsid = vector_store_id or load_vector_store_id() or load_settings().vector_store_id

    files = []
    for fid, rec in idx.get("files", {}).items():
        if rec.get("vector_store_id") != vsid:
            continue
        attrs = rec.get("attributes", {}) or {}
        title = attrs.get("title") or rec.get("source_path", "").split("/")[-1]
        files.append({
            "id": fid,
            "title": title,
            "attributes": attrs,
            "status": rec.get("status"),
        })
    return {
        "vector_store_id": vsid,
        "available_attributes": idx.get("attribute_keys") or [],
        "files": files,
    }

def tool_schema() -> dict:
    return {
        "type": "function",
        "name": "file_list",
        "description": "List files in a vector store with normalized attributes from the local metadata index.",
        "parameters": {
            "type": "object",
            "properties": {
                "vector_store_id": {"type": "string", "description": "Vector store id to list. If empty, use default."}
            },
            "required": ["vector_store_id"],
            "additionalProperties": False
        },
        "strict": True
    }
