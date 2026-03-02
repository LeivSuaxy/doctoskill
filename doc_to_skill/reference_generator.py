"""Generate reference markdown files for each API module and the schemas."""

from __future__ import annotations

import json
from typing import Any

from .models import (
    APISpec,
    EndpointInfo,
    ModuleInfo,
    ParameterInfo,
    SchemaDefinition,
)
from .schema_resolver import example_to_json, resolve_ref
from .utils import ref_name, sanitize_filename


# ---------------------------------------------------------------------------
# Schema reference (references/schemas.md)
# ---------------------------------------------------------------------------

def generate_schemas_reference(api: APISpec, spec_raw: dict[str, Any]) -> str:
    """Generate the ``references/schemas.md`` file that documents every
    component schema with its properties, types, constraints, and an
    example payload.
    """
    lines = [
        "# Data Models\n",
        f"[Back to SKILL.md](../SKILL.md)\n",
        "This document contains all data models (schemas) used by the "
        f"{api.title} API.\n",
        "## Table of contents\n",
    ]

    for schema in api.schemas:
        anchor = schema.name.lower().replace(" ", "-")
        lines.append(f"- [{schema.name}](#{anchor})")
    lines.append("")

    for schema in api.schemas:
        lines.append(f"## {schema.name}\n")

        if schema.description:
            lines.append(f"{schema.description}\n")

        if schema.properties:
            lines.append("| Property | Type | Required | Description | Example |")
            lines.append("|----------|------|----------|-------------|---------|")

            for prop in schema.properties:
                ptype = _format_prop_type(prop)
                req = "Yes" if prop.required else "No"
                desc = prop.description or "—"
                example = f"`{prop.example}`" if prop.example else "—"
                lines.append(f"| `{prop.name}` | {ptype} | {req} | {desc} | {example} |")

            lines.append("")

        # Generate example payload
        raw_schema = (
            spec_raw
            .get("components", {})
            .get("schemas", {})
            .get(schema.name, {})
        )
        if raw_schema:
            lines.append("**Example payload:**\n")
            lines.append("```json")
            lines.append(example_to_json(raw_schema, spec_raw))
            lines.append("```\n")

        lines.append("---\n")

    return "\n".join(lines)


def _format_prop_type(prop) -> str:
    """Format a property type for display, including refs and array items."""
    if prop.ref:
        return f"[{prop.ref}](#{prop.ref.lower()})"
    if prop.type == "array":
        if prop.items_ref:
            return f"array\\<[{prop.items_ref}](#{prop.items_ref.lower()})\\>"
        return f"array\\<{prop.items_type or 'string'}\\>"
    base = prop.type
    if prop.format:
        base += f" ({prop.format})"
    if prop.enum:
        base += f" enum: {prop.enum}"
    return base


# ---------------------------------------------------------------------------
# Module reference (references/<module>.md)
# ---------------------------------------------------------------------------

def generate_module_reference(module: ModuleInfo, api: APISpec,
                              spec_raw: dict[str, Any]) -> str:
    """Generate a ``references/<module>.md`` file with full endpoint docs."""

    lines = [
        f"# {module.name}\n",
        f"[Back to SKILL.md](../SKILL.md)\n",
    ]

    if module.description:
        lines.append(f"{module.description}\n")

    if module.external_docs_url:
        lines.append(f"More info: [{module.external_docs_url}]({module.external_docs_url})\n")

    lines.append(f"## Endpoints ({len(module.endpoints)})\n")

    # Mini TOC
    for ep in module.endpoints:
        anchor = _endpoint_anchor(ep)
        lines.append(f"- [`{ep.method} {ep.path}`](#{anchor})")
    lines.append("")

    # Full endpoint docs
    for ep in module.endpoints:
        lines.extend(_render_endpoint(ep, api, spec_raw))

    return "\n".join(lines)


def _endpoint_anchor(ep: EndpointInfo) -> str:
    return f"{ep.method.lower()}-{ep.path.replace('/', '').replace('{', '').replace('}', '')}"


def _render_endpoint(ep: EndpointInfo, api: APISpec,
                     spec_raw: dict[str, Any]) -> list[str]:
    lines: list[str] = []

    deprecated = " (DEPRECATED)" if ep.deprecated else ""
    lines.append(f"### `{ep.method}` {ep.path}{deprecated}\n")

    if ep.summary:
        lines.append(f"**{ep.summary}**\n")

    if ep.description and ep.description != ep.summary:
        lines.append(f"{ep.description}\n")

    if ep.operation_id:
        lines.append(f"*Operation ID*: `{ep.operation_id}`\n")

    # Auth
    if ep.security:
        scheme_names = []
        for sec in ep.security:
            for name, scopes in sec.items():
                if scopes:
                    scheme_names.append(f"`{name}` (scopes: {', '.join(scopes)})")
                else:
                    scheme_names.append(f"`{name}`")
        lines.append(f"**Authentication**: {' | '.join(scheme_names)}\n")
    else:
        lines.append("**Authentication**: None required\n")

    # Parameters by location
    _render_parameters(ep.parameters, lines)

    # Request body
    if ep.request_body:
        _render_request_body(ep.request_body, spec_raw, lines)

    # Responses
    if ep.responses:
        _render_responses(ep.responses, api, spec_raw, lines)

    lines.append("---\n")
    return lines


