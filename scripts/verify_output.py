"""Static completeness/privacy checks for a generated web app."""
import argparse
import json
import re
from pathlib import Path


def verify(root):
    root = Path(root).resolve()
    errors, warnings = [], []
    required = ["index.html", "style.css", "app.js", "trip.json", "sw.js", "cache-config.js", "manifest.webmanifest", "vendor/leaflet.js", "vendor/leaflet.css", "vendor/pdf.min.js", "vendor/pdf.worker.min.js", "icons/icon-192.png", "icons/icon-512.png"]
    for name in required:
        if not (root / name).is_file(): errors.append("Missing " + name)
    if errors: return errors, warnings
    trip = json.loads((root / "trip.json").read_text(encoding="utf-8"))
    all_ids = [e["id"] for d in trip["days"] for e in d["events"]]
    if len(set(all_ids)) != len(all_ids): errors.append("Event IDs are not globally unique")
    for ticket in trip.get("tickets", []):
        if ticket.get("file") and not (root / ticket["file"]).is_file(): errors.append("Missing ticket " + ticket["file"])
    declared = set(json.loads(re.search(r"self\.TRIP_CACHE=(.*);", (root/"cache-config.js").read_text(), re.S).group(1))["assets"])
    for path in root.rglob("*"):
        if path.is_file() and path.name not in ("sw.js", "cache-config.js") and path.relative_to(root).as_posix() not in declared: errors.append("Uncached app asset " + path.relative_to(root).as_posix())
    text_files = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in (".html", ".css", ".js", ".json", ".webmanifest", ".txt") and "vendor" not in p.parts]
    content = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in text_files)
    for pattern, label in [(r"https?://images\.unsplash\.com", "remote Unsplash image"), (r"(?i)(password|storePassword)\s*[:=]\s*['\"][^'\"]+", "embedded password"), (r"(?i)BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY", "private key")]:
        if re.search(pattern, content): errors.append("Detected " + label)
    allowed_remote = ("tile.openstreetmap.org", "www.openstreetmap.org/copyright", "www.google.com/maps", "maps.apple.com", "uri.amap.com", "creativecommons.org")
    for url in re.findall(r"https://[^\s'\"<>]+", content):
        if not any(host in url for host in allowed_remote) and not any(url == c.get(k) for c in trip.get("mediaCredits", []) for k in ("sourceUrl", "licenseUrl")):
            warnings.append("Review remote URL: " + url[:160])
    if trip.get("settings", {}).get("privacy") == "public-demo":
        for ticket in trip.get("tickets", []):
            if ticket.get("file") and "fictional" not in ticket.get("notes", "").lower(): errors.append("Public demo ticket not visibly marked fictional: " + ticket["id"])
    return errors, sorted(set(warnings))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("web");a=p.parse_args();errors,warnings=verify(a.web)
    for item in warnings: print("WARNING:", item)
    for item in errors: print("ERROR:", item)
    print(f"{len(errors)} errors, {len(warnings)} warnings")
    return bool(errors)
if __name__ == "__main__": raise SystemExit(main())
