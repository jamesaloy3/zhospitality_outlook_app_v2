from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import Optional
import json
from pathlib import Path

ATTR_CFG_PATH = Path(__file__).resolve().parent / "attributes_config.json"

def load_attribute_config() -> dict:
    return json.loads(ATTR_CFG_PATH.read_text())

_cfg = load_attribute_config()

class DocAttributes(BaseModel):
    # All fields are strings. Use "" when unknown. We normalize to keep consistent formatting.
    {
  "version": 2,
  "notes": "Scaled attribute set: hospitality + airlines. Leave blanks if unknown; all values are strings.",
  "attributes": [
    "title" : str,
    "company",
    "brand_family",
    "industry",
    "asset_class" : list[ "hospitality",
      "airline",
      "travel",
      "real_estate"],
    "company_type" : list[ "brand"  ,
      "reit",
      "research",
      "real_estate",
      "capital_markets",
      "airline"
    ],
    "data_type",
    "doc_date",
    "period",
    "year",
    "fiscal_quarter",
    "month",
    "country",
    "region",
    "travel_types",
    "price_scales",
    "carrier",
    "iata_code",
    "icao_code",
    "alliance",
    "network_focus",
    "language",
    "source_url"
  ],


    "company_type": [
      "brand",
      "reit",
      "research",
      "real_estate",
      "capital_markets",
      "airline"
    ],
    "data_type": [
      "earnings_call",
      "10q",
      "market_research",
      "commentary",
      "economic_research",
      "traffic_report",
      "investor_presentation"
    ],
    "period": [
      "month",
      "quarter",
      "annual"
    ],
    "travel_types": [
      "leisure",
      "group",
      "business",
      "convention"
    ],
    "price_scales": [
      "luxury",
      "upper_upscale",
      "upscale",
      "midscale",
      "economy",
      "premium"
    ],
    "alliance": [
      "oneworld",
      "star",
      "skyteam",
      "none"
    ],
    "network_focus": [
      "domestic",
      "international",
      "transatlantic",
      "transpacific",
      "latin_america"
    ]
  }
}

   