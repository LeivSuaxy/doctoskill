"""Parse an OpenAPI 3.x specification into an ``APISpec`` model."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import requests

from .models import (
    APISpec,
    EndpointInfo,
    ModuleInfo,
    ParameterInfo,
    RequestBodyInfo,
    ResponseInfo,
    SecuritySchemeInfo,
)
from .schema_resolver import parse_schema_definition, resolve_schema
from .utils import ref_name


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_spec(source: str) -> dict[str, Any]:
    """Load an OpenAPI spec from a URL or a local file path.

    Raises ``ValueError`` when the source cannot be loaded or parsed.
    """
    path = Path(source)
    if path.is_file():
        text = path.read_text(encoding="utf-8")
        return json.loads(text)

    # Treat as URL
    try:
        resp = requests.get(source, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        raise ValueError(f"Cannot load OpenAPI spec from '{source}': {exc}") from exc


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_parameters(raw_params: list[dict[str, Any]]) -> list[ParameterInfo]:
    params: list[ParameterInfo] = []
    for p in raw_params:
        schema = p.get("schema", {})
        params.append(ParameterInfo(
            name=p["name"],
            location=p.get("in", "query"),
            required=p.get("required", False),
            description=p.get("description", ""),
            schema_type=schema.get("type", "string"),
            schema_format=schema.get("format"),
            default=str(schema["default"]) if "default" in schema else None,
            enum=schema.get("enum", []),
            example=str(p["example"]) if "example" in p else None,
        ))
    return params


def _parse_request_body(raw: dict[str, Any], spec: dict[str, Any]) -> RequestBodyInfo:
    content = raw.get("content", {})
    content_types = list(content.keys())

    # Use the first content type that has a schema
    schema_ref: str | None = None
    is_array = False
    items_ref: str | None = None

    for ct_data in content.values():
        schema = ct_data.get("schema", {})
        if "$ref" in schema:
            schema_ref = ref_name(schema["$ref"])
            break
        resolved = resolve_schema(schema, spec)
        if resolved.get("type") == "array":
            is_array = True
            items = resolved.get("items", {})
            if "$ref" in items:
                items_ref = ref_name(items["$ref"])
            break
        if "properties" in resolved:
            # Inline schema – we don't assign a ref but could expand later
            break

    return RequestBodyInfo(
        description=raw.get("description", ""),
        required=raw.get("required", False),
        content_types=content_types,
        schema_ref=schema_ref,
        is_array=is_array,
        items_ref=items_ref,
    )


def _parse_responses(raw: dict[str, Any], spec: dict[str, Any]) -> list[ResponseInfo]:
    responses: list[ResponseInfo] = []
    for code, data in raw.items():
        schema_ref: str | None = None
        is_array = False
        items_ref: str | None = None

        if "content" in data:
            for ct_data in data["content"].values():
                schema = ct_data.get("schema", {})
                if "$ref" in schema:
                    schema_ref = ref_name(schema["$ref"])
                    break
                resolved = resolve_schema(schema, spec)
                if resolved.get("type") == "array":
                    is_array = True
                    items = resolved.get("items", {})
                    if "$ref" in items:
                        items_ref = ref_name(items["$ref"])
                    break
                break

        responses.append(ResponseInfo(
            status_code=str(code),
            description=data.get("description", ""),
            schema_ref=schema_ref,
            is_array=is_array,
            items_ref=items_ref,
        ))
    return responses


def _parse_security_schemes(raw: dict[str, Any]) -> list[SecuritySchemeInfo]:
    schemes: list[SecuritySchemeInfo] = []
    for name, data in raw.items():
        scheme_type = data.get("type", "")
        scopes: dict[str, str] = {}
        auth_url = ""
        token_url = ""

        if scheme_type == "oauth2":
            flows = data.get("flows", {})
            for flow_data in flows.values():
                scopes.update(flow_data.get("scopes", {}))
                auth_url = auth_url or flow_data.get("authorizationUrl", "")
                token_url = token_url or flow_data.get("tokenUrl", "")

        schemes.append(SecuritySchemeInfo(
            name=name,
            type=scheme_type,
            scheme=data.get("scheme", ""),
            bearer_format=data.get("bearerFormat", ""),
            location=data.get("in", ""),
            param_name=data.get("name", ""),
            description=data.get("description", ""),
            scopes=scopes,
            authorization_url=auth_url,
            token_url=token_url,
        ))
    return schemes


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}


def parse(source: str) -> APISpec:
    """Load and parse an OpenAPI specification, returning an ``APISpec``.

    Parameters
    ----------
    source:
        A URL (``http(s)://...``) or a local file path to a JSON OpenAPI spec.
    """
    spec = load_spec(source)
    info = spec.get("info", {})

    # -- Servers -------------------------------------------------------------
    servers_raw = spec.get("servers", [])
    servers = [s.get("url", "") for s in servers_raw]
    base_url = servers[0] if servers else ""

    # -- Security schemes ----------------------------------------------------
    components = spec.get("components", {})
    security_schemes = _parse_security_schemes(
        components.get("securitySchemes", {}),
    )

    # -- Schemas -------------------------------------------------------------
    schemas = [
        parse_schema_definition(name, raw, spec)
        for name, raw in components.get("schemas", {}).items()
    ]

    # -- Endpoints grouped by tag --------------------------------------------
    tag_map: dict[str, list[EndpointInfo]] = defaultdict(list)

    for path, methods in spec.get("paths", {}).items():
        for method, details in methods.items():
            if method.lower() not in HTTP_METHODS:
                continue

            params = _parse_parameters(details.get("parameters", []))
            req_body = (
                _parse_request_body(details["requestBody"], spec)
                if "requestBody" in details
                else None
            )
            responses = _parse_responses(details.get("responses", {}), spec)
            tags = details.get("tags", ["General"])

            ep = EndpointInfo(
                path=path,
                method=method.upper(),
                summary=details.get("summary", ""),
                description=details.get("description", ""),
                operation_id=details.get("operationId", ""),
                tags=tags,
                parameters=params,
                request_body=req_body,
                responses=responses,
                security=details.get("security", []),
                deprecated=details.get("deprecated", False),
            )

            for tag in tags:
                tag_map[tag].append(ep)

    # -- Build ModuleInfo from tags ------------------------------------------
    tag_descriptions: dict[str, tuple[str, str]] = {}
    for tag_obj in spec.get("tags", []):
        ext_docs = tag_obj.get("externalDocs", {})
        tag_descriptions[tag_obj["name"]] = (
            tag_obj.get("description", ""),
            ext_docs.get("url", ""),
        )

    modules = []
    for tag_name in sorted(tag_map):
        desc, ext_url = tag_descriptions.get(tag_name, ("", ""))
        endpoints = sorted(tag_map[tag_name], key=lambda e: (e.path, e.method))
        modules.append(ModuleInfo(
            name=tag_name,
            description=desc,
            endpoints=endpoints,
            external_docs_url=ext_url,
        ))

    # -- External docs -------------------------------------------------------
    ext_docs = spec.get("externalDocs", {})

    return APISpec(
        title=info.get("title", "API"),
        version=info.get("version", ""),
        description=info.get("description", ""),
        base_url=base_url,
        servers=servers,
        modules=modules,
        schemas=schemas,
        security_schemes=security_schemes,
        external_docs_url=ext_docs.get("url", ""),
        external_docs_description=ext_docs.get("description", ""),
        contact_email=info.get("contact", {}).get("email", ""),
        license_name=info.get("license", {}).get("name", ""),
        license_url=info.get("license", {}).get("url", ""),
        terms_of_service=info.get("termsOfService", ""),
    )
