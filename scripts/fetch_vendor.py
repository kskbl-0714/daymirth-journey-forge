"""Vendor pinned Leaflet/PDF.js runtimes and their licenses, never trip data."""
import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

FILES = {
    "leaflet.js": "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js",
    "leaflet.css": "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css",
    "images/marker-icon.png": "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/images/marker-icon.png",
    "images/marker-icon-2x.png": "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/images/marker-icon-2x.png",
    "images/marker-shadow.png": "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/images/marker-shadow.png",
    "images/layers.png": "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/images/layers.png",
    "images/layers-2x.png": "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/images/layers-2x.png",
    "LEAFLET-LICENSE.txt": "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/LICENSE",
    "pdf.min.js": "https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.min.js",
    "pdf.worker.min.js": "https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.worker.min.js",
    "PDFJS-LICENSE.txt": "https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/LICENSE",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "assets/web/vendor")
    args = parser.parse_args()
    lockfile = args.output / "vendor-lock.json"
    expected = json.loads(lockfile.read_text()) if lockfile.exists() else {}
    lock = {}
    for name, url in FILES.items():
        path = args.output / name
        if path.exists() and name in expected and hashlib.sha256(path.read_bytes()).hexdigest() == expected[name]["sha256"]:
            content = path.read_bytes()
        else:
            with urllib.request.urlopen(url, timeout=45) as response:
                content = response.read()
        digest = hashlib.sha256(content).hexdigest()
        if name in expected and digest != expected[name]["sha256"]:
            raise SystemExit("Integrity mismatch: " + name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        lock[name] = {"url": url, "sha256": digest}
        print(name, len(content))
    lockfile.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
