import argparse
import csv
import gzip
import hashlib
import shutil
from pathlib import Path

from kpi_autopsy.export import write_json
from kpi_autopsy.powerbi import TABLES, generate


def package(data_folder: Path, output: Path, data_url: str) -> Path:
    files = []
    for filename, _ in TABLES.values():
        source = data_folder / filename
        target = output / "data" / (filename + ".gz")
        target.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as incoming, target.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                shutil.copyfileobj(incoming, compressed)
        with source.open(newline="", encoding="utf-8") as stream:
            rows = sum(1 for _ in csv.reader(stream)) - 1
        with target.open("rb") as stream:
            fingerprint = hashlib.file_digest(stream, "sha256").hexdigest()
        files.append({"file": target.name, "rows": rows,
                      "sha256": fingerprint})
    write_json(output / "data" / "manifest.json", {"tables": files})
    return generate(data_folder, output / "report", data_url=data_url)


def main() -> None:
    parser = argparse.ArgumentParser(description="Package the full exports for the shared Power BI report.")
    parser.add_argument("--data-folder", type=Path, default=Path("reports/powerbi"))
    parser.add_argument("--output", type=Path, default=Path("powerbi"))
    parser.add_argument("--data-url", required=True)
    args = parser.parse_args()
    print(package(args.data_folder, args.output, args.data_url))


if __name__ == "__main__":
    main()
