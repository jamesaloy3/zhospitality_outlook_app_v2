from __future__ import annotations

from pathlib import Path
from typing import List
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel

from .files_api import upload_file
from .attribute_extractor import extract_attributes_from_file
from .vector_upload import attach_file_to_vector_store
from .openai_client import get_client
from .vectorstore import ensure_vector_store
from .config import load_metadata_index, save_metadata_index

console = Console()

def find_pdfs(folder: str) -> List[Path]:
    folder_path = Path(folder)
    return sorted([p for p in folder_path.rglob("*.pdf") if p.is_file()])

def ingest_folder(folder: str) -> None:
    pdfs = find_pdfs(folder)
    if not pdfs:
        console.print(f"[yellow]No PDFs found under {folder}[/]")
        return

    table = Table(title="PDF Ingest → Attributes → Vector Store", expand=True)
    table.add_column("#", justify="right")
    table.add_column("File")
    table.add_column("Upload")
    table.add_column("Attributes")
    table.add_column("VectorStore")
    table.add_column("Status")

    rows = []
    for i, path in enumerate(pdfs, start=1):
        rows.append([str(i), path.name, "⏳", "⏳", "⏳", ""])

    with Live(table, refresh_per_second=8):
        for i, path in enumerate(pdfs, start=1):
            # Upload
            try:
                file_id = upload_file(str(path))
                rows[i-1][2] = f"✅ {file_id[:12]}…"
            except Exception as e:
                rows[i-1][2] = f"❌ {e}"
                continue

            # Extract attributes
            try:
                attrs = extract_attributes_from_file(file_id, filename_hint=path.name)
                rows[i-1][3] = f"✅"
            except Exception as e:
                rows[i-1][3] = f"❌ {e}"
                attrs = None

            # Attach to vector store
            try:
                attr_dict = attrs.model_dump() if attrs else {}
                attach_res = attach_file_to_vector_store(file_id, attr_dict, str(path))
                rows[i-1][4] = f"✅ {attach_res['vector_store_id'][:12]}…"
                rows[i-1][5] = attach_res["status"]
            except Exception as e:
                rows[i-1][4] = f"❌"
                rows[i-1][5] = f"{e}"

            table.rows = []
            for r in rows:
                table.add_row(*r)

    console.print(Panel.fit("[green]Done.[/] You can run [bold]python -m app.cli reconcile[/bold] later to refresh statuses."))

def reconcile_status() -> None:
    """
    Re-list vector store files and refresh local processing status in the sidecar metadata.
    Safe to run anytime.
    """
    vsid = ensure_vector_store()
    client = get_client()
    try:
        listing = client.vector_stores.files.list(vector_store_id=vsid)
    except Exception as e:
        console.print(f"[red]Failed to list vector store files:[/] {e}")
        return

    idx = load_metadata_index()
    updated = 0
    for f in listing.data:
        try:
            item = client.vector_stores.files.retrieve(vector_store_id=vsid, file_id=f.id)
            if f.id in idx.get("files", {}):
                idx["files"][f.id]["status"] = getattr(item, "status", idx["files"][f.id].get("status"))
                updated += 1
        except Exception:
            pass
    save_metadata_index(idx)
    console.print(f"[green]Reconciled {updated} files for vector_store {vsid}.[/]")
