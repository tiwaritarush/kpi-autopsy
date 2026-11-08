import argparse
import json
import urllib.request
from pathlib import Path

from jsonschema.validators import validator_for
from referencing import Registry, Resource

BASE = "https://developer.microsoft.com/json-schemas/"
SCHEMAS = [
    "fabric/gitIntegration/platformProperties/2.0.0/schema.json",
    "fabric/pbip/pbipProperties/1.0.0/schema.json",
    "fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
    "fabric/item/report/definitionProperties/2.0.0/schema.json",
    "fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
    *[f"fabric/item/report/definition/{name}/1.0.0/schema.json" for name in (
        "report", "page", "versionMetadata", "visualContainer",
        "semanticQuery", "formattingObjectDefinitions",
    )],
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path("powerbi/generated"))
    parser.add_argument("--schema-dir", type=Path, default=Path(".test-tmp/pbir-schemas"))
    args = parser.parse_args()
    args.schema_dir.mkdir(parents=True, exist_ok=True)
    resources = {}
    for path in SCHEMAS:
        filename = args.schema_dir / (path.removesuffix("/schema.json").replace("/", "_") + ".json")
        if not filename.exists():
            url = "https://raw.githubusercontent.com/microsoft/json-schemas/main/" + path
            with urllib.request.urlopen(url, timeout=30) as response:
                filename.write_bytes(response.read())
        resources[BASE + path] = json.loads(filename.read_text(encoding="utf-8-sig"))
    registry = Registry().with_resources((url, Resource.from_contents(schema)) for url, schema in resources.items())
    checked = 0
    for path in sorted(args.project.rglob("*")):
        if not path.is_file() or (path.suffix not in {".json", ".pbip", ".pbir", ".pbism"} and path.name != ".platform"):
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        uri = document.get("$schema")
        if not uri:
            continue
        schema = resources[uri]
        validator = validator_for(schema)(schema, registry=registry)
        errors = sorted(validator.iter_errors(document), key=lambda error: str(error.path))
        if errors:
            details = "\n".join(f"  {list(error.path)}: {error.message}" for error in errors)
            raise SystemExit(f"Invalid Power BI file: {path}\n{details}")
        checked += 1
    if not checked:
        raise SystemExit("No generated Power BI files were found. Run the build command first.")
    print(f"Validated {checked} Power BI files against Microsoft's public schemas.")
    print("This checks the file format. Opening and refreshing in Power BI Desktop is a separate check.")


if __name__ == "__main__":
    main()
