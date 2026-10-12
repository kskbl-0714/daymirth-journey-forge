"""Build, sign, and verify an APK; SDK fallback needs no Gradle."""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


def resolve(executable, explicit=None, required=True):
    found = explicit or shutil.which(executable)
    if found and Path(found).is_file():
        return Path(found).resolve()
    if required:
        raise SystemExit(executable + " not found; pass an explicit option or update PATH")
    return None


def sdk_tool(sdk, name):
    suffix = ".bat" if name in ("d8", "apksigner") else ".exe"
    path = sdk / "build-tools/35.0.0" / (name + (suffix if os.name == "nt" else ""))
    if not path.is_file():
        raise SystemExit("Android build tool missing: " + str(path))
    return path


def run(args, cwd=None, env=None, capture=False):
    # Never print credentials or the full signing command.
    print("Running", Path(str(args[0])).name, str(args[1]))
    return subprocess.run([str(a) for a in args], cwd=cwd, env=env, check=True,
                          capture_output=capture, text=capture, encoding="utf-8" if capture else None)


def android_config(android):
    text = (android / "app/build.gradle").read_text(encoding="utf-8")
    patterns = {"package": r"applicationId\s+'([^']+)'", "code": r"versionCode\s+(\d+)",
                "version": r"versionName\s+'([^']+)'", "namespace": r"namespace\s+'([^']+)'"}
    config = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if not match:
            raise SystemExit("Missing Android config: " + key)
        config[key] = match.group(1)
    return config


def verify_apk(source, android, sdk, env):
    run([sdk_tool(sdk, "apksigner"), "verify", "--verbose", source], env=env)
    run([sdk_tool(sdk, "zipalign"), "-c", "4", source], env=env)
    badging = run([sdk_tool(sdk, "aapt"), "dump", "badging", source], env=env, capture=True).stdout
    config = android_config(android)
    for token in ("name='" + config["package"] + "'", "versionCode='" + config["code"] + "'",
                  "versionName='" + config["version"] + "'", "targetSdkVersion:'35'"):
        if token not in badging:
            raise SystemExit("APK metadata mismatch: " + token)
    with zipfile.ZipFile(source) as archive:
        if archive.testzip() or not {"classes.dex", "AndroidManifest.xml", "assets/www/index.html"}.issubset(archive.namelist()):
            raise SystemExit("APK missing required entries or corrupt")
        assets = android / "app/src/main/assets"
        files = [p for p in assets.rglob("*") if p.is_file()]
        for path in files:
            name = "assets/" + path.relative_to(assets).as_posix()
            if name not in archive.namelist() or archive.read(name) != path.read_bytes():
                raise SystemExit("APK asset missing/changed: " + name)
        trip = json.loads(archive.read("assets/www/trip.json"))
        embedded = sum(bool(t.get("file")) for t in trip.get("tickets", []))
    print("Verified package", config["package"], "assets", len(files), "embedded ticket files", embedded)
    return {"packageId": config["package"], "versionCode": int(config["code"]),
            "versionName": config["version"], "assetsVerified": len(files), "embeddedTicketFiles": embedded,
            "signatureVerified": True, "alignmentVerified": True, "nativeDeviceTested": False}


