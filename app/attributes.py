from __future__ import annotations

"""Attribute schema definitions and helpers.

This module loads the attribute configuration from ``attributes_config.json`` and
builds a ``DocAttributes`` Pydantic model dynamically.  Each attribute is stored
as a string but the model accepts numbers or lists of strings from upstream
parsers and normalises them to strings where appropriate.

The ``make_loose_json_schema_for_values`` helper produces a relaxed JSON schema
used by the extraction pipeline.  It allows each property to be either a
string, number, or an array of strings, which mirrors the guidance provided to
the language model during attribute extraction.
"""

from pathlib import Path
import json
from typing import Any

from pydantic import BaseModel, Field, field_validator, create_model


# ---------------------------------------------------------------------------
# Configuration loading
# ---------------------------------------------------------------------------

ATTR_CFG_PATH = Path(__file__).resolve().parent / "attributes_config.json"


def load_attribute_config() -> dict:
    """Load the JSON configuration describing attribute fields."""
    return json.loads(ATTR_CFG_PATH.read_text())


_cfg = load_attribute_config()


# ---------------------------------------------------------------------------
# DocAttributes model
# ---------------------------------------------------------------------------

AttributeValue = str | int | float | list[str] | None


class _BaseAttributes(BaseModel):
    """Base model providing normalisation for all attribute values."""

    @field_validator("*", mode="before")
    @classmethod
    def _normalize(cls, v: Any) -> Any:
        if v is None:
            return ""
        if isinstance(v, (int, float)):
            return str(v)
        if isinstance(v, list):
            return [str(x) for x in v]
        return v

    class Config:
        extra = "ignore"


field_definitions = {
    name: (AttributeValue, Field(default="")) for name in (_cfg.get("attributes") or [])
}


# Dynamically construct the model so that changes in the config file are
# automatically reflected here without manual code updates.
DocAttributes = create_model(  # type: ignore[misc]
    "DocAttributes", __base__=_BaseAttributes, **field_definitions
)


# ---------------------------------------------------------------------------
# Schema helper
# ---------------------------------------------------------------------------

def make_loose_json_schema_for_values(model_cls: type[BaseModel]) -> dict:
    """Return a relaxed JSON schema for ``model_cls`` values.

    Each property is permitted to be a string, a number, or an array of strings
    so that the extraction step can emit whichever type best fits the source
    data.  All properties remain optional and unknown properties are disallowed.
    """

    schema = model_cls.model_json_schema()
    properties = schema.get("properties", {})
    loose_type = {
        "anyOf": [
            {"type": "string"},
            {"type": "number"},
            {"type": "array", "items": {"type": "string"}},
        ]
    }
    for prop in properties.values():
        prop.clear()
        prop.update(loose_type)

    schema["properties"] = properties
    schema["additionalProperties"] = False
    return schema


__all__ = [
    "DocAttributes",
    "load_attribute_config",
    "make_loose_json_schema_for_values",
]

