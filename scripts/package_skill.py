"""Package only public Skill files, with integrity metadata; no upload is performed."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP_FILES = {"SKILL.md", "README.md", "README.zh-CN.md", "CHANGELOG.md", "LICENSE", ".gitignore", "requirements.txt"}
TOP_DIRS = {".github", "agents", "assets", "examples", "references", "scripts"}
SKIP_PARTS = {"__pycache__", ".git", ".gradle", "build"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(ROOT):
        raise ValueError("Store the archive outside the Skill repository")
    files = []
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if not path.is_file() or SKIP_PARTS.intersection(rel.parts) or path.suffix in {".pyc", ".pyo"}:
            continue
        if (len(rel.parts) == 1 and rel.name in TOP_FILES) or (len(rel.parts) > 1 and rel.parts[0] in TOP_DIRS):
            if path.suffix.lower() in {".jks", ".keystore", ".pem", ".key", ".p12", ".apk", ".aab"}:
                raise ValueError("Forbidden release file: " + str(rel))
            files.append(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, ROOT.name + "/" + path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("Archive integrity check failed")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix + ".sha256").write_text(digest + "  " + output.name + "\n", encoding="utf-8")
    print(json.dumps({"archive": str(output), "files": len(files), "sha256": digest}, indent=2))


if __name__ == "__main__":
    main()
