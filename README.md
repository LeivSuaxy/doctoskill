# doc-to-skill

**doctoskill** is an open-source tool that transforms OpenAPI / Swagger specifications (JSON) into structured **agent skills** — a SKILL.md entry point paired with a set of detailed Markdown reference files.

Built on a simple belief: **a well-documented API shouldn't just help your team — it should power your AI agents too**.

The generated skills are designed to be loaded by AI agents that support the skill format, giving them complete knowledge of any REST API with minimal token overhead.

**doctoskill is not AI-powered**. The skill generation is fully static — no magic, no inference, no hidden model rewriting your docs. The output quality depends entirely on how well your API is documented. That's intentional: this tool is a bet on good documentation, and a reward for teams that take it seriously.

---

## Output structure

```
generated/<skill-name>/
├── SKILL.md              ← entry point with quick overview, auth, and endpoint table
└── references/
    ├── <module-1>.md     ← full docs for every endpoint in the module
    ├── <module-2>.md
    └── schemas.md        ← all data models with property tables and example payloads
```

---

## Requirements

| Requirement | Version |
|-------------|---------|
| Python | ≥ 3.14 |
| [uv](https://docs.astral.sh/uv/) *(recommended)* | latest |

---

## Installation & setup

### Option A — with `uv` (recommended)

```bash
# 1. Clone the repository
git clone https://github.com/LeivSuaxy/doctoskill.git
cd swagger-to-skill

# 2. Create a virtual environment and install dependencies
uv sync

# 3. Activate the environment (optional, uv run handles it automatically)
source .venv/bin/activate
```

### Option B — with standard `pip`

```bash
# 1. Clone the repository
git clone https://github.com/LeivSuaxy/doctoskill.git
cd swagger-to-skill

# 2. Create and activate a virtual environment
python3.14 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install requests
```

---

## Usage

### From a local file

```bash
python main.py path/to/openapi.json
```

### From a URL

```bash
python main.py http://127.0.0.1:8000/openapi.json
```

### With options

```bash
# Custom output directory
python main.py openapi.json -o my-output-dir

# Custom skill name
python main.py openapi.json -n my-api-skill

# Both at once
python main.py openapi.json -o my-output-dir -n my-api-skill
```

### As a Python module

```bash
python -m doc_to_skill openapi.json
```

### With `uv run` (no manual activation needed)

```bash
uv run python main.py openapi.json
```

---

## CLI reference

```
usage: doc-to-skill [-h] [-o OUTPUT] [-n NAME] source

Convert an OpenAPI/Swagger spec into an agent skill.

positional arguments:
  source          URL or local file path to the OpenAPI JSON specification.

options:
  -h, --help      Show this help message and exit.
  -o, --output    Output directory (default: generated/<skill-name>/).
  -n, --name      Skill name override (default: derived from the API title).
```

---

## Example

Using the public Swagger Petstore spec:

```bash
python main.py https://petstore3.swagger.io/api/v3/openapi.json
```

This generates:

```
generated/swagger-petstore-openapi-3-0-api/
├── SKILL.md
└── references/
    ├── pet.md
    ├── store.md
    ├── user.md
    └── schemas.md
```

---

## Python API

You can also call the tool programmatically:

```python
from doc_to_skill.__main__ import build_skill

out_path = build_skill(
    source="https://petstore3.swagger.io/api/v3/openapi.json",
    output_dir="output/petstore",   # optional
    skill_name="petstore-skill",    # optional
)
print(f"Skill written to: {out_path}")
```

---

## Project structure

```
doc-to-skill/
├── main.py                        ← CLI entry point
├── pyproject.toml
├── uv.lock
└── doc_to_skill/
    ├── __main__.py                ← argparse CLI + build_skill()
    ├── models.py                  ← dataclasses (APISpec, EndpointInfo, …)
    ├── parser.py                  ← loads and parses the OpenAPI JSON
    ├── schema_resolver.py         ← resolves $ref chains and builds examples
    ├── skill_generator.py         ← renders SKILL.md
    ├── reference_generator.py     ← renders references/*.md
    └── utils.py                   ← shared helpers
```

---

## License

[Apache](LICENSE)
