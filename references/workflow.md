# Complete production workflow

## Intake

Read current conversation, pasted itinerary, documents, screenshots, PDFs. Another chat is usable only if its content/link is accessible. Recommend confirming itinerary before invocation. Present already obtained, needs confirmation, and each fallback.

| Input | Ask if missing | Fallback |
|---|---|---|
| Destination/itinerary | Required: destination or travel intent | Help organize; never fabricate bookings |
| Dates/times | Only if needed for booking accuracy | Day 1/2; morning/afternoon/evening or order |
| App name | Ask once, supports Chinese/English | TripPocket |
| Platform | Android/iPhone/both | PWA plus Android attempt if tools available |
| Language | Chinese/English/bilingual | Infer from user language |
| Embedded map | Separate from navigation | OpenStreetMap |
| External navigation | Apple/Google/Amap/system | Device-appropriate chooser |
| Tickets/travelers | Associate existing files; ask ambiguous links | Hide ticket controls if absent |
| Cover/icon | Offer supplied image | Original route cover and name-based icon |
| Landmark photos | Search proactively first | Disclose gap; contextual illustration/no image |
| Daily fun banners | Match supplied pool first | Ask AI generation or remove; if unanswered omit |
| Theme/subtitle | Do not ask | Derive automatically; explicit confirmation overrides |

Preserve paid booking times and surface overlaps/transport gaps. No unsolicited reshuffling. If optimization is requested, explain assumptions and preserve fixed commitments. Map lines are schematic event order, actual navigation is external. Optional reservation/Xiaohongshu shortcuts may be added when supplied; no Dianping dependency.

## Build

Keep private input/output outside the public repo. Assign stable trip/day/event/ticket/traveler IDs, independent of titles and array order. ASCII-safe ticket filenames retain original display names in JSON. One ticket may serve many people/events; many files may belong to one event. Never fixed `ticket1/ticket2` slots.

```sh
python scripts/validate_trip.py /private/input/trip.json --assets-root /private/input
python scripts/build_app.py /private/input/trip.json --input-root /private/input --output /private/output
python scripts/verify_output.py /private/output/web
python -m http.server 8000 --directory /private/output/web
```

Default build removes bundled ticket bytes and offers local import. Use `--embed-private-tickets` only after explaining APK extraction/private sharing, or for clearly marked fictional tickets. Keep private originals separately.

Generator writes web, Android source, media ledger, checksums and build metadata. Download/vendor declared Leaflet/PDF.js versions with `scripts/fetch_vendor.py` before a full build (network required once). Their licenses stay attached. No CDN runtime dependency.

## Verify and preview

Validate input, generated output and real interaction: daily navigation, map markers/targets, document/page/traveler grouping, zoom, notes/image limit, check-ins, restart persistence, export/import, offline core, absent optional inputs, malicious text/file paths, and separate trip cache namespaces.

Complete first build, then open preview. Review home, every day/banner/timeline, photos/credits, map, tickets, records. Collect one batch of feedback. Fix/rebuild/retest, obtain explicit confirmation. No response means **preview pending**. Artifacts must match final approved preview.

## Delivery

Provide source, PWA, signed APK when verified, SHA256, media credits, installation/update instructions and verification report. Mention truly untested native/device cases. A missing native toolchain cannot be called a completed APK. Provide diagnostics and exact continuation command instead.

Generate `PHONE-GUIDE.md` for the actual target. Android instructions cover APK integrity check, trusted transfer, permission to install from the chosen source, install/update behavior, ticket import, offline/map boundaries, export/import, and uninstall-data loss. iPhone PWA instructions cover the HTTPS URL, Safari Share → Add to Home Screen, first online load, ticket import/storage eviction, export/import, and how updates appear. When both are selected, keep platform steps separate. Never tell an iPhone user to install an APK or imply an unbuilt IPA exists.

Use per-app signing keys outside Git, preserve package/signing/trip/storage IDs and increment versions for updates. Never create/push a public GitHub repository without user authorization.
