#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

FILES = [
    "node_modules/@capacitor-community/admob/ios/Sources/AdMobPlugin/Consent/ConsentExecutor.swift",
    "node_modules/@capacitor-community/admob/ios/Sources/AdMobPlugin/Helper/AuthorizationStatusEnum.swift",
]

REPLACEMENTS = {
    "UMPConsentInformation.sharedInstance": "ConsentInformation.shared",
    "UMPConsentStatus": "ConsentStatus",
    "UMPFormStatus": "FormStatus",
    "UMPConsentForm": "ConsentForm",
    "UMPRequestParameters": "RequestParameters",
    "UMPDebugSettings": "DebugSettings",
    "UMPDebugGeography": "DebugGeography",
}

for file in FILES:
    if not os.path.exists(file):
        print(f"[patch-admob] Bulunamadı: {file}")
        continue

    with open(file, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    for old, new in REPLACEMENTS.items():
        content = content.replace(old, new)

    if content != original:
        with open(file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[patch-admob] Güncellendi: {file}")
    else:
        print(f"[patch-admob] Değişiklik gerekmiyor: {file}")

print("[patch-admob] Tamamlandı.")
