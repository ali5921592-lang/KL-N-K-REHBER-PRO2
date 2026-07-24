#!/usr/bin/env python3
"""
ensure-android-sdk.py
----------------------
KOK NEDEN ANALIZI:
Capacitor 6, android/app/build.gradle icinde compileSdk degerini DOGRUDAN
yazmaz; bunun yerine "rootProject.ext.compileSdkVersion" gibi bir referans
kullanir. Bu referansin gercek degeri android/variables.gradle dosyasinda
tanimlanir ve android/build.gradle (root) icindeki "apply from: variables.gradle"
satiriyla projeye dahil edilir.

"compileSdkVersion is not specified" hatasi, bu zincirdeki HERHANGI bir
halkanin (variables.gradle dosyasi, icindeki deger, veya apply satiri)
eksik/bozuk olmasi durumunda ortaya cikar.

Bu script, app/build.gradle dosyasina HICBIR SEKILDE DOKUNMADAN, yalnizca
variables.gradle dosyasini ve root build.gradle'daki apply satirini
GARANTI ALTINA alarak bu sorunu kokten cozer. Boylece build.gradle'in
kirilgan regex/sed islemleriyle bozulma riski tamamen ortadan kalkar.

Kullanim: python3 scripts/ensure-android-sdk.py
"""
import os
import re
import sys

ANDROID_DIR = "android"
ROOT_BUILD_GRADLE = os.path.join(ANDROID_DIR, "build.gradle")
VARIABLES_GRADLE = os.path.join(ANDROID_DIR, "variables.gradle")

# Guvenli, guncel varsayilan degerler.
COMPILE_SDK = 36
TARGET_SDK = 36
MIN_SDK = 23


def log(msg):
    print(f"[ensure-android-sdk] {msg}")


def ensure_variables_gradle():
    """variables.gradle dosyasini olustur/duzelt: compileSdkVersion,
    targetSdkVersion, minSdkVersion degerlerinin var ve DOGRU oldugunu garanti eder."""
    if not os.path.isdir(ANDROID_DIR):
        log(f"HATA: {ANDROID_DIR} klasoru bulunamadi. 'npx cap add android' calistirildi mi?")
        return False

    if os.path.exists(VARIABLES_GRADLE):
        with open(VARIABLES_GRADLE, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = "ext {\n}\n"
        log(f"UYARI: {VARIABLES_GRADLE} bulunamadi, sifirdan olusturuluyor.")

    def set_or_insert(content, key, value):
        pattern = rf"({key}\s*=\s*)\d+"
        if re.search(pattern, content):
            new_content = re.sub(pattern, rf"\g<1>{value}", content, count=1)
            log(f"{key} -> {value} olarak guncellendi (zaten mevcuttu).")
            return new_content
        else:
            # ext { ... } blogunun icine, ilk acilistan hemen sonra ekle.
            new_content, n = re.subn(
                r"(ext\s*\{)",
                rf"\1\n    {key} = {value}",
                content,
                count=1,
            )
            if n == 0:
                # ext {} blogu hic yoksa dosyanin basina yeni bir tane ekle.
                new_content = f"ext {{\n    {key} = {value}\n}}\n" + content
                log(f"UYARI: 'ext {{' blogu bulunamadi, yeni ext blogu olusturuldu.")
            log(f"{key} = {value} olarak eklendi (daha once yoktu).")
            return new_content

    content = set_or_insert(content, "compileSdkVersion", COMPILE_SDK)
    content = set_or_insert(content, "targetSdkVersion", TARGET_SDK)
    content = set_or_insert(content, "minSdkVersion", MIN_SDK)

    with open(VARIABLES_GRADLE, "w", encoding="utf-8") as f:
        f.write(content)

    log(f"variables.gradle garanti altina alindi: compileSdkVersion={COMPILE_SDK}, "
        f"targetSdkVersion={TARGET_SDK}, minSdkVersion={MIN_SDK}")
    return True


def ensure_variables_applied():
    """Root android/build.gradle dosyasinin variables.gradle'i gercekten
    projeye dahil ettigini (apply from: ...) dogrular; eksikse ekler."""
    if not os.path.exists(ROOT_BUILD_GRADLE):
        log(f"HATA: {ROOT_BUILD_GRADLE} bulunamadi.")
        return

    with open(ROOT_BUILD_GRADLE, "r", encoding="utf-8") as f:
        content = f.read()

    if "variables.gradle" in content:
        log("Root build.gradle zaten variables.gradle dosyasini dahil ediyor (apply from).")
        return

    # Dosyanin en sonuna guvenli sekilde ekle.
    content = content.rstrip() + '\n\napply from: "variables.gradle"\n'
    with open(ROOT_BUILD_GRADLE, "w", encoding="utf-8") as f:
        f.write(content)
    log("UYARI: Root build.gradle'da variables.gradle dahil edilmemisti, eklendi.")


def main():
    if not ensure_variables_gradle():
        return 1
    ensure_variables_applied()
    log("Android SDK versiyon zinciri (variables.gradle) dogrulandi/onarildi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
