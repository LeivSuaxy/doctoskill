"""CLI entry point: ``python -m doc_to_skill``."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .parser import load_spec, parse
from .reference_generator import generate_all_references
from .skill_generator import generate_skill_md
from .utils import sanitize_filename


def build_skill(
    source: str,
    output_dir: str | None = None,
    skill_name: str | None = None,
) -> Path:
    """Parse an OpenAPI spec and write the full skill directory.

    Parameters
    ----------
    source:
        URL or local file path to the OpenAPI JSON spec.
    output_dir:
        Destination directory.  Defaults to ``<skill-name>/`` in the
        current working directory.
    skill_name:
        Override the auto-generated skill name.

    Returns
    -------
    Path to the created skill directory.
    """
    api = parse(source)

    if skill_name is None:
        skill_name = sanitize_filename(api.title) + "-api"

    if output_dir is None:
        output_dir = f"generated/{skill_name}"

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "references").mkdir(exist_ok=True)

    # -- SKILL.md ------------------------------------------------------------
    skill_md = generate_skill_md(api, skill_name=skill_name)
    (out / "SKILL.md").write_text(skill_md, encoding="utf-8")

    # -- Reference files -----------------------------------------------------
    spec_raw = load_spec(source)
    refs = generate_all_references(api, spec_raw)

    for rel_path, content in refs.items():
        dest = out / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")

    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="swagger-to-skill",
        description="Convert an OpenAPI/Swagger spec into an agent skill.",
    )
    parser.add_argument(
        "source",
        help="URL or local file path to the OpenAPI JSON specification.",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output directory (default: generated/<skill-name>/).",
    )
    parser.add_argument(
        "-n", "--name",
        default=None,
        help="Skill name override (default: derived from API title).",
    )

    args = parser.parse_args(argv)

    try:
        out = build_skill(args.source, output_dir=args.output,
                          skill_name=args.name)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    # Summary
    files = list(out.rglob("*.md"))
    print(f"Skill generated in: {out}/")
    print(f"  SKILL.md + {len(files) - 1} reference files")


if __name__ == "__main__":
    main()
