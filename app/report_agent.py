from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .openai_client import get_client
from .vectorstore import ensure_vector_store
from .file_list_tool import file_list_handler, tool_schema
from .config import load_settings
from .attributes import load_attribute_config
from .period_utils import compose_period_string

DEV_INSTRUCTIONS = """Developer: You are an expert in hospitality, real estate, and financial analysis.

Begin with a concise checklist (3-7 bullets) of the key sub-tasks you will perform; keep items conceptual, not implementation-level.

Objective:
- Produce a forward-looking U.S. Lodging Industry Outlook report for the specified date or period.
- Deliver a comprehensive assessment of relevant data, prevailing opinions, and sentiment, including how these have evolved over time.
- Provide a professional forecast and predictions, grounded in data analysis and overall industry landscape.
- Incorporate all pertinent information from the provided vector store.

Required Report Sections:
1. Summary
2. Demand Trends (segment by travel type & price tier)
3. Economic & Industry Metrics
4. Sentiment Analysis (include attributed quotes or paraphrased opinions)
5. Regional Segmentation
6. Emerging Trends
7. Historical Comparison
8. Professional Conclusions (evidence, nuance, reasoning)

Workflow:
1. Call `file_list(vector_store_id)` a single time to inventory available data (brands, quarters, regions, segments).
2. Strategize which subsets you need (e.g., Brands 2025 Q2 transcripts, Reits 2025 2Q transcript, region commentary). 
3. Use multiple targeted `file_search` calls, applying metadata filters from `file_list` as appropriate.
4. Complete each report section, building a forward-focused outlook that covers:
   - Demand trends (leisure, group, business, convention)
   - Price/chain scale performance (luxury, premium, economy)
   - Key performance indicators (e.g., RevPAR, ADR, OCC, GOP) and any macroeconomic links
   - Regional variations
   - Notable emerging themes
   - Attributed sentiment (quotes/paraphrases with source)
   - Clear comparison to prior periods
5. Cite sources inline using file title and fiscal quarter or brand. Avoid duplicate quotes.

Before any significant tool call, state in one line its purpose and the minimal required inputs.
After each tool call or section completion, validate the result in 1-2 lines and either proceed or self-correct if validation fails.

Retrieval Guidelines:
- Prioritize retrieving and analyzing data that matches the user's specified date or time window as closely as possible. This is so you can compare things like the FY outlook as of Q1 to the FY outlook as of Q2. 
- If directly matching data is insufficient, systematically expand the data search by including additional brands or document types, and always clearly indicate, and qualify the exact timeframe associated with each data point or source. 
- For major report sections, conduct dedicated searches as necessary. Combine or adapt queries to ensure thorough and relevant dataset coverage.

Output Format:
Return the report as a structured JSON object using the following schema. Preserve the order and data types specified. Use clear narrative text (unless arrays are indicated for lists). For missing data, set fields to null or an empty structure and note this in the related section.

```json
{
  "summary": "<narrative summary>",
  "demand_trends": {
    "leisure": "<narrative>",
    "group": "<narrative>",
    "business": "<narrative>",
    "convention": "<narrative>",
    "by_price_scale": {
      "luxury": "<narrative>",
      "premium": "<narrative>",
      "economy": "<narrative>"
    }
  },
  "economic_and_industry_metrics": [
    {
      "metric": "<example: RevPAR>",
      "value": <number|null>,
      "trend_vs_prior": "<comparison>",
      "source": "<file title + quarter or brand>",
      "notes": "<optional notes>"
    }
  ],
  "sentiment_analysis": [
    {
      "quote_or_paraphrase": "<text>",
      "attribution": {
        "speaker": "<name/role, if available>",
        "source": "<file title + quarter or brand>"
      }
    }
  ],
  "regional_segmentation": [
    {
      "region": "<region>",
      "trend": "<narrative>",
      "sources": ["<file title + quarter or brand>"]
    }
  ],
  "emerging_trends": [
    "<narrative>"
  ],
  "historical_comparison": {
    "period_compared": "<e.g., 2023-Q4 vs 2024-Q2>",
    "key_differences": ["<narrative>"]
  },
  "conclusions": "<professional analysis and outlook>"
}
```

- For sentiment, use objects with quote/paraphrase and attribution as shown.
- Only use tabular formatting within arrays if justified by the metrics; otherwise, keep to objects/arrays per the schema.
- If any metric or data subset is unavailable, use null or an empty array/object and acknowledge missing data in the commentary.
"""

REPORT_USER_TEMPLATE = """You are generating a U.S. Lodging Industry Outlook for period: {period}.
Attribute keys available (for filtering): {attr_keys}.
Enum guidance (partial): {attr_enums}.
Use file_search across vector_store_id={vsid}. Return ONLY the JSON object per the schema.
"""

def _gather_outputs(resp) -> List[dict]:
    return getattr(resp, "output", []) or []

