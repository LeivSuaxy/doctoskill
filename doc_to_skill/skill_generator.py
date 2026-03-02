"""Generate the main SKILL.md file for an API skill.

The SKILL.md follows the agent-skill format:
- YAML frontmatter (name, description)
- Concise overview with base URL, auth, and module index
- Pointers to reference files for details (progressive disclosure)
"""

from __future__ import annotations

from .models import APISpec, SecuritySchemeInfo
from .utils import sanitize_filename


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------

def _build_frontmatter(api: APISpec, skill_name: str) -> str:
    # Build a "pushy" description that helps triggering
    module_names = ", ".join(m.name for m in api.modules)
    desc = (
        f"Complete reference for the {api.title} API (v{api.version}). "
        f"Use this skill whenever you need to interact with {api.title} "
        f"endpoints — including {module_names}. "
        f"Covers authentication, all endpoints with parameters and payloads, "
        f"response schemas, and example requests."
    )

    lines = [
        "---",
        f"name: {skill_name}",
        f"description: \"{desc}\"",
        "---",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def _section_overview(api: APISpec) -> str:
    lines = [f"# {api.title}\n"]

    if api.description:
        lines.append(f"{api.description}\n")

    lines.append("## Quick info\n")
    lines.append(f"- **Version**: {api.version}")

    if api.base_url:
        lines.append(f"- **Base URL**: `{api.base_url}`")

    if api.servers and len(api.servers) > 1:
        extra = ", ".join(f"`{s}`" for s in api.servers[1:])
        lines.append(f"- **Additional servers**: {extra}")

    if api.contact_email:
        lines.append(f"- **Contact**: {api.contact_email}")

    if api.license_name:
        lic = api.license_name
        if api.license_url:
            lic = f"[{api.license_name}]({api.license_url})"
        lines.append(f"- **License**: {lic}")

    if api.external_docs_url:
        label = api.external_docs_description or "External docs"
        lines.append(f"- **Docs**: [{label}]({api.external_docs_url})")

    lines.append("")
    return "\n".join(lines)


def _section_auth(api: APISpec) -> str:
    if not api.security_schemes:
        return ""

    lines = ["## Authentication\n"]

    for scheme in api.security_schemes:
        lines.append(f"### {scheme.name}\n")
        lines.append(_describe_scheme(scheme))
        lines.append("")

    return "\n".join(lines)


def _describe_scheme(s: SecuritySchemeInfo) -> str:
    parts: list[str] = []

    if s.type == "http":
        parts.append(f"- **Type**: HTTP {s.scheme}")
        if s.bearer_format:
            parts.append(f"- **Format**: {s.bearer_format}")
        if s.scheme == "bearer":
            parts.append("- **Usage**: Send header `Authorization: Bearer <token>`")
        elif s.scheme == "basic":
            parts.append("- **Usage**: Send header `Authorization: Basic <base64(user:pass)>`")

    elif s.type == "apiKey":
        parts.append(f"- **Type**: API Key")
        parts.append(f"- **Location**: `{s.location}`")
        parts.append(f"- **Parameter name**: `{s.param_name}`")
        parts.append(f"- **Usage**: Send `{s.param_name}: <your-key>` in the {s.location}")

    elif s.type == "oauth2":
        parts.append("- **Type**: OAuth 2.0")
        if s.authorization_url:
            parts.append(f"- **Authorization URL**: `{s.authorization_url}`")
        if s.token_url:
            parts.append(f"- **Token URL**: `{s.token_url}`")
        if s.scopes:
            parts.append("- **Scopes**:")
            for scope, desc in s.scopes.items():
                parts.append(f"  - `{scope}` — {desc}")

    elif s.type == "openIdConnect":
        parts.append("- **Type**: OpenID Connect")

    if s.description:
        parts.append(f"- {s.description}")

    return "\n".join(parts)


def _section_modules(api: APISpec) -> str:
    total_endpoints = sum(len(m.endpoints) for m in api.modules)

    lines = [f"## API Modules ({total_endpoints} endpoints)\n"]
    lines.append("| Module | Endpoints | Description | Reference |")
    lines.append("|--------|-----------|-------------|-----------|")

    for module in api.modules:
        fname = sanitize_filename(module.name)
        desc = module.description or "—"
        count = len(module.endpoints)
        lines.append(
            f"| **{module.name}** | {count} | {desc} "
            f"| [references/{fname}.md](references/{fname}.md) |"
        )

    lines.append("")
    return "\n".join(lines)


def _section_endpoints_overview(api: APISpec) -> str:
    """Quick-reference table of every endpoint (method + path + summary)."""
    lines = ["## Endpoints at a glance\n"]
    lines.append("| Method | Path | Summary | Auth |")
    lines.append("|--------|------|---------|------|")

    for module in api.modules:
        for ep in module.endpoints:
            auth = "Yes" if ep.security else "No"
            summary = ep.summary or "—"
            deprecated = " *(deprecated)*" if ep.deprecated else ""
            lines.append(
                f"| `{ep.method}` | `{ep.path}` | {summary}{deprecated} | {auth} |"
            )

    lines.append("")
    return "\n".join(lines)


def _section_schemas_summary(api: APISpec) -> str:
    if not api.schemas:
        return ""

    lines = ["## Data models\n"]
    lines.append(
        "Full schemas with properties, types, and examples are in "
        "[references/schemas.md](references/schemas.md).\n"
    )
    lines.append("| Model | Fields | Description |")
    lines.append("|-------|--------|-------------|")

    for schema in api.schemas:
        desc = schema.description or "—"
        fields = len(schema.properties)
        lines.append(f"| `{schema.name}` | {fields} | {desc} |")

    lines.append("")
    return "\n".join(lines)


def _section_how_to_use() -> str:
    lines = [
        "## How to use this skill\n",
        "When you need to call an endpoint:\n",
        "1. Check the **Endpoints at a glance** table above to find the right endpoint.",
        "2. Open the corresponding module reference file (linked in the Modules table) "
        "for full details: parameters, request body, responses, and example payloads.",
        "3. Check **Authentication** above to determine what credentials are needed.",
        "4. Check [references/schemas.md](references/schemas.md) if you need to "
        "understand the shape of a request or response object.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_skill_md(api: APISpec, skill_name: str | None = None) -> str:
    """Return the full contents of ``SKILL.md`` for the given API spec.

    Parameters
    ----------
    api:
        The parsed API specification.
    skill_name:
        Override for the skill name.  Defaults to a sanitised version of
        the API title.
    """
    if skill_name is None:
        skill_name = sanitize_filename(api.title) + "-api"

    parts = [
        _build_frontmatter(api, skill_name),
        "",
        _section_overview(api),
        _section_auth(api),
        _section_modules(api),
        _section_endpoints_overview(api),
        _section_schemas_summary(api),
        _section_how_to_use(),
    ]

    return "\n".join(parts)
