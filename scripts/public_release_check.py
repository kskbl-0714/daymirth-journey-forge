"""Fail closed on common sensitive/public-repository mistakes."""
import argparse
import re
import json
import hashlib
from pathlib import Path

ALLOWED_BINARY={".png",".jpg",".jpeg",".webp",".pdf"}
DENY_EXT={".jks",".keystore",".p12",".pem",".key",".apk",".aab"}
DENY_PARTS={"build",".gradle","private-input","private-output","real-tickets","chrome-profile","browser-profile"}
PATTERNS={"private key":rb"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY","password assignment":rb"(?i)(?:password|storePassword)\s*[:=]\s*['\"][^'\"\r\n]+","email":rb"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b","phone-like personal number":rb"(?<![A-Za-z0-9])(?:\+?\d[\s().-]+){4,}\d(?![A-Za-z0-9])"}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("root",type=Path);a=p.parse_args();root=a.root.resolve();errors=[]
    vendor=root/"assets/web/vendor";lock=json.loads((vendor/"vendor-lock.json").read_text()) if (vendor/"vendor-lock.json").is_file() else {}
    for path in root.rglob("*"):
        if not path.is_file():continue
        rel=path.relative_to(root);parts={part.lower() for part in rel.parts}
        if ".git" in parts or "__pycache__" in parts:continue
        if path.is_relative_to(vendor) and path.name!="vendor-lock.json":
            name=path.relative_to(vendor).as_posix()
            if name not in lock or hashlib.sha256(path.read_bytes()).hexdigest()!=lock[name]["sha256"]:errors.append(f"Unverified third-party file: {rel}")
            continue
        if path.suffix.lower() in DENY_EXT:errors.append(f"Forbidden extension: {rel}")
        if parts&{p.lower() for p in DENY_PARTS}:errors.append(f"Forbidden path: {rel}")
        if path.stat().st_size>5_000_000:errors.append(f"Large file needs manual review: {rel}")
        data=path.read_bytes() if path.suffix.lower() not in ALLOWED_BINARY else b""
        for label,pattern in PATTERNS.items():
            if re.search(pattern,data):errors.append(f"Potential {label}: {rel}")
    for e in errors:print("ERROR:",e)
    print(f"{len(errors)} potential release issues")
    return bool(errors)
if __name__=="__main__":raise SystemExit(main())
