#!/usr/bin/env python3
"""
generate-export-options.py
----------------------------
xcodebuild -exportArchive icin gereken exportOptions.plist dosyasini
ortam degiskenlerinden (env vars) okuyarak guvenli sekilde uretir.

Bu script, GitHub Actions workflow'u icine gomulu bir Python heredoc
kullanmak yerine ayri bir dosya olarak tutulur; boylece YAML girinti
(indentation) sorunlarindan etkilenmez ve test edilebilir/okunabilir olur.

Gerekli ortam degiskenleri:
  IOS_TEAM_ID       - Apple Developer Team ID
  IOS_PROFILE_NAME  - Provisioning profile adi (App Store Connect'te tanimli)
  BUNDLE_ID         - Uygulamanin bundle identifier'i
"""
import os
import plistlib
import sys


def main():
    team_id = os.environ.get("IOS_TEAM_ID", "")
    profile_name = os.environ.get("IOS_PROFILE_NAME", "")
    bundle_id = os.environ.get("BUNDLE_ID", "")

    missing = [name for name, val in [
        ("IOS_TEAM_ID", team_id),
        ("IOS_PROFILE_NAME", profile_name),
        ("BUNDLE_ID", bundle_id),
    ] if not val]
    if missing:
        print(f"[generate-export-options] HATA: eksik ortam degiskeni: {missing}")
        return 1

    opts = {
        "method": "app-store",
        "teamID": team_id,
        "signingStyle": "manual",
        "provisioningProfiles": {
            bundle_id: profile_name,
        },
        "uploadSymbols": True,
        "compileBitcode": False,
    }
    with open("exportOptions.plist", "wb") as f:
        plistlib.dump(opts, f)
    print("[generate-export-options] exportOptions.plist created:", opts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
