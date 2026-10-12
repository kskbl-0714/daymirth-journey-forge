---
name: daymirth-journey-forge
description: Turn a trip itinerary, tickets, and images into a personalized installable travel app with daily routes, maps, navigation, ticket access, check-ins, notes, and reminders. Use for Android APKs, iPhone-installable PWAs, and interactive travel-app previews.
---

# DayMirth Journey Forge

将零散的旅行计划、预约信息、门票和图片，一站式制作成可安装、可离线使用的个性化旅行 App。整理每日路线，生成时间线与交互地图，提供地图跳转、票据打开、完成打卡、文字与图片备注、预约及注意事项提醒，并自动配置封面、景点实景图和每日趣味配图。

本 Skill 在**电脑端 Codex/Agent** 中执行，读取电脑上的行程与素材并完成搜索、生成、预览、测试和打包；最终产物才安装到 Android 或 iPhone。不要要求用户在手机上安装或运行本 Skill。

**使用建议：** 最好先确认每日行程、景点顺序、交通安排及已购票的预约时间，再调用本 Skill，让制作更加精准。行程可主动提供，也可来自当前对话上下文；未确定部分先整理成确认清单。

## Workflow

1. Read [workflow.md](references/workflow.md) and [trip-schema.md](references/trip-schema.md). Extract existing context and files before asking questions. Show obtained / needs confirmation / fallback if omitted. Ask missing questions together, without repeating answered questions.
2. Ask platform (Android/iPhone/both), language (Chinese/English/bilingual), embedded map, and external navigation separately. Ask App name when missing; default **TripPocket** if omitted. Do not ask theme color or subtitle; derive them automatically and change only on explicit user request during confirmation.
3. Preserve purchased reservation times; flag conflicts. Missing dates use Day 1/Day 2; missing times use periods/order. Do not invent bookings or coordinates. At least destination/travel intent is needed. Planning is optional when requested; this skill must not depend on another skill being installed.
4. Read [media-privacy.md](references/media-privacy.md). Proactively find verified, reusable real landmark photos. User images override. Disclose unsuccessful searches; use a supplied image, clearly labeled contextual illustration, or no-image layout. Optional missing images must not block completion.
5. Match daily fun banners to the day's theme. Explicit user mappings win, otherwise match the provided image pool and show date/image/reason. With no usable pool ask **AI generation or remove the section**. Never redistribute private memes without rights. Cover/icon: ask for user media or use a route-themed cover and generated icon.
6. Put private input/output outside this repository. Use Python 3.9+ with `requirements.txt`. Create `trip.json`, run `scripts/validate_trip.py`, then `scripts/build_app.py`. Read [platforms.md](references/platforms.md) before packaging. For Android, try `scripts/build_android.py`; its direct SDK fallback needs no Gradle and stages Windows inputs under an ASCII path. Tickets and travelers are dynamic lists with no fixed count (practical storage/device limits apply), including multi-person, multi-file, multi-page bookings.
7. Verify all days, navigation targets, ticket grouping/page controls, notes/images, check-ins, persistence, backup/import, missing-data layouts, and scoped offline cache. Use `scripts/verify_output.py` plus real interaction checks. Browser checks are not native-device proof.
8. Open the complete interactive preview **after the first build**, collect batched feedback, fix/rebuild/retest, then request user confirmation. Silence is not acceptance. Deliver only artifacts matching the latest approved preview.

## Required behavior

- Daily timelines and interactive map. Route lines show visit order; do not claim live traffic/shortest-path routing without an actual routing service.
- One tap external navigation; event-associated PDF/JPG/PNG tickets with traveler/document/page labels and recoverable errors.
- Persisted check-ins, text notes, and up to six compressed note images per event; JSON export/import backup. Stable event IDs survive renaming/reordering.
- In-app reservation/caution notices. Scheduled system notifications are an additional feature only when requested and supported.
- Graceful fallbacks for missing dates/times/tickets/images/coordinates; no empty banner space when disabled.

## Delivery boundaries

Android: signed APK, source, checksum and update/install instructions when toolchain succeeds. iPhone: installable HTTPS PWA by default; IPA requires macOS/Xcode/Apple signing. If native tools are absent, deliver validated PWA, native source, diagnostics, and continuation command; explicitly mark APK/IPA pending. Never imply an APK works on iPhone.

After production, generate a user-facing phone guide tailored to the selected/delivered platform: installation, first launch, home-screen placement, local ticket import, offline limits, notes/check-in backup and restore, privacy warning, and version updates. For both platforms, provide separate Android and iPhone sections. Mention only artifacts that were actually produced and tested.

Use fictional public demo data. Real tickets, QR codes, traveler details, private photos, keys, passwords and generated private builds stay outside GitHub. APK assets are extractable; explain private distribution before embedding tickets. PWA tickets should be locally imported or hosted with genuine private authentication. Do not publish remotely unless authorized.
