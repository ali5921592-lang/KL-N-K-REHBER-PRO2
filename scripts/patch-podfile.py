#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch-podfile.py
----------------
Capacitor'in urettigi ios/App/Podfile dosyasina bir post_install kancasi
ekler; TUM Pod hedeflerinde kod imzalamayi kapatir ve framework'leri statik
baglar ('use_frameworks! :linkage => :static').

NEDEN GEREKLI?
CI ortamindaki imzalama kimligi yalnizca ana uygulama hedefi icin
gecerlidir. CocoaPods ile gelen bagimliliklar (Capacitor eklentileri)
ayri hedefler olarak derlenir ve Xcode
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
FRAMEWORKS_MARKER = "# --- CI: static framework linkage ---"

# ---------------------------------------------------------------------------
# NEDEN use_frameworks! :linkage => :static GEREKLI?
#
# Capacitor iOS eklentileri Swift modulu olarak dagitilir. Bazi statik
# XCFramework tabanli pod'larla karisik kullanildiginda CocoaPods'un
# varsayilan dinamik framework baglamasi modul bulma hatalarina yol
# acabilir. Frameworks'leri STATIK baglamak bu tur sorunlari onler ve
# tum eklenti modullerinin dogru sekilde bulunmasini saglar.
#
# Podfile'da zaten "use_frameworks!" varsa (parametresiz ya da farkli bir
# parametreyle), bu satiri ":linkage => :static" ile degistiriyoruz.
# Hic yoksa, en basa yeni bir satir olarak ekliyoruz.
# ---------------------------------------------------------------------------
STATIC_FRAMEWORKS_LINE = "use_frameworks! :linkage => :static  " + FRAMEWORKS_MARKER

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


def patch_use_frameworks(content):
    """Podfile'daki use_frameworks! satirini statik linkage'a zorlar."""
    if FRAMEWORKS_MARKER in content:
        log("Static framework linkage yamasi zaten mevcut, atlandi.")
        return content, False

    # Var olan "use_frameworks!" satirini bul (parametreli ya da parametresiz).
    match = re.search(r"^\s*use_frameworks!.*$", content, re.MULTILINE)

    if match:
        content = content[:match.start()] + STATIC_FRAMEWORKS_LINE + content[match.end():]
        log("Mevcut 'use_frameworks!' satiri statik linkage'a "
            "(':linkage => :static') donusturuldu.")
        return content, True

    # Hic yoksa, "target 'App' do" bloguna, ondan hemen once ekle.
    target_match = re.search(r"^target ['\"]App['\"] do\s*$", content, re.MULTILINE)
    if target_match:
        insert_at = target_match.start()
        content = content[:insert_at] + STATIC_FRAMEWORKS_LINE + "\n\n" + content[insert_at:]
        log("'use_frameworks!' satiri Podfile'da yoktu; statik linkage ile "
            "yeni eklendi.")
        return content, True

    log("UYARI: 'use_frameworks!' eklenecek uygun bir konum bulunamadi "
        "(ne var olan satir ne de \"target 'App' do\" blogu bulundu).")
    return content, False


def main():
    if not os.path.exists(PODFILE):
        log("HATA: %s bulunamadi." % PODFILE)
        log("'npx cap add ios' bu adimdan ONCE calistirilmis olmali.")
        return 1

    with open(PODFILE, "r", encoding="utf-8") as f:
        content = f.read()

    changed = False

    # ---- 1) use_frameworks! satirini statik linkage'a zorla ----
    content, fw_changed = patch_use_frameworks(content)
    changed = changed or fw_changed

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
