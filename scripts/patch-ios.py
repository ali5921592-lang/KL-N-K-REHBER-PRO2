#!/usr/bin/env python3
"""
patch-ios.py
------------
Capacitor `npx cap add ios` ile tazece uretilen native iOS projesini,
GitHub Actions icinde asagidaki sekilde otomatik duzenler:

  1) Privacy Manifest dosyasini (PrivacyInfo.xcprivacy) projeye ekler.
  2) ITSAppUsesNonExemptEncryption = false ekler.
  3) iPhone ve iPad icin uygun ekran yonu (orientation) destegini ayarlar.
  4) Gereksiz izin/aciklama anahtarlarini dogrular.
  5) Uygulamanin minimum iOS deployment target'ini 15.0'a ceker.

Bundle Identifier, versiyon ve build numarasi xcodebuild override'lariyla
workflow tarafinda verilir. Bu script yalnizca CI/CD tarafindan native ios/
klasoru uzerinde calisir.
"""
import os
import plistlib
import shutil
import sys

IOS_APP_DIR = os.path.join("ios", "App", "App")
INFO_PLIST_PATH = os.path.join(IOS_APP_DIR, "Info.plist")
PBXPROJ_PATH = os.path.join("ios", "App", "App.xcodeproj", "project.pbxproj")
PRIVACY_MANIFEST_SRC = os.path.join("ios-privacy", "PrivacyInfo.xcprivacy")
PRIVACY_MANIFEST_DST = os.path.join(IOS_APP_DIR, "PrivacyInfo.xcprivacy")
MIN_IOS_VERSION = "15.0"


def log(msg):
    print(f"[patch-ios] {msg}")


def copy_privacy_manifest():
    if not os.path.exists(PRIVACY_MANIFEST_SRC):
        log(f"UYARI: {PRIVACY_MANIFEST_SRC} bulunamadi, Privacy Manifest eklenemedi.")
        return
    if not os.path.isdir(IOS_APP_DIR):
        log(f"HATA: {IOS_APP_DIR} bulunamadi. 'npx cap add ios' calistirildi mi?")
        return
    shutil.copyfile(PRIVACY_MANIFEST_SRC, PRIVACY_MANIFEST_DST)
    log(f"Privacy Manifest kopyalandi: {PRIVACY_MANIFEST_DST}")
    log("NOT: Bu dosyanin Xcode projesine (.pbxproj) gercek bir referans olarak "
        "eklenmesi ayri bir adimda (scripts/add_privacy_manifest_to_xcodeproj.rb) "
        "yapilir; sadece diske kopyalamak Xcode'un onu .ipa icine paketlemesi "
        "icin yeterli degildir.")


def patch_info_plist():
    if not os.path.exists(INFO_PLIST_PATH):
        log(f"HATA: {INFO_PLIST_PATH} bulunamadi.")
        return
    with open(INFO_PLIST_PATH, "rb") as f:
        plist = plistlib.load(f)

    plist["ITSAppUsesNonExemptEncryption"] = False
    plist["UISupportedInterfaceOrientations"] = [
        "UIInterfaceOrientationPortrait",
        "UIInterfaceOrientationPortraitUpsideDown",
    ]
    plist["UISupportedInterfaceOrientations~ipad"] = [
        "UIInterfaceOrientationPortrait",
        "UIInterfaceOrientationPortraitUpsideDown",
        "UIInterfaceOrientationLandscapeLeft",
        "UIInterfaceOrientationLandscapeRight",
    ]
    plist.pop("UIRequiresFullScreen", None)

    with open(INFO_PLIST_PATH, "wb") as f:
        plistlib.dump(plist, f)
    log("Info.plist guncellendi: ITSAppUsesNonExemptEncryption=false, "
        "iPhone/iPad ekran yonleri, UIRequiresFullScreen kaldirildi.")


def patch_deployment_target():
    """Generated Capacitor target'in minimum iOS surumunu 15.0 yapar."""
    if not os.path.exists(PBXPROJ_PATH):
        raise FileNotFoundError(
            f"{PBXPROJ_PATH} bulunamadi; Capacitor iOS projesi olusturulmamis olabilir."
        )

    with open(PBXPROJ_PATH, "r", encoding="utf-8") as f:
        project = f.read()

    old_target = "IPHONEOS_DEPLOYMENT_TARGET = 13.0;"
    new_target = f"IPHONEOS_DEPLOYMENT_TARGET = {MIN_IOS_VERSION};"
    replaced = project.count(old_target)
    if replaced:
        project = project.replace(old_target, new_target)
        log(f"iOS deployment target {replaced} ayarda {MIN_IOS_VERSION} olarak guncellendi.")
    elif new_target in project:
        log(f"iOS deployment target zaten {MIN_IOS_VERSION}.")
    else:
        raise RuntimeError(
            "IPHONEOS_DEPLOYMENT_TARGET bulunamadi; minimum iOS surumu dogrulanamadi."
        )

    if new_target not in project:
        raise RuntimeError("iOS deployment target patch sonrasi dogrulanamadi.")

    with open(PBXPROJ_PATH, "w", encoding="utf-8", newline="") as f:
        f.write(project)
    log("Xcode project deployment target dogrulamasi tamamlandi; IAP capability eklenmedi.")


def verify_no_unnecessary_permissions():
    if not os.path.exists(INFO_PLIST_PATH):
        return
    with open(INFO_PLIST_PATH, "rb") as f:
        plist = plistlib.load(f)
    permission_keys = [k for k in plist.keys() if k.startswith("NS") and k.endswith("UsageDescription")]
    if permission_keys:
        log(f"UYARI: Info.plist'te izin aciklama anahtarlari bulundu: {permission_keys}. "
            "Uygulama bu izinleri kullanmiyorsa bu anahtarlar kaldirilmalidir.")
    else:
        log("Dogrulandi: Info.plist'te gereksiz izin aciklamasi (kamera/konum/mikrofon vb.) yok.")


def main():
    copy_privacy_manifest()
    patch_info_plist()
    patch_deployment_target()
    verify_no_unnecessary_permissions()
    log("iOS proje duzenlemeleri tamamlandi.")


if __name__ == "__main__":
    sys.exit(main())
