from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from rich.console import Console
from rich.table import Table

from .config import load_metadata_index

console = Console()

def list_files() -> None:
    idx = load_metadata_index()
    files = idx.get("files", {})
    if not files:
        console.print("[yellow]No files recorded in state yet. Try ingesting first.[/]")
        return
    table = Table(title="Vector Store Files (from local index)", expand=True)
    table.add_column("File ID", overflow="fold")
    table.add_column("Title")
    table.add_column("Status")
    table.add_column("Company/Carrier")
    table.add_column("Data Type")
    table.add_column("Period")
    table.add_column("Year")
    table.add_column("FQ")

    for fid, rec in files.items():
        attrs = rec.get("attributes", {}) or {}
        table.add_row(
            fid,
            attrs.get("title") or Path(rec.get("source_path","")).name,
            rec.get("status",""),
            attrs.get("company","") or attrs.get("carrier",""),
            attrs.get("data_type",""),
            attrs.get("period",""),
            attrs.get("year",""),
            attrs.get("fiscal_quarter","")
        )
    console.print(table)

def _find_file_record(key: str) -> Optional[Dict[str, Any]]:
    idx = load_metadata_index()
    files = idx.get("files", {})
    # exact or startswith on file_id
    if key in files:
        return files[key]
    for fid, rec in files.items():
        if fid.startswith(key):
            return rec
    # title contains
    for fid, rec in files.items():
        title = (rec.get("attributes", {}) or {}).get("title") or Path(rec.get("source_path","")).name
        if key.lower() in (title or "").lower():
            return rec
    return None

def show_attributes(key: str) -> None:
    rec = _find_file_record(key)
    if not rec:
        console.print(f("[yellow]No file matched:[/] {key}"))
        return
    attrs = rec.get("attributes", {}) or {}
    pretty = json.dumps(attrs, indent=2, ensure_ascii=False)
    console.rule(f"Attributes for {key}")
    console.print(pretty)

def export_attributes(out_dir: str = "./output/attributes") -> None:
    idx = load_metadata_index()
    files = idx.get("files", {})
    if not files:
        console.print("[yellow]No files recorded in state yet.[/]")
        return
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    count = 0
    for fid, rec in files.items():
        attrs = rec.get("attributes", {}) or {}
        (out / f"{fid}.json").write_text(json.dumps(attrs, indent=2, ensure_ascii=False), encoding="utf-8")
        count += 1
    console.print(f"[green]Exported[/] {count} attribute JSON files to {out.resolve()}")
