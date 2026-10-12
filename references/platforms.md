# Platforms and maps

Embedded map is distinct from external navigation. Default local Leaflet + OSM, no API key. OSM attribution visible; do not bulk cache tiles. Lines are ordered schematic links. Navigation system chooser/Apple/Google/Amap. Amap query uses text unless verified GCJ-02 data/conversion is configured; never pass WGS84 as GCJ-02. Other embedded providers conditional on valid keys/licenses/adapter. Maps/navigation require network.

## PWA

HTTPS initial installation/cache required (localhost allowed for development). iPhone: Safari Share → Add to Home Screen. Core itinerary/notes/check-ins and imported tickets work offline after caching; maps/navigation do not. OS/browser storage may be evicted; export/import records and retain original tickets. PDF.js and worker vendored locally. Native IPA conditional on macOS/Xcode/Apple signing/provisioning; Windows cannot promise it.

## Android

Standard Android source, minSDK 24, target/compile 35. Discover JDK/SDK/Gradle via environment or explicit flags; no machine paths in repository. Use `scripts/build_android.py` with JDK17, SDK35 and build-tools 35.0.0. `--builder auto` uses Gradle when found, then falls back to the direct Android SDK pipeline; `--builder sdk` skips Gradle. On Windows the fallback copies source, `android.jar`, and the signing key into a temporary ASCII-only folder (normally `C:\Users\Public`) before aapt2/javac/d8/zipalign/apksigner, avoiding Unicode-path failures. The temporary directory is removed after the verified APK is copied out. Use `--staging-root` if that default is unavailable.

```powershell
python scripts/build_android.py <generated-output>/android --builder sdk --java <jdk17>/bin/java.exe --sdk <android-sdk> --output <private-output>/TripPocket-debug.apk
```

The script creates a demo-debug signed APK or a release APK using `DAYMIRTH_KEYSTORE`, `DAYMIRTH_STORE_PASSWORD`, `DAYMIRTH_KEY_ALIAS`, and optional `DAYMIRTH_KEY_PASSWORD`. Password values are read through environment variables and not printed. It verifies signature, 4-byte alignment, package/version, `classes.dex`, all bundled web assets and ticket count, then writes `.sha256` and `.report.json`. Production keys never belong in the public repository. Preserve package/key/storage IDs and increment versions when updating.

Native WebView note-image chooser and constrained ticket bridge; PDF/image viewer has documents/pages, prev/next, swipes, zoom, error handling. Do not treat desktop web preview as native proof. Verify on emulator/device when available; otherwise disclose untested native interaction. Native app origin is trusted local assets; bridge cannot browse arbitrary private files.

Missing tools: deliver validated PWA+Android source+diagnostics+continuation command, mark APK pending. Successful package: signature verification, SHA256, install/update instructions; distinguish demo debug from release signing.

## Tailored phone handoff

After the approved build, produce instructions matching only delivered artifacts. Include: install/add-to-home-screen; first online launch; ticket local import; what works offline; maps/navigation online requirement; records backup/import; browser-storage/APK-extraction privacy; update method; and uninstall/clear-data consequences. Separate Android and iPhone procedures when both are requested, and identify any emulator/device step not tested.
