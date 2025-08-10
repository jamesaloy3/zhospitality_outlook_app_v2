from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
from .openai_client import get_client
from .vectorstore import ensure_vector_store
from .config import load_metadata_index, save_metadata_index

def attach_file_to_vector_store(file_id: str, attrs: Dict[str, Any], source_path: str) -> dict:
    """Attach the file to vector store and persist sidecar metadata locally."""
    client = get_client()
    vsid = ensure_vector_store()

    res = client.vector_stores.files.create_and_poll(
        vector_store_id=vsid,
        file_id=file_id,
    )

    idx = load_metadata_index()
    file_record = {
        "vector_store_id": vsid,
        "file_id": file_id,
        "attributes": attrs,
        "source_path": str(Path(source_path).resolve()),
        "status": res.status,
        "created_at": res.created_at,
    }
    idx.setdefault("files", {})[file_id] = file_record
    idx.setdefault("by_vector_store", {}).setdefault(vsid, [])
    if file_id not in idx["by_vector_store"][vsid]:
        idx["by_vector_store"][vsid].append(file_id)
    # Track attribute keys for the tool
    keys = set(idx.get("attribute_keys") or [])
    keys.update(list(attrs.keys()))
    idx["attribute_keys"] = sorted(keys)
    save_metadata_index(idx)

    return {"status": res.status, "vector_store_id": vsid, "file_id": file_id}