def _render_parameters(params: list[ParameterInfo], lines: list[str]) -> None:
    if not params:
        return

    by_location: dict[str, list[ParameterInfo]] = {}
    for p in params:
        by_location.setdefault(p.location, []).append(p)

    location_labels = {
        "path": "Path Parameters",
        "query": "Query Parameters",
        "header": "Header Parameters",
        "cookie": "Cookie Parameters",
    }

    for loc in ("path", "query", "header", "cookie"):
        group = by_location.get(loc)
        if not group:
            continue

        label = location_labels.get(loc, loc.title())
        lines.append(f"**{label}**:\n")
        lines.append("| Name | Type | Required | Description |")
        lines.append("|------|------|----------|-------------|")

        for p in group:
            ptype = p.schema_type
            if p.schema_format:
                ptype += f" ({p.schema_format})"
            if p.enum:
                ptype += f" enum: {p.enum}"
            req = "Yes" if p.required else "No"
            desc = p.description or "—"
            if p.default is not None:
                desc += f" (default: `{p.default}`)"
            if p.example is not None:
                desc += f" (example: `{p.example}`)"
            lines.append(f"| `{p.name}` | {ptype} | {req} | {desc} |")

        lines.append("")


def _render_request_body(rb, spec_raw: dict[str, Any],
                         lines: list[str]) -> None:
    lines.append("**Request Body**:\n")

    if rb.description:
        lines.append(f"{rb.description}\n")

    if rb.content_types:
        ct_list = ", ".join(f"`{ct}`" for ct in rb.content_types)
        lines.append(f"*Content-Type*: {ct_list}\n")

    if rb.schema_ref:
        lines.append(f"*Schema*: [{rb.schema_ref}](schemas.md#{rb.schema_ref.lower()})\n")

        # Generate example from schema
        raw_schema = (
            spec_raw
            .get("components", {})
            .get("schemas", {})
            .get(rb.schema_ref, {})
        )
        if raw_schema:
            lines.append("**Example payload:**\n")
            lines.append("```json")
            lines.append(example_to_json(raw_schema, spec_raw))
            lines.append("```\n")

    elif rb.is_array and rb.items_ref:
        lines.append(
            f"*Schema*: array of "
            f"[{rb.items_ref}](schemas.md#{rb.items_ref.lower()})\n"
        )
        raw_schema = (
            spec_raw
            .get("components", {})
            .get("schemas", {})
            .get(rb.items_ref, {})
        )
        if raw_schema:
            lines.append("**Example payload:**\n")
            lines.append("```json")
            example = json.dumps(
                [json.loads(example_to_json(raw_schema, spec_raw))],
                indent=2, ensure_ascii=False,
            )
            lines.append(example)
            lines.append("```\n")


def _render_responses(responses, api: APISpec,
                      spec_raw: dict[str, Any],
                      lines: list[str]) -> None:
    lines.append("**Responses**:\n")

    for resp in sorted(responses, key=lambda r: r.status_code):
        status = resp.status_code
        desc = resp.description or "—"
        lines.append(f"- **{status}** — {desc}")

        if resp.schema_ref:
            lines.append(
                f"  - Schema: [{resp.schema_ref}](schemas.md#{resp.schema_ref.lower()})"
            )
        elif resp.is_array and resp.items_ref:
            lines.append(
                f"  - Schema: array of "
                f"[{resp.items_ref}](schemas.md#{resp.items_ref.lower()})"
            )

    lines.append("")


# ---------------------------------------------------------------------------
# Public: generate all reference files
# ---------------------------------------------------------------------------

def generate_all_references(
    api: APISpec,
    spec_raw: dict[str, Any],
) -> dict[str, str]:
    """Return a mapping of ``{filename: content}`` for all reference files.

    Keys are relative paths like ``references/schemas.md`` or
    ``references/pet.md``.
    """
    files: dict[str, str] = {}

    # Schemas
    if api.schemas:
        files["references/schemas.md"] = generate_schemas_reference(api, spec_raw)

    # Per-module
    for module in api.modules:
        fname = sanitize_filename(module.name)
        files[f"references/{fname}.md"] = generate_module_reference(
            module, api, spec_raw,
        )

    return files
