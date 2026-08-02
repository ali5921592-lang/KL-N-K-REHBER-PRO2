#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch-podfile.py
----------------
Capacitor'in urettigi ios/App/Podfile dosyasina bir post_install kancasi
ekler ve TUM Pod hedeflerinde kod imzalamayi kapatir.

NEDEN GEREKLI?
CI ortamindaki imzalama kimligi yalnizca ana uygulama hedefi icin
gecerlidir. CocoaPods ile gelen bagimliliklar (AdMob, Firebase,
cordova-plugin-purchase gibi) ayri hedefler olarak derlenir ve Xcode
bunlari da imzalamaya calisirsa arsivleme su hatayla coker:

    "No signing certificate iOS Development found"
    "Signing for <Pod> requires a development team"

Kod imzasi yalnizca ana uygulamada gerekli oldugu icin Pod hedeflerinde
imzalamayi kapatmak hem guvenli hem de Apple tarafindan kabul edilen
standart yaklasimdir.

AYRICA: CocoaPods yalnizca TEK bir post_install blogu kabul eder.
Capacitor kendi Podfile'inda zaten bir post_install tanimlar
(assertDeploymentTarget). Bu yuzden yeni bir blok EKLEMEK yerine,
var olan blogun icine ekleme yapariz.

Kullanim: python3 scripts/patch-podfile.py
"""
import os
import re
import sys

PODFILE = os.path.join("ios", "App", "Podfile")

MARKER = "# --- CI: Pod hedeflerinde kod imzalamayi kapat ---"
PIN_MARKER = "# --- CI: Bagimlilik surum sabitleme ---"

# ---------------------------------------------------------------------------
# NEDEN SURUM SABITLEME GEREKLI?
#
# @capacitor-community/admob eklentisinin iOS kodu, Google'in User Messaging
# Platform (UMP) SDK'sinin ESKI Swift isimlerini kullanir:
#     UMPConsentInformation.sharedInstance   /   UMPConsentStatus
#
# Google, UMP 3.0.0 (24 Mart 2025) ile Swift API isimlerini degistirdi:
#     ConsentInformation.shared              /   ConsentStatus
#
# Eklentinin podspec dosyasi UMP surumunu SABITLEMEDIGI icin CocoaPods her
# derlemede en guncel surumu (3.x) ceker ve derleme su hatalarla coker:
#     'sharedInstance' has been renamed to 'shared'
#     'UMPConsentStatus' has been renamed to 'ConsentStatus'
#
# Bu, derlemenin "dun calisiyordu bugun calismiyor" davranisinin da
# sebebidir: kodda hicbir sey degismese bile Google yeni surum yayinladiginda
# derleme kirilir.
#
# COZUM: UMP'yi eklentinin destekledigi 2.x serisine sabitlemek.
# '~> 2.0' ifadesi 2.x serisinin en guncel surumunu secer, 3.0'a gecmez.
# ---------------------------------------------------------------------------
PINNED_PODS = """
  """ + PIN_MARKER + """
  # UMP 3.x, Swift API isimlerini degistirdigi icin @capacitor-community/admob
  # ile uyumsuz. 2.x serisine sabitliyoruz. Ayrinti icin bu dosyanin basina bakin.
  pod 'GoogleUserMessagingPlatform', '~> 2.0'
"""

SIGNING_SNIPPET = """
  """ + MARKER + """
  installer.pods_project.targets.each do |target|
    target.build_configurations.each do |config|
      config.build_settings['CODE_SIGNING_ALLOWED'] = 'NO'
      config.build_settings['CODE_SIGNING_REQUIRED'] = 'NO'
      config.build_settings['CODE_SIGNING_IDENTITY'] = ''
      config.build_settings['EXPANDED_CODE_SIGN_IDENTITY'] = ''
      config.build_settings['CODE_SIGN_ENTITLEMENTS'] = ''
      config.build_settings['DEVELOPMENT_TEAM'] = ''
      config.build_settings['PROVISIONING_PROFILE_SPECIFIER'] = ''
    end
  end
  installer.pods_project.build_configurations.each do |config|
    config.build_settings['CODE_SIGNING_ALLOWED'] = 'NO'
    config.build_settings['CODE_SIGNING_REQUIRED'] = 'NO'
  end
"""

NEW_POST_INSTALL = """
post_install do |installer|
""" + SIGNING_SNIPPET + """end
"""


def log(msg):
    print("[patch-podfile] %s" % msg)


def main():
    if not os.path.exists(PODFILE):
        log("HATA: %s bulunamadi." % PODFILE)
        log("'npx cap add ios' bu adimdan ONCE calistirilmis olmali.")
        return 1

    with open(PODFILE, "r", encoding="utf-8") as f:
        content = f.read()

    changed = False

    # ---- 1) Bagimlilik surumlerini sabitle ----
    if PIN_MARKER in content:
        log("Surum sabitleme zaten mevcut, atlandi.")
    else:
        target_match = re.search(r"^target ['\"]App['\"] do\s*$", content, re.MULTILINE)
        if target_match:
            insert_at = target_match.end()
            content = content[:insert_at] + "\n" + PINNED_PODS + content[insert_at:]
            log("GoogleUserMessagingPlatform '~> 2.0' olarak sabitlendi "
                "(UMP 3.x Swift API degisikligi nedeniyle).")
            changed = True
        else:
            log("UYARI: \"target 'App' do\" blogu bulunamadi; surum sabitleme "
                "eklenemedi. Podfile yapisi beklenenden farkli olabilir.")

    # ---- 2) Kod imzalamayi kapat ----
    if MARKER in content:
        log("Imzalama yamasi zaten mevcut, atlandi.")
        if changed:
            with open(PODFILE, "w", encoding="utf-8") as f:
                f.write(content)
        return 0

    # Capacitor'in var olan post_install blogunu bul.
    match = re.search(r"^post_install do \|(\w+)\|\s*$", content, re.MULTILINE)

    if match:
        var_name = match.group(1)
        snippet = SIGNING_SNIPPET
        # Blok degiskeni 'installer' degilse ona gore uyarla.
        if var_name != "installer":
            snippet = snippet.replace("installer.", "%s." % var_name)
        insert_at = match.end()
        content = content[:insert_at] + "\n" + snippet + content[insert_at:]
        log("Var olan post_install blogunun icine imzalama ayarlari eklendi "
            "(blok degiskeni: '%s')." % var_name)
    else:
        content = content.rstrip() + "\n" + NEW_POST_INSTALL
        log("Podfile'da post_install blogu yoktu; yenisi olusturuldu.")

    with open(PODFILE, "w", encoding="utf-8") as f:
        f.write(content)

    log("Tamamlandi: Pod hedeflerinde kod imzalama kapatildi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
