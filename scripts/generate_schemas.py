"""Generate JSON Schema files for every EAP resource kind.

The JSON Schemas in ``contracts/schemas/`` are the public, declarative form of
the contracts. They are generated from the executable Pydantic models so the two
never drift. Run this whenever a spec model changes:

    python scripts/generate_schemas.py
"""

from __future__ import annotations

import json
from pathlib import Path

from eap.specifications.loader import KIND_MODELS

OUT_DIR = Path(__file__).resolve().parents[1] / "contracts" / "schemas"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for kind, model_cls in KIND_MODELS.items():
        schema = model_cls.model_json_schema(by_alias=True)
        schema["title"] = kind.value
        target = OUT_DIR / f"{kind.value}.schema.json"
        target.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {target.relative_to(OUT_DIR.parents[1])}")


if __name__ == "__main__":
    main()
