# Hospitality Outlook App v2

End-to-end pipeline to:
1) **Initialize** a Vector Store (or create one automatically on first use)  
2) Ingest PDFs → upload to Files API  
3) Extract **scaled attributes** (hospitality + airlines) via structured outputs  
4) Attach to **Vector Store** and persist a local **sidecar metadata index**  
5) Generate a **U.S. Lodging Industry Outlook** using `file_search` + a custom `file_list` tool  
6) Return **JSON** per your schema and render a **Markdown** report

**Models:** `gpt-5-mini` (extraction) · `gpt-5` (report) with `reasoning.effort=high`

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env         # add OPENAI_API_KEY
python -m app.cli init       # creates + saves a Vector Store

# Ingest PDFs from ./input
python -m app.cli ingest-folder --folder .\input


# Generate a report:
#   a) Free text period
python -m app.cli report --period "Q2 2025" --out ./output/outlook_Q2_2025.md
#   b) Structured: quarter/year
python -m app.cli report --quarter Q2 --year 2025 --out ./output/outlook_Q2_2025.md
#   c) Structured: month/year
python -m app.cli report --month 7 --year 2025 --out ./output/outlook_2025-07.md
#   d) No args: defaults to the nearest earnings season for current year
python -m app.cli report
```

The app stores Vector Store id + normalized attributes in `app/state/`.
