from __future__ import annotations

import json
from typing import Optional, Dict, Any, List
from pathlib import Path
from pydantic import BaseModel
from .openai_client import get_client
from .attributes import DocAttributes, load_attribute_config, make_loose_json_schema_for_values


class InputText(BaseModel):
    type: str = "input_text"
    text: str


class InputFile(BaseModel):
    type: str = "input_file"
    file_id: str


class UserContent(BaseModel):
    content: List[InputText | InputFile]


class SystemMessage(BaseModel):
    role: str = "system"
    content: str


class UserMessage(BaseModel):
    role: str = "user"
    content: List[InputText | InputFile]


SYSTEM_PROMPT = (
    "You are extracting structured attributes from the attached document.\n"
    "Output ONLY a JSON object that exactly matches the provided JSON schema.\n"
    "Each field may be a string, a number, or an array of strings.\n"
    "If a value is unknown, output an empty string \"\" (or an empty array [] where appropriate).\n"
    "Do not include any keys that are not in the schema. Do not include explanations.\n"
)


def _build_json_schema() -> Dict[str, Any]:
    # Start from the Pydantic model and relax types to string|number|array<string>
    schema = make_loose_json_schema_for_values(DocAttributes)

    # Strengthen enum fields based on the attributes config: accept either a single enum value
    # or an array of enum values. Also allow empty string for unknown (per instructions).
    cfg = load_attribute_config()
    enum_map = (cfg.get("enums") or {})
    properties: Dict[str, Any] = schema.get("properties", {})

    for field_name, allowed_values in enum_map.items():
        if field_name in properties:
            properties[field_name] = {
                "anyOf": [
                    {"type": "string", "enum": list(allowed_values) + [""]},
                    {"type": "array", "items": {"type": "string", "enum": list(allowed_values)}}
                ]
            }

    schema["properties"] = properties

    # Name field required by the Responses API for strict JSON schema
    return {
        "name": "DocAttributes",
        "schema": schema,
        "strict": True
    }


def extract_attributes_from_file(file_id: str, filename_hint: Optional[str] = None) -> DocAttributes:
    """
    Extract structured attributes from a file using the DocAttributes schema.

    Args:
        file_id: The OpenAI file ID to process
        filename_hint: Optional filename for title backfill

    Returns:
        DocAttributes object with extracted attributes
    """
    client = get_client()
    cfg = load_attribute_config()

    # Build enum guidance text to gently steer the model (constraints are not enforced in schema)
    enum_guidance = ""
    if cfg.get("enums"):
        enum_guidance = "\n\nEnum hints (use only if present in the document):\n"
        for field, values in cfg["enums"].items():
            enum_guidance += f"- {field}: {', '.join(values)}\n"

    # Messages: fully typed content style for Responses API
    schema_wrapper = _build_json_schema()
    schema_text = json.dumps(schema_wrapper.get("schema", {}), indent=2)

    input_text = InputText(
        text=(
            "Extract attributes for this document according to the attached JSON schema. "
            "Return a single JSON object. Use only the allowed enum values where provided.\n"
        )
    )
    schema_as_text = InputText(text=f"JSON Schema:\n\n{schema_text}")
    input_file = InputFile(file_id=file_id)

    system_message = SystemMessage(content=SYSTEM_PROMPT + enum_guidance)
    user_message = UserMessage(content=[input_text, schema_as_text, input_file])

    api_payload = [system_message.model_dump(), user_message.model_dump()]

    # Strict guidance via schema provided in-text; avoid unsupported response_format param
    response = client.responses.create(
        model="gpt-5-mini",
        reasoning={"effort": "high"},
        input=api_payload
    )

    # Extract and parse the response JSON safely
    data: Dict[str, Any] = {}
    # Prefer unified accessor when available
    raw_text = getattr(response, "output_text", None)

    def try_parse(text: Optional[str]) -> Optional[Dict[str, Any]]:
        if not text:
            return None
        try:
            return json.loads(text)
        except Exception:
            return None

    parsed = try_parse(raw_text)
    if parsed is None:
        # Fallback: walk structured output
        for item in getattr(response, "output", []) or []:
            if getattr(item, "type", None) == "message":
                for piece in getattr(item, "content", []) or []:
                    if getattr(piece, "type", None) == "output_text":
                        parsed = try_parse(getattr(piece, "text", ""))
                        if parsed is not None:
                            break
            if parsed is not None:
                break

    data = parsed or {}

    # Ensure all configured attributes exist with defaults
    for k in (cfg.get("attributes") or []):
        if k not in data or data[k] is None:
            data[k] = ""

    # Backfill title from filename if still blank
    if (not (str(data.get("title") or "").strip())) and filename_hint:
        data["title"] = Path(filename_hint).stem.replace("_", " ").strip()

    # Validate/normalize with Pydantic
    return DocAttributes.model_validate(data)
