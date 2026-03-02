"""Utilities shared across modules."""

from __future__ import annotations

import re


def sanitize_filename(name: str) -> str:
    """Convert a module / schema name into a safe, lowercase filename stem.

    Examples
    --------
    >>> sanitize_filename("Pet Store")
    'pet-store'
    >>> sanitize_filename("user/admin")
    'user-admin'
    """
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    return name.strip("-")


def indent(text: str, level: int = 1, width: int = 2) -> str:
    """Indent every line of *text* by *level* x *width* spaces."""
    prefix = " " * (level * width)
    return "\n".join(prefix + line if line else "" for line in text.splitlines())


def ref_name(ref: str) -> str:
    """Extract the component name from a ``$ref`` string.

    >>> ref_name("#/components/schemas/Pet")
    'Pet'
    """
    return ref.rsplit("/", 1)[-1] if ref else ""
