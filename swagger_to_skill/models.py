"""Data models for parsed OpenAPI specifications."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParameterInfo:
    """A single endpoint parameter (path, query, header, cookie)."""

    name: str
    location: str  # "path" | "query" | "header" | "cookie"
    required: bool = False
    description: str = ""
    schema_type: str = "string"
    schema_format: str | None = None
    default: str | None = None
    enum: list[str] = field(default_factory=list)
    example: str | None = None


@dataclass
class SchemaProperty:
    """A single property inside a component schema."""

    name: str
    type: str = "string"
    format: str | None = None
    description: str = ""
    required: bool = False
    enum: list[str] = field(default_factory=list)
    example: str | None = None
    ref: str | None = None
    items_ref: str | None = None
    items_type: str | None = None


@dataclass
class SchemaDefinition:
    """A fully-resolved component schema (e.g. Pet, Order)."""

    name: str
    type: str = "object"
    description: str = ""
    properties: list[SchemaProperty] = field(default_factory=list)
    required_fields: list[str] = field(default_factory=list)


@dataclass
class RequestBodyInfo:
    """Parsed request body for an endpoint."""

    description: str = ""
    required: bool = False
    content_types: list[str] = field(default_factory=list)
    schema_ref: str | None = None
    schema_properties: list[SchemaProperty] = field(default_factory=list)
    is_array: bool = False
    items_ref: str | None = None


@dataclass
class ResponseInfo:
    """A single HTTP response definition."""

    status_code: str
    description: str = ""
    schema_ref: str | None = None
    is_array: bool = False
    items_ref: str | None = None


@dataclass
class EndpointInfo:
    """A fully parsed API endpoint."""

    path: str
    method: str
    summary: str = ""
    description: str = ""
    operation_id: str = ""
    tags: list[str] = field(default_factory=list)
    parameters: list[ParameterInfo] = field(default_factory=list)
    request_body: RequestBodyInfo | None = None
    responses: list[ResponseInfo] = field(default_factory=list)
    security: list[dict[str, list[str]]] = field(default_factory=list)
    deprecated: bool = False


@dataclass
class SecuritySchemeInfo:
    """An authentication / security scheme."""

    name: str
    type: str  # "http" | "apiKey" | "oauth2" | "openIdConnect"
    scheme: str = ""  # "bearer", "basic", etc.
    bearer_format: str = ""
    location: str = ""  # "header" | "query" | "cookie"  (for apiKey)
    param_name: str = ""  # actual header / query name   (for apiKey)
    description: str = ""
    scopes: dict[str, str] = field(default_factory=dict)
    authorization_url: str = ""
    token_url: str = ""


@dataclass
class ModuleInfo:
    """A group of endpoints sharing the same tag."""

    name: str
    description: str = ""
    endpoints: list[EndpointInfo] = field(default_factory=list)
    external_docs_url: str = ""


@dataclass
class APISpec:
    """The entire parsed OpenAPI specification."""

    title: str
    version: str
    description: str = ""
    base_url: str = ""
    servers: list[str] = field(default_factory=list)
    modules: list[ModuleInfo] = field(default_factory=list)
    schemas: list[SchemaDefinition] = field(default_factory=list)
    security_schemes: list[SecuritySchemeInfo] = field(default_factory=list)
    external_docs_url: str = ""
    external_docs_description: str = ""
    contact_email: str = ""
    license_name: str = ""
    license_url: str = ""
    terms_of_service: str = ""