def manual_build(android, sdk, java, env, release, output, staging_root=None):
    # Windows SDK resource tools fail on some Unicode input paths. Stage all their
    # inputs, including android.jar and signing keys, under an ASCII-only path.
    base = Path(staging_root) if staging_root else (Path(os.environ.get("PUBLIC", "C:/Users/Public")) if os.name == "nt" else Path(tempfile.gettempdir()))
    base = base.resolve()
    if not base.is_dir() or not str(base).isascii():
        raise SystemExit("Pass --staging-root pointing to an existing writable ASCII-only directory")
    config = android_config(android)
    jdk = java.parent
    extension = ".exe" if os.name == "nt" else ""
    for name in ("javac", "jar", "keytool"):
        resolve(name, str(jdk / (name + extension)))
    with tempfile.TemporaryDirectory(prefix="daymirth-build-", dir=base) as temporary:
        stage = Path(temporary)
        main = stage / "src"
        shutil.copytree(android / "app/src/main", main)
        android_jar = stage / "android.jar"
        shutil.copy2(sdk / "platforms/android-35/android.jar", android_jar)
        for name in ("gen", "classes", "dex"):
            (stage / name).mkdir()
        manifest_path = main / "AndroidManifest.xml"
        ET.register_namespace("android", "http://schemas.android.com/apk/res/android")
        manifest = ET.parse(manifest_path)
        # Native classes keep their namespace when the installable package differs.
        manifest.getroot().set("package", config["namespace"])
        manifest.write(manifest_path, encoding="utf-8", xml_declaration=True)
        compiled = stage / "resources.zip"
        unsigned = stage / "unsigned.apk"
        aligned = stage / "aligned.apk"
        signed = stage / "signed.apk"
        run([sdk_tool(sdk, "aapt2"), "compile", "--dir", main / "res", "-o", compiled], env=env)
        run([sdk_tool(sdk, "aapt2"), "link", "-o", unsigned, "-I", android_jar, "--manifest", manifest_path,
             "--min-sdk-version", "24", "--target-sdk-version", "35", "--version-code", config["code"],
             "--version-name", config["version"], "--rename-manifest-package", config["package"],
             "--custom-package", config["namespace"], "--java", stage / "gen", compiled], env=env)
        sources = list((main / "java").rglob("*.java")) + list((stage / "gen").rglob("*.java"))
        run([jdk / ("javac" + extension), "-encoding", "UTF-8", "-source", "8", "-target", "8",
             "-classpath", android_jar, "-d", stage / "classes", *sources], env=env)
        classes_jar = stage / "classes.jar"
        run([jdk / ("jar" + extension), "cf", classes_jar, "-C", stage / "classes", "."], env=env)
        run([sdk_tool(sdk, "d8"), "--lib", android_jar, "--min-api", "24", "--output", stage / "dex", classes_jar], env=env)
        # ZIP entry names must include assets/. Python supports UTF-8 media names
        # without aapt's filename limitations and puts dex at the archive root.
        with zipfile.ZipFile(unsigned, "a", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted((main / "assets").rglob("*")):
                if path.is_file():
                    archive.write(path, "assets/" + path.relative_to(main / "assets").as_posix())
            for path in (stage / "dex").glob("*.dex"):
                archive.write(path, path.name)
        run([sdk_tool(sdk, "zipalign"), "-f", "4", unsigned, aligned], env=env)
        signing_env = env.copy()
        if release:
            keystore = Path(env["DAYMIRTH_KEYSTORE"]).resolve()
            alias = env["DAYMIRTH_KEY_ALIAS"]
            signing_env["DAYMIRTH_KEY_PASSWORD"] = env.get("DAYMIRTH_KEY_PASSWORD") or env["DAYMIRTH_STORE_PASSWORD"]
        else:
            keystore = android.parent / "daymirth-demo-debug.keystore"
            alias = "daymirth-demo"
            signing_env["DAYMIRTH_STORE_PASSWORD"] = "daymirth-demo"
            signing_env["DAYMIRTH_KEY_PASSWORD"] = "daymirth-demo"
        stage_key = stage / "signing.keystore"
        if not keystore.is_file() and not release:
            run([jdk / ("keytool" + extension), "-genkeypair", "-keystore", stage_key,
                 "-storepass:env", "DAYMIRTH_STORE_PASSWORD", "-keypass:env", "DAYMIRTH_KEY_PASSWORD",
                 "-alias", alias, "-keyalg", "RSA", "-keysize", "2048", "-validity", "3650",
                 "-dname", "CN=DayMirth Demo, O=Local Demo, C=XX"], env=signing_env)
            shutil.copy2(stage_key, keystore)
        else:
            shutil.copy2(keystore, stage_key)
        run([sdk_tool(sdk, "apksigner"), "sign", "--ks", stage_key, "--ks-key-alias", alias,
             "--ks-pass", "env:DAYMIRTH_STORE_PASSWORD", "--key-pass", "env:DAYMIRTH_KEY_PASSWORD",
             "--out", signed, aligned], env=signing_env)
        report = verify_apk(signed, android, sdk, env)
        shutil.copy2(signed, output)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("android", type=Path)
    p.add_argument("--gradle")
    p.add_argument("--java")
    p.add_argument("--sdk")
    p.add_argument("--builder", choices=("auto", "gradle", "sdk"), default="auto")
    p.add_argument("--staging-root", type=Path)
    p.add_argument("--release", action="store_true")
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    android = a.android.resolve()
    java = resolve("java.exe" if os.name == "nt" else "java", a.java)
    sdk_value = a.sdk or os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if not sdk_value:
        raise SystemExit("Pass --sdk or set ANDROID_HOME")
    sdk = Path(sdk_value).resolve()
    if not (sdk / "platforms/android-35/android.jar").is_file():
        raise SystemExit("Android SDK platform 35 missing; pass --sdk")
    env = os.environ.copy()
    env.update(JAVA_HOME=str(java.parent.parent), ANDROID_HOME=str(sdk), ANDROID_SDK_ROOT=str(sdk))
    env["PATH"] = str(java.parent) + os.pathsep + env.get("PATH", "")
    if a.release:
        missing = [key for key in ("DAYMIRTH_KEYSTORE", "DAYMIRTH_STORE_PASSWORD", "DAYMIRTH_KEY_ALIAS") if not env.get(key)]
        if missing:
            raise SystemExit("Release signing variables missing: " + ", ".join(missing))
    variant = "release" if a.release else "debug"
    output = (a.output or android.parent / ("TripPocket-" + variant + ".apk")).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    gradle = resolve("gradle.bat" if os.name == "nt" else "gradle", a.gradle, required=a.builder == "gradle") if a.builder != "sdk" else None
    report = None
    if gradle:
        try:
            run([gradle, "--no-daemon", "assembleRelease" if a.release else "assembleDebug"], cwd=android, env=env)
            source = android / f"app/build/outputs/apk/{variant}/app-{variant}.apk"
            report = verify_apk(source, android, sdk, env)
            shutil.copy2(source, output)
        except (subprocess.CalledProcessError, OSError):
            if a.builder == "gradle":
                raise
            print("Gradle failed; trying the Android SDK fallback in an ASCII staging directory.")
    if report is None:
        report = manual_build(android, sdk, java, env, a.release, output, a.staging_root)
    digest = hashlib.sha256(output.read_bytes()).hexdigest().upper()
    output.with_suffix(output.suffix + ".sha256").write_text(digest + "  " + output.name + "\n", encoding="utf-8")
    report.update(sha256=digest, signing="release" if a.release else "demo-debug")
    output.with_suffix(output.suffix + ".report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(output)
    print("SHA256", digest)


if __name__ == "__main__":
    main()
