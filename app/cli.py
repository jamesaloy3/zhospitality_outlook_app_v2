from __future__ import annotations

import json
from pathlib import Path
import typer
from rich.console import Console

from .bulk_ingest import ingest_folder, reconcile_status
from .files_api import upload_file
from .attribute_extractor import extract_attributes_from_file
from .vector_upload import attach_file_to_vector_store
from .report_agent import generate_report, render_markdown
from .vectorstore import ensure_vector_store
from .period_utils import compose_period_string
from .inspect import list_files as _list_files, show_attributes as _show_attributes, export_attributes as _export_attributes
from .config import load_metadata_index, save_metadata_index

app = typer.Typer(help="Hospitality Outlook: ingest PDFs, extract attributes, upload to Vector Store, generate reports.")
console = Console()

@app.command()
def init():
    vsid = ensure_vector_store()
    console.print(f"[green]Vector Store ready:[/] {vsid}")

@app.command()
def ingest(file: str = typer.Argument(..., help="Path to a single PDF file to ingest.")):
    ensure_vector_store()
    fid = upload_file(file)
    attrs = extract_attributes_from_file(fid, filename_hint=Path(file).name)
    attach_file_to_vector_store(fid, attrs.model_dump(), file)
    console.print(f"[green]Ingested[/] {file} → file_id={fid}")

@app.command("ingest-folder")
def ingest_folder_cmd(
    folder: str = typer.Argument("./input", help="Folder to scan recursively for PDFs (default: ./input)")
):
    ensure_vector_store()
    ingest_folder(folder)

@app.command()
def reconcile():
    reconcile_status()

@app.command("list-files")
def list_files():
    _list_files()

@app.command("show-attributes")
def show_attributes(key: str = typer.Argument(..., help="file_id (or prefix) or part of the title/filename")):
    _show_attributes(key)

@app.command("export-attributes")
def export_attributes(out_dir: str = typer.Option("./output/attributes", help="Directory to write per-file attribute JSONs")):
    _export_attributes(out_dir)

@app.command("retry-extraction")
def retry_extraction(limit: int = typer.Option(0, help="Limit number of files to retry (0 = all).")):
    """
    Re-run attribute extraction for files that have missing/blank attributes in the local index.
    """
    ensure_vector_store()
    idx = load_metadata_index()
    files = idx.get("files", {})
    count = 0
    for fid, rec in files.items():
        attrs = rec.get("attributes", {}) or {}
        needs = (not attrs) or all((not (attrs.get(k) or "").strip()) for k in (attrs.keys() or []))
        if needs:
            try:
                new_attrs = extract_attributes_from_file(fid, filename_hint=Path(rec.get("source_path","")).name if rec.get("source_path") else None)
                idx["files"][fid]["attributes"] = new_attrs.model_dump()
                count += 1
                console.print(f"[green]Re-extracted[/] {fid[:12]}…")
                if limit and count >= limit:
                    break
            except Exception as e:
                console.print(f"[red]Retry failed for[/] {fid[:12]}…: {e}")
    save_metadata_index(idx)
    console.print(f"[green]Completed retries.[/] Updated: {count} file(s).")

@app.command()
def report(
    period: str = typer.Option(None, help="Free-form period text (e.g., 'Q2 2025' or '2025-07')."),
    quarter: str = typer.Option(None, help="Quarter like Q1,Q2,Q3,Q4."),
    month: int = typer.Option(None, help="Month as 1-12 when using monthly reporting."),
    year: int = typer.Option(None, help="Year like 2025."),
    out: str = typer.Option("", help="Output filename (.md recommended). A .json with same stem is also written.")
):
    ensure_vector_store()
    display_period = compose_period_string(quarter, month, year) if not period else period
    data = generate_report(period=period, quarter=quarter, month=month, year=year)
    out_path = Path(out) if out else Path(f"./output/report_{display_period.replace(' ','_').replace(':','-')}.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_path = out_path.with_suffix(".json")
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    md = render_markdown(data, display_period)
    out_path.write_text(md, encoding="utf-8")

    console.print(f"[green]Saved:[/] {out_path}  and  {json_path}")

@app.command()
def reindex():
    console.print("[yellow]Not implemented in this starter.[/] Use `reconcile`, `retry-extraction`, or re-ingest.")
    
if __name__ == "__main__":
    app()
