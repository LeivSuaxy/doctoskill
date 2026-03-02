"""Resolve ``$ref`` pointers and generate example payloads from schemas."""

from __future__ import annotations

import json
from typing import Any

from .models import SchemaDefinition, SchemaProperty
from .utils import ref_name


# ---------------------------------------------------------------------------
# Schema resolution
# ---------------------------------------------------------------------------

def resolve_ref(ref: str, spec: dict[str, Any]) -> dict[str, Any]:
    """Follow a ``$ref`` pointer like ``#/components/schemas/Pet`` and return
    the resolved JSON object.  Returns an empty dict if the path is invalid.
    """
    if not ref or not ref.startswith("#/"):
        return {}
    parts = ref.lstrip("#/").split("/")
    node: Any = spec
    for part in parts:
        if isinstance(node, dict):
            node = node.get(part, {})
        else:
            return {}
    return node if isinstance(node, dict) else {}


def resolve_schema(schema: dict[str, Any], spec: dict[str, Any],
                   *, _depth: int = 0) -> dict[str, Any]:
    """Recursively resolve a schema, following ``$ref`` pointers up to a
    reasonable depth to avoid infinite loops.
    """
    if _depth > 10:
        return schema
    if "$ref" in schema:
        return resolve_schema(resolve_ref(schema["$ref"], spec), spec,
                              _depth=_depth + 1)
    return schema


# ---------------------------------------------------------------------------
# Example generation
# ---------------------------------------------------------------------------

_TYPE_DEFAULTS: dict[str, Any] = {
    "string": "string",
    "integer": 0,
    "number": 0.0,
    "boolean": False,
}

_FORMAT_DEFAULTS: dict[str, Any] = {
    "date-time": "2024-01-15T10:30:00Z",
    "date": "2024-01-15",
    "email": "user@example.com",
    "uri": "https://example.com",
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "int32": 0,
    "int64": 0,
    "float": 0.0,
    "double": 0.0,
    "binary": "<binary>",
    "byte": "dGVzdA==",
}


def generate_example(schema: dict[str, Any], spec: dict[str, Any],
                     *, _depth: int = 0) -> Any:
    """Generate a representative example payload from *schema*.

    Uses ``example`` values when available, otherwise falls back to
    type-appropriate defaults.  Resolves ``$ref`` transparently.
    """
    if _depth > 8:
        return "..."

    schema = resolve_schema(schema, spec, _depth=_depth)

    # Direct example on the schema itself
    if "example" in schema:
        return schema["example"]

    schema_type = schema.get("type", "object")

    if schema_type == "array":
        items = schema.get("items", {})
        return [generate_example(items, spec, _depth=_depth + 1)]

    if schema_type == "object" or "properties" in schema:
        result: dict[str, Any] = {}
        for prop_name, prop_schema in schema.get("properties", {}).items():
            result[prop_name] = generate_example(prop_schema, spec,
                                                 _depth=_depth + 1)
        return result

    # Enum
    if "enum" in schema:
        return schema["enum"][0]

    # Format-specific defaults
    fmt = schema.get("format", "")
    if fmt in _FORMAT_DEFAULTS:
        return _FORMAT_DEFAULTS[fmt]

    return _TYPE_DEFAULTS.get(schema_type, "string")


def example_to_json(schema: dict[str, Any], spec: dict[str, Any]) -> str:
    """Return a pretty-printed JSON string of an example payload."""
    return json.dumps(generate_example(schema, spec), indent=2,
                      ensure_ascii=False)


# ---------------------------------------------------------------------------
# Schema → SchemaDefinition model
# ---------------------------------------------------------------------------

def parse_schema_definition(name: str, raw: dict[str, Any],
                            spec: dict[str, Any]) -> SchemaDefinition:
    """Convert a raw component schema dict into a `SchemaDefinition`."""
    resolved = resolve_schema(raw, spec)
    required_fields = resolved.get("required", [])

    properties: list[SchemaProperty] = []
    for prop_name, prop_data in resolved.get("properties", {}).items():
        prop_resolved = resolve_schema(prop_data, spec)

        prop_ref: str | None = None
        items_ref: str | None = None
        items_type: str | None = None

        if "$ref" in prop_data:
            prop_ref = ref_name(prop_data["$ref"])
        if prop_resolved.get("type") == "array":
            items = prop_resolved.get("items", {})
            if "$ref" in items:
                items_ref = ref_name(items["$ref"])
            else:
                items_type = items.get("type", "string")

        properties.append(SchemaProperty(
            name=prop_name,
            type=prop_resolved.get("type", "object"),
            format=prop_resolved.get("format"),
            description=prop_resolved.get("description", ""),
            required=prop_name in required_fields,
            enum=prop_resolved.get("enum", []),
            example=str(prop_resolved["example"]) if "example" in prop_resolved else None,
            ref=prop_ref,
            items_ref=items_ref,
            items_type=items_type,
        ))

    return SchemaDefinition(
        name=name,
        type=resolved.get("type", "object"),
        description=resolved.get("description", ""),
        properties=properties,
        required_fields=required_fields,
    )
