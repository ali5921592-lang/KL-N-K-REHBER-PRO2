#!/usr/bin/env python3
"""
patch-ads.py
------------
ad-config.json dosyasindaki AdMob reklam kimliklerini TEK KAYNAK olarak
kullanip, asagidaki 3 yere otomatik olarak isler:

  1) android/app/src/main/AndroidManifest.xml
     -> com.google.android.gms.ads.APPLICATION_ID meta-data etiketi eklenir/guncellenir.

  2) ios/App/App/Info.plist
     -> GADApplicationIdentifier anahtari eklenir/guncellenir.

  3) www/index.html icindeki mobil kopru scriptinin AD_CONFIG bolumu
     -> AD_CONFIG_START / AD_CONFIG_END yorum isaretleri arasindaki JS
        objesi, ad-config.json'daki gercek degerlerle degistirilir.

Bu sayede kullanici yalnizca ad-config.json dosyasini duzenleyip commit
ederek, bir sonraki CI derlemesinde gercek reklam kimliklerinin projenin
her yerine otomatik yayilmasini saglar ("tek dosyadan degistirme").

Kullanim: python3 scripts/patch-ads.py
"""
import json
import os
import re
import sys

AD_CONFIG_PATH = "ad-config.json"
ANDROID_MANIFEST = os.path.join("android", "app", "src", "main", "AndroidManifest.xml")
IOS_INFO_PLIST = os.path.join("ios", "App", "App", "Info.plist")
WWW_INDEX = os.path.join("www", "index.html")


def log(msg):
    print(f"[patch-ads] {msg}")


def load_ad_config():
    if not os.path.exists(AD_CONFIG_PATH):
        log(f"UYARI: {AD_CONFIG_PATH} bulunamadi, reklam yapilandirmasi atlaniyor.")
        return None
    with open(AD_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def patch_android_manifest(cfg):
    if not os.path.exists(ANDROID_MANIFEST):
        log(f"UYARI: {ANDROID_MANIFEST} bulunamadi (Android platformu henuz eklenmemis olabilir).")
        return
    app_id = cfg["android"]["appId"]
    with open(ANDROID_MANIFEST, "r", encoding="utf-8") as f:
        content = f.read()

    meta_tag = (
        f'<meta-data\n'
        f'            android:name="com.google.android.gms.ads.APPLICATION_ID"\n'
        f'            android:value="{app_id}"/>'
    )

    if "com.google.android.gms.ads.APPLICATION_ID" in content:
        content = re.sub(
            r'<meta-data\s+android:name="com\.google\.android\.gms\.ads\.APPLICATION_ID"\s+android:value="[^"]*"\s*/>',
            meta_tag,
            content,
        )
        log("AdMob APPLICATION_ID meta-data guncellendi.")
    else:
        content, n = re.subn(r"(<application[^>]*>)", r"\1\n        " + meta_tag, content, count=1)
        if n == 0:
            log("HATA: <application> etiketi bulunamadi, AdMob APPLICATION_ID eklenemedi.")
            return
        log("AdMob APPLICATION_ID meta-data eklendi.")

    with open(ANDROID_MANIFEST, "w", encoding="utf-8") as f:
        f.write(content)


def patch_ios_info_plist(cfg):
    if not os.path.exists(IOS_INFO_PLIST):
        log(f"UYARI: {IOS_INFO_PLIST} bulunamadi (iOS platformu henuz eklenmemis olabilir).")
        return
    import plistlib

    app_id = cfg["ios"]["appId"]
    with open(IOS_INFO_PLIST, "rb") as f:
        plist = plistlib.load(f)

    plist["GADApplicationIdentifier"] = app_id
    # Google Mobile Ads SDK 8+ icin SKAdNetwork tanimlayicilari (Apple ATT/SKAdNetwork uyumu icin onerilir).
    existing = plist.get("SKAdNetworkItems", [])
    known_ids = {item.get("SKAdNetworkIdentifier") for item in existing if isinstance(item, dict)}
    google_skadnetwork_ids = [
        "cstr6suwn9.skadnetwork", "4fzdc2evr5.skadnetwork", "2u9pt9hc89.skadnetwork",
        "3sh42y64q3.skadnetwork", "f38h382jlk.skadnetwork", "hs6bdukanm.skadnetwork",
    ]
    for skid in google_skadnetwork_ids:
        if skid not in known_ids:
            existing.append({"SKAdNetworkIdentifier": skid})
    plist["SKAdNetworkItems"] = existing

    with open(IOS_INFO_PLIST, "wb") as f:
        plistlib.dump(plist, f)
    log("iOS Info.plist GADApplicationIdentifier ve SKAdNetworkItems guncellendi.")


def patch_web_app(cfg):
    if not os.path.exists(WWW_INDEX):
        log(f"HATA: {WWW_INDEX} bulunamadi.")
        return
    with open(WWW_INDEX, "r", encoding="utf-8") as f:
        content = f.read()

    # JSON verilerini dogrudan JS obje literaline donusturerek yaz.
    test_mode = cfg.get("testMode", True)
    test_mode_js = "true" if test_mode else "false"
    android_json = json.dumps(cfg["android"], ensure_ascii=False)
    ios_json = json.dumps(cfg["ios"], ensure_ascii=False)
    replacement_block = (
        "    var AD_CONFIG = {\n"
        f"      testMode: {test_mode_js},\n"
        f"      android: {android_json},\n"
        f"      ios: {ios_json}\n"
        "    };"
    )

    pattern = re.compile(
        r"// ---- AD_CONFIG_START.*?// ---- AD_CONFIG_END ----",
        re.DOTALL,
    )
    if not pattern.search(content):
        log("UYARI: AD_CONFIG_START/END isaretleri bulunamadi, web uygulamasi reklam kimlikleri guncellenmedi.")
        return

    new_marked_block = (
        "// ---- AD_CONFIG_START (scripts/patch-ads.py bu blogu ad-config.json'dan uretir) ----\n"
        + replacement_block
        + "\n    // ---- AD_CONFIG_END ----"
    )
    content = pattern.sub(lambda m: new_marked_block, content, count=1)

    with open(WWW_INDEX, "w", encoding="utf-8") as f:
        f.write(content)
    log("Web uygulamasindaki AD_CONFIG bolumu ad-config.json degerleriyle guncellendi.")


def main():
    cfg = load_ad_config()
    if cfg is None:
        return 0
    patch_android_manifest(cfg)
    patch_ios_info_plist(cfg)
    patch_web_app(cfg)
    log("Reklam yapilandirmasi tamamlandi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