def _tool_loop(input_messages: List[dict], vector_store_id: str) -> str:
    client = get_client()
    settings = load_settings()
    tools = [
        {
            "type": "file_search",
            "vector_store_ids": [vector_store_id],
            "max_num_results": settings.file_search_max_results,
        },
        tool_schema(),
    ]
    resp = client.responses.create(
        model=settings.model_report,
        reasoning={"effort": "high"},
        input=input_messages,
        tools=tools,
        include=["file_search_call.results"],
    )

    input_accum = list(input_messages) + _gather_outputs(resp)

    while True:
        tool_calls = [o for o in _gather_outputs(resp) if getattr(o, "type", None) == "function_call"]
        if not tool_calls:
            return getattr(resp, "output_text", "")

        for call in tool_calls:
            name = getattr(call, "name", "")
            if name != "file_list":
                tool_output = json.dumps({"error": f"Unknown tool {name}"})
            else:
                try:
                    args = json.loads(call.arguments or "{}")
                except Exception:
                    args = {}
                result = file_list_handler(args.get("vector_store_id") or vector_store_id)
                tool_output = json.dumps(result)

            input_accum.append({
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": tool_output,
            })

        resp = client.responses.create(
            model=settings.model_report,
            reasoning={"effort": "high"},
            instructions="Continue. Use file_search as needed. Return ONLY the JSON object per schema.",
            tools=tools,
            input=input_accum,
            include=["file_search_call.results"],
        )
        input_accum += _gather_outputs(resp)

def generate_report(period: str | None, quarter: str | None = None, month: int | None = None, year: int | None = None) -> dict:
    vsid = ensure_vector_store()
    period_text = period or compose_period_string(quarter, month, year)
    cfg = load_attribute_config()
    messages = [
        {"role": "system", "content": DEV_INSTRUCTIONS},
        {"role": "user", "content": REPORT_USER_TEMPLATE.format(period=period_text, attr_keys=list(cfg.get("attributes", [])), attr_enums=cfg.get("enums", {}), vsid=vsid)},
    ]
    json_text = _tool_loop(messages, vsid).strip()
    try:
        data = json.loads(json_text)
    except Exception:
        data = {"summary": json_text, "demand_trends": {"leisure": None,"group": None,"business": None,"convention": None,"by_price_scale": {"luxury": None,"premium": None,"economy": None}}, "economic_and_industry_metrics": [], "sentiment_analysis": [], "regional_segmentation": [], "emerging_trends": [], "historical_comparison": {"period_compared": None, "key_differences": []}, "conclusions": None}
    return data

def render_markdown(report: dict, period: str) -> str:
    def _n(x): return x if x else "_No data_"
    dt = report.get("demand_trends", {})
    bps = dt.get("by_price_scale", {}) if isinstance(dt, dict) else {}

    lines = []
    lines.append(f"# U.S. Lodging Industry Outlook — {period}\n")
    lines.append("## Summary\n")
    lines.append(_n(report.get("summary")) + "\n")

    lines.append("## Demand Trends\n")
    lines.append(f"- **Leisure:** { _n(dt.get('leisure')) }")
    lines.append(f"- **Group:** { _n(dt.get('group')) }")
    lines.append(f"- **Business:** { _n(dt.get('business')) }")
    lines.append(f"- **Convention:** { _n(dt.get('convention')) }\n")
    lines.append("**By Price Scale**")
    lines.append(f"- Luxury: { _n(bps.get('luxury')) }")
    lines.append(f"- Premium: { _n(bps.get('premium')) }")
    lines.append(f"- Economy: { _n(bps.get('economy')) }\n")

    lines.append("## Economic & Industry Metrics\n")
    metrics = report.get("economic_and_industry_metrics", []) or []
    if metrics:
        lines.append("| Metric | Value | Trend vs Prior | Source | Notes |")
        lines.append("|---|---:|---|---|---|")
        for m in metrics:
            lines.append(f"| {m.get('metric','')} | {m.get('value','')} | {m.get('trend_vs_prior','')} | {m.get('source','')} | {m.get('notes','')} |")
        lines.append("")
    else:
        lines.append("_No metrics_\n")

    lines.append("## Sentiment Analysis\n")
    senti = report.get("sentiment_analysis", []) or []
    if senti:
        for s in senti:
            q = s.get("quote_or_paraphrase","")
            at = s.get("attribution",{}) or {}
            lines.append(f"- “{q}” — {at.get('speaker') or 'Unknown'}, *{at.get('source') or ''}*")
        lines.append("")
    else:
        lines.append("_No sentiment items_\n")

    lines.append("## Regional Segmentation\n")
    regions = report.get("regional_segmentation", []) or []
    if regions:
        for r in regions:
            lines.append(f"- **{r.get('region','')}** — {r.get('trend','')} (Sources: {', '.join(r.get('sources') or [])})")
        lines.append("")
    else:
        lines.append("_No regional items_\n")

    lines.append("## Emerging Trends\n")
    trends = report.get("emerging_trends", []) or []
    if trends:
        for t in trends:
            lines.append(f"- {t}")
        lines.append("")
    else:
        lines.append("_No emerging trends_\n")

    lines.append("## Historical Comparison\n")
    hc = report.get("historical_comparison", {}) or {}
    lines.append(f"- **Period Compared:** { _n(hc.get('period_compared')) }")
    diffs = hc.get("key_differences", []) or []
    if diffs:
        for d in diffs:
            lines.append(f"- {d}")
        lines.append("")
    else:
        lines.append("_No key differences_\n")

    lines.append("## Conclusions\n")
    lines.append(_n(report.get("conclusions")) + "\n")

    return "\n".join(lines)
