#!/usr/bin/env python3
"""swagger-to-skill: Convert an OpenAPI/Swagger spec into an agent skill.

Usage
-----
    # From a local file:
    python main.py example.json

    # From a URL:
    python main.py http://127.0.0.1:8000/openapi.json

    # With options:
    python main.py example.json -o my-skill -n my-api-skill

    # Or as a module:
    python -m doc_to_skill example.json
"""

from doc_to_skill.__main__ import main

if __name__ == "__main__":
    main()
