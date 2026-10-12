# -*- coding: utf-8 -*-
"""Generate a self-contained PWA and Android source from validated trip JSON."""
import argparse
import copy
import hashlib
import html
import json
import re
import shutil
from pathlib import Path
from validate_trip import validate, local_path

SKILL = Path(__file__).resolve().parents[1]


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def generate(trip_path, input_root, output, embed=False):
    data = json.loads(Path(trip_path).read_text(encoding="utf-8-sig"))
    errors, warnings = validate(data, input_root)
    if errors:
        raise ValueError("\n".join(errors))
    output = Path(output).resolve()
    if output == Path(input_root).resolve() or output.is_relative_to(SKILL):
        raise ValueError("Use an output outside the public Skill and input directories")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output must be new/empty; choose a fresh version directory")
    vendor = SKILL / "assets/web/vendor"
    for name in ("leaflet.js", "pdf.min.js", "pdf.worker.min.js", "vendor-lock.json"):
        if not (vendor / name).is_file():
            raise ValueError("Missing vendored runtime; run scripts/fetch_vendor.py first")
    web = output / "web"
    shutil.copytree(SKILL / "assets/web", web)
    result = copy.deepcopy(data)
    app = result["app"]
    app.setdefault("name", "TripPocket")
    app.setdefault("language", "zh")
    app.setdefault("subtitle", " · ".join(d.get("title", d.get("label", "")) for d in result["days"][:3]))
    app.setdefault("theme", {"primary": "#146C63"})
    result.setdefault("settings", {"embeddedMap": "osm", "navigation": "system", "privacy": "private"})
    result.setdefault("tickets", [])
    result.setdefault("travelers", [])
    for t in result["tickets"]:
        if not embed or t.get("deliveryMode") == "local-import":
            t.pop("file", None)
            t["deliveryMode"] = "local-import"
        elif t.get("file"):
            source = local_path(t["file"], "tickets", input_root)
            t["file"] = "tickets/" + t["id"] + source.suffix.lower()
            target = web / t["file"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    files = [app.get("cover"), app.get("icon")]
    for day in result["days"]:
        files.append(day.get("banner"))
        files.extend(e.get("photo") for e in day["events"])
    for name in set(filter(None, files)):
        target = web / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path(name, "media", input_root), target)
    make_icons(web, app, input_root)
    write_json(web / "trip.json", result)
    title = html.escape(app["name"])
    index = (web / "index.html").read_text(encoding="utf-8").replace("__APP_NAME__", title).replace("__LANG__", "zh-CN" if app["language"] == "zh" else "en")
    (web / "index.html").write_text(index, encoding="utf-8")
    write_json(web / "manifest.webmanifest", {"id": "./?trip=" + result["tripId"], "name": app["name"], "short_name": app["name"][:18], "start_url": "./", "scope": "./", "display": "standalone", "background_color": "#fffaf2", "theme_color": app["theme"].get("primary", "#146C63"), "icons": [{"src": f"icons/icon-{n}.png", "sizes": f"{n}x{n}", "type": "image/png", "purpose": "any maskable"} for n in (192, 512)]})
    assets = [p.relative_to(web).as_posix() for p in web.rglob("*") if p.is_file() and p.name not in ("sw.js", "cache-config.js")]
    revision = hashlib.sha256(b"".join((web / p).read_bytes() for p in sorted(assets))).hexdigest()[:16]
    (web / "cache-config.js").write_text("self.TRIP_CACHE=" + json.dumps({"namespace": "daymirth-" + result["tripId"] + "-", "revision": revision, "assets": assets}) + ";\n", encoding="utf-8")
    android = output / "android"
    shutil.copytree(SKILL / "assets/android", android)
    shutil.copytree(web, android / "app/src/main/assets/www")
    package = data.get("android", {}).get("packageId", "com.daymirth.trip." + data["tripId"].replace("-", ""))
    if not re.fullmatch(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*){2,}", package):
        raise ValueError("Invalid Android package ID")
    config = data.get("android", {})
    gradle = (android / "app/build.gradle").read_text()
    gradle = gradle.replace("__PACKAGE_ID__", package).replace("__VERSION_CODE__", str(int(config.get("versionCode", 1)))).replace("__VERSION_NAME__", str(config.get("versionName", "1.0")))
    (android / "app/build.gradle").write_text(gradle, encoding="utf-8")
    resources = android / "app/src/main/res/values"
    resources.mkdir(parents=True, exist_ok=True)
    # Android escapes apostrophes and treats leading @/? specially.
    label = html.escape(app["name"].replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"'))
    (resources / "strings.xml").write_text('<resources><string name="app_name">"' + label + '"</string></resources>\n', encoding="utf-8")
    icon_resource = android / "app/src/main/res/mipmap-hdpi/ic_launcher.png"
    icon_resource.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(web / "icons/icon-192.png", icon_resource)
    write_json(output / "build-info.json", {"tripId": result["tripId"], "appName": app["name"], "packageId": package, "embeddedTickets": embed, "warnings": warnings, "previewStatus": "pending", "revision": revision})
    write_json(output / "media-credits.json", result.get("mediaCredits", []))
    platforms = result.get("settings", {}).get("platforms", ["pwa"])
    chinese_guide = app.get("language") in ("zh", "bilingual")
    guide = (["# " + app["name"] + " 手机使用说明", "", "仅使用本次构建实际交付的文件。预览状态：**等待用户明确确认**。", ""] if chinese_guide else ["# " + app["name"] + " phone guide", "", "Use only the artifact delivered with this build. Preview status: **pending explicit user confirmation**.", ""])
    if "android" in platforms:
        guide += (["## Android", "", "1. 将 APK 的 SHA-256 与交付的校验值核对，再通过可信的私人渠道传到手机。", "2. 打开 APK；若系统询问，仅临时允许当前文件管理器或浏览器安装未知应用，安装后关闭该权限。", "3. 首次联网启动；在对应行程卡片中导入未内置的票据，并保留原始票据文件。", "4. 行程、打卡、备注和已导入票据可在本机离线使用；地图瓦片与外部导航需要网络。", "5. 定期从菜单导出记录 JSON；在同一行程中导入它可恢复打卡和备注。", "6. 更新版必须沿用相同包名与签名密钥并提高版本号。兼容更新会保留数据；卸载或清除 App 数据会删除本地记录与导入票据。", "", "APK 内置资源可被提取，包含私人票据的版本只能私下交付。未在 Android 真机或模拟器测试前，设备交互仍标记为未验证。", ""] if chinese_guide else ["## Android", "", "1. Compare the APK SHA-256 with the delivered checksum, then transfer it through a trusted private channel.", "2. Open the APK. If Android asks, allow installation from this source only for the file manager/browser you used; turn that permission off afterward.", "3. Launch the App once online. Import any non-bundled ticket from its event card. Keep the original ticket files.", "4. Itinerary, check-ins, notes and imported tickets work locally. Map tiles and external navigation need a connection.", "5. Use the menu to export records regularly. Import that JSON to restore check-ins and notes for the same trip.", "6. Updates must use the same package/signing key and a higher version. Installing a compatible update keeps data; uninstalling or clearing App data removes local records and imported tickets.", "", "Bundled APK assets can be extracted. Share a private-ticket build only with intended recipients. Device interactions remain unverified until tested on an Android device/emulator.", ""])
    if "iphone" in platforms or "pwa" in platforms:
        guide += (["## iPhone / 可安装网页 App", "", "1. 联网时在 Safari 打开交付的 HTTPS 地址，核对名称和封面，再点“分享”→“添加到主屏幕”。", "2. 联网打开一次新图标以缓存核心文件；在行程卡片中本地导入票据并保留原件。", "3. 缓存后，行程、打卡、备注和导入票据可离线使用；地图瓦片和外部导航需要网络。", "4. 定期导出记录 JSON，并在同一行程中导入恢复。iOS 可能清理浏览器存储；删除主屏幕 App 或网站数据会移除本地记录和票据。", "5. 联网重新打开 HTTPS App 可接收已发布更新。PWA 不是 IPA，也不通过 App Store 安装。", "", "私人行程必须使用私人托管。未在目标 iPhone 测试前，Safari 与主屏幕行为仍标记为未验证。", ""] if chinese_guide else ["## iPhone / installable web app", "", "1. Open the delivered HTTPS address in Safari while online. Confirm the name and cover, then use Share -> Add to Home Screen.", "2. Open the new home-screen icon once while online so core files can be cached. Import tickets locally from their event cards and retain the originals.", "3. Itinerary, check-ins, notes and imported tickets can work offline after caching. Map tiles and external navigation require a connection.", "4. Export records regularly and import the JSON to restore this trip. iOS may evict browser storage; deleting the home-screen app/site data removes local records and tickets.", "5. Reopen the HTTPS app online to receive a published update. A PWA is not an IPA and does not install through the App Store.", "", "Hosting must remain private when trip data is private. Safari/home-screen behavior remains unverified until tested on the target iPhone.", ""])
    (output / "PHONE-GUIDE.md").write_text("\n".join(guide), encoding="utf-8")
    checksums = {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in output.rglob("*") if p.is_file()}
    write_json(output / "SHA256.json", checksums)
    return output


def make_icons(web, app, input_root):
    from PIL import Image, ImageDraw
    icon_dir = web / "icons"
    icon_dir.mkdir(exist_ok=True)
    for size in (192, 512):
        if app.get("icon"):
            source = Image.open(local_path(app["icon"], "media", input_root)).convert("RGB")
            from PIL import ImageOps
            image = ImageOps.fit(source, (size, size))
        else:
            image = Image.new("RGB", (size, size), app["theme"].get("primary", "#146C63"))
            draw = ImageDraw.Draw(image)
            m = size // 4
            draw.rounded_rectangle((m, m, size-m, size-m), radius=size//12, fill="#fffaf2")
            draw.line((m+size//12, m+size//8, size//2, size-m-size//8, size-m-size//12, m+size//8), fill=app["theme"].get("primary", "#146C63"), width=size//24)
        image.save(icon_dir / f"icon-{size}.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trip", type=Path)
    parser.add_argument("--input-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--embed-private-tickets", action="store_true", help="Private/fictional build only; APK assets can be extracted")
    args = parser.parse_args()
    print(generate(args.trip, args.input_root or args.trip.parent, args.output, args.embed_private_tickets))


if __name__ == "__main__":
    main()
