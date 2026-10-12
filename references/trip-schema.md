# Data contract (UTF-8 JSON, schemaVersion 1)

See `examples/fictional-trip/trip.json` for a runnable fictional example.

Root: `schemaVersion: 1`, stable ASCII `tripId`, `app`, nonempty `days`. IDs use lowercase letters/digits/hyphens. Unicode text is supported everywhere. `app.name` defaults TripPocket; `app.language` is zh/en/bilingual. `app.subtitle`, `cover`, `icon`, `theme.primary` (#RRGGBB) optional. Images are local relative paths below media/. Settings: embeddedMap osm/none; navigation system/google/apple/amap; privacy private/public-demo. Other embedded providers require replacing the adapter with a licensed/tested provider and correct coordinate system.

Travelers: array of `{id, displayName}` with no fixed count, optional. Do not collect passport/payment details.

Days: `{id, label, title, date?, banner?, bannerAlt?, bannerReason?, notices:[], events:[]}`. Real dates use ISO YYYY-MM-DD; otherwise omit. Event order is authoritative.

Events: `{id, title, time?, period?, kind?, description?, address?, coordinates?:{lat,lng}, durationMinutes?, photo?, photoAlt?, photoLabel?, notices:[], navigationQuery?}`. Time can be a range/string; period morning/afternoon/evening. Unverified coordinates omitted, not guessed. `photoLabel` distinguishes contextual/AI art from verified photos. Stable event IDs survive updates.

Tickets: array of `{id,title,originalName?,file?,mimeType,eventIds:[],travelerIds:[],pageCount?,notes?,deliveryMode?}`. MIME types application/pdf, image/jpeg, image/png. Local file below tickets/, ASCII basename. Any number of tickets/travelers; a file may cover many travelers/events, many files may link one event, multi-page PDF stays one record. Public/local-import build keeps metadata but not private bytes; app imports matching file on device. Preserve originals outside repo.

Media ledger: `mediaCredits` array `{file,subject?,sourceUrl?,author,license,licenseUrl?,verifiedRealPlace:boolean}`. Every used cover/banner/photo/icon needs a ledger entry. User assets: private-use license unless public rights provided. AI/contextual illustrations: verifiedRealPlace false, visible honest photoLabel. Third-party photos: author/source/license plus verified identity.

Optional `android`: `{packageId,versionCode,versionName}`. Package defaults com.daymirth.trip.<normalizedTripId>; keep it stable on updates. A private existing app's package/signing identity must be explicitly preserved, never copied into a public demo.
