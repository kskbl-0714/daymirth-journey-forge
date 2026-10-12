"""Validate trip data and local paths. No third-party dependencies."""
import argparse
import datetime
import json
import re
from pathlib import Path

ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MIMES = {"application/pdf": {".pdf"}, "image/jpeg": {".jpg", ".jpeg"}, "image/png": {".png"}}


def local_path(value, prefix, root=None):
    if not isinstance(value, str) or not value.startswith(prefix + "/"):
        raise ValueError(f"Expected {prefix}/ relative path: {value!r}")
    if any(c in value for c in ("\\", "%", ":", "?", "#", "\x00")) or any(p in ("", ".", "..") for p in value.split("/")):
        raise ValueError(f"Unsafe path: {value!r}")
    if root:
        target = (Path(root) / value).resolve()
        if not target.is_relative_to(Path(root).resolve()):
            raise ValueError(f"Path escapes input root: {value}")
        return target
    return Path(value)


def validate(data, root=None):
    errors = []
    warnings = []
    def check(ok, message):
        if not ok:
            errors.append(message)
    def ids(items, label):
        if not isinstance(items, list):
            errors.append(label + " must be an array")
            return set()
        result = set()
        for item in items:
            if not isinstance(item, dict):
                errors.append(label + " entries must be objects")
                continue
            value = item.get("id", "")
            if not isinstance(value, str) or not ID.fullmatch(value):
                errors.append(f"Invalid {label} id: {value!r}")
            if value in result:
                errors.append(f"Duplicate {label} id: {value}")
            if isinstance(value, str):
                result.add(value)
        return result
    if not isinstance(data, dict):
        return ["Root must be an object"], []
    check(data.get("schemaVersion") == 1, "schemaVersion must be 1")
    check(isinstance(data.get("tripId"), str) and bool(ID.fullmatch(data.get("tripId", ""))), "Invalid tripId")
    app = data.get("app", {})
    if not isinstance(app, dict):
        return errors + ["app must be object"], warnings
    check(app.get("language", "zh") in ("zh", "en", "bilingual"), "Invalid app language")
    for key in ("name", "subtitle"):
        check(key not in app or isinstance(app[key], str), f"app.{key} must be text")
    theme = app.get("theme", {})
    check(isinstance(theme, dict), "theme must be object")
    if isinstance(theme, dict):
        for key, value in theme.items():
            check(isinstance(value, str) and bool(re.fullmatch(r"#[0-9a-fA-F]{6}", value)), f"Invalid theme color {key}")
    settings = data.get("settings", {})
    check(isinstance(settings, dict), "settings must be object")
    if isinstance(settings, dict):
        check(settings.get("embeddedMap", "osm") in ("osm", "none"), "Unsupported map adapter; implement/test provider first")
        check(settings.get("navigation", "system") in ("system", "google", "apple", "amap"), "Invalid navigation provider")
        check(settings.get("privacy", "private") in ("private", "public-demo"), "Invalid privacy mode")
        check(isinstance(settings.get("platforms", ["pwa"]), list) and all(p in ("android", "iphone", "pwa") for p in settings.get("platforms", ["pwa"])), "Invalid target platforms")
    travelers = data.get("travelers", [])
    traveler_ids = ids(travelers, "traveler")
    days = data.get("days", [])
    check(isinstance(days, list) and len(days) > 0, "At least one day required")
    ids(days, "day")
    events = []
    images = []
    for key in ("cover", "icon"):
        if app.get(key):
            images.append(app[key])
    if isinstance(days, list):
        for day in days:
            if not isinstance(day, dict):
                continue
            if day.get("date"):
                try:
                    datetime.date.fromisoformat(day["date"])
                except (ValueError, TypeError):
                    errors.append("Invalid ISO date: " + str(day["date"]))
            if day.get("banner"):
                images.append(day["banner"])
            if not isinstance(day.get("events"), list):
                errors.append("Day events must be array")
                continue
            events.extend(day["events"])
            check(isinstance(day.get("notices", []), list), "Day notices must be array")
    event_ids = ids(events, "event")
    for event in events:
        if not isinstance(event, dict):
            continue
        check(isinstance(event.get("title"), str) and bool(event["title"].strip()), "Event title required")
        check(isinstance(event.get("notices", []), list), "Event notices must be array")
        c = event.get("coordinates")
        if c is not None:
            check(isinstance(c, dict) and type(c.get("lat")) in (float, int) and type(c.get("lng")) in (float, int) and -90 <= c["lat"] <= 90 and -180 <= c["lng"] <= 180, "Invalid event coordinates")
        if event.get("photo"):
            images.append(event["photo"])
    credits = data.get("mediaCredits", [])
    check(isinstance(credits, list), "mediaCredits must be array")
    credited = {c.get("file") for c in credits if isinstance(c, dict)} if isinstance(credits, list) else set()
    for image in images:
        try:
            p = local_path(image, "media", root)
            check(p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".svg"), "Unsupported image type")
            if root:
                check(p.is_file(), f"Missing image: {image}")
            check(image in credited, f"Missing media license entry: {image}")
        except ValueError as exc:
            errors.append(str(exc))
    tickets = data.get("tickets", [])
    ids(tickets, "ticket")
    if isinstance(tickets, list):
        for ticket in tickets:
            if not isinstance(ticket, dict):
                continue
            mime = ticket.get("mimeType")
            check(mime in MIMES, "Unsupported ticket MIME type")
            for key, allowed in (("eventIds", event_ids), ("travelerIds", traveler_ids)):
                values = ticket.get(key, [])
                check(isinstance(values, list), key + " must be array")
                if isinstance(values, list):
                    check(all(v in allowed for v in values), f"Unknown IDs in ticket {key}")
            if ticket.get("file"):
                try:
                    p = local_path(ticket["file"], "tickets", root)
                    check(bool(re.fullmatch(r"[a-zA-Z0-9_.-]+", p.name)), "Ticket internal filename must be ASCII-safe")
                    check(p.suffix.lower() in MIMES.get(mime, set()), "Ticket extension/MIME mismatch")
                    if root and ticket.get("deliveryMode") != "local-import":
                        check(p.is_file(), "Missing ticket: " + ticket["file"])
                except ValueError as exc:
                    errors.append(str(exc))
            else:
                warnings.append(f"Ticket {ticket.get('id')} requires local import")
    for credit in credits if isinstance(credits, list) else []:
        if not isinstance(credit, dict):
            errors.append("Credit must be object")
            continue
        check(bool(credit.get("author")) and bool(credit.get("license")), "Credit needs author and license")
        for key in ("sourceUrl", "licenseUrl"):
            if credit.get(key):
                check(isinstance(credit[key], str) and credit[key].startswith("https://"), "Credit URLs must use https")
    if not any(e.get("coordinates") for e in events if isinstance(e, dict)):
        warnings.append("No verified coordinates; map is omitted")
    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trip")
    parser.add_argument("--assets-root")
    args = parser.parse_args()
    data = json.loads(Path(args.trip).read_text(encoding="utf-8-sig"))
    errors, warnings = validate(data, args.assets_root)
    for item in warnings:
        print("WARNING:", item)
    for item in errors:
        print("ERROR:", item)
    print(f"{len(errors)} errors, {len(warnings)} warnings")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
