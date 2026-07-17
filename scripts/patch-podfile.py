#!/usr/bin/env python3
"""
patch-podfile.py
------------------
`npx cap add ios` calistiktan hemen sonra, `npx cap sync ios` (pod install'i
tetikleyen adim) calismadan ONCE calistirilmalidir.

SORUN: Manuel imzalama (CODE_SIGN_STYLE=Manual + PROVISIONING_PROFILE_SPECIFIER)
xcodebuild komut satirindan verildiginde, bu ayar workspace'teki TUM hedeflere
uygulanir - App hedefine degil, ayni zamanda CocoaPods kutuphane/framework
hedeflerine de (CapacitorLocalNotifications, CapacitorStatusBar, vb.).
Ancak framework/kutuphane hedefleri provisioning profile KULLANAMAZ, bu da
"X does not support provisioning profiles" hatasina ve arsivin basarisiz
olmasina yol acar.

COZUM: Podfile'a bir `post_install` kancasi ekleyerek, TUM Pods hedeflerinde
kod imzalamayi tamamen devre disi birakiyoruz (CODE_SIGNING_ALLOWED=NO).
Bu, sadece kutuphaneler icindir - asil App hedefinin imzalanmasini ETKILEMEZ,
o hala xcodebuild komut satirindaki PROVISIONING_PROFILE_SPECIFIER ile
duzgun sekilde imzalanir.

Bu, Capacitor/CocoaPods projelerinde manuel imzalama kullanirken standart
ve yaygin olarak onerilen bir duzeltmedir.
"""
import os
import re
import sys

PODFILE_PATH = os.path.join("ios", "App", "Podfile")

POST_INSTALL_SNIPPET = """    installer.pods_project.targets.each do |target|
      target.build_configurations.each do |config|
        config.build_settings['CODE_SIGNING_ALLOWED'] = 'NO'
        config.build_settings['CODE_SIGNING_REQUIRED'] = 'NO'
      end
    end
"""


def log(msg):
    print(f"[patch-podfile] {msg}")


def main():
    if not os.path.exists(PODFILE_PATH):
        log(f"HATA: {PODFILE_PATH} bulunamadi. 'npx cap add ios' calistirildi mi?")
        return 1

    with open(PODFILE_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    if "CODE_SIGNING_ALLOWED" in content:
        log("Podfile zaten yamali (CODE_SIGNING_ALLOWED bulundu). Tekrar yama uygulanmayacak.")
        return 0

    post_install_pattern = re.compile(r"(post_install do \|installer\|\s*\n)")
    match = post_install_pattern.search(content)

    if match:
        # Mevcut post_install bloğunun hemen icine ekle
        insert_pos = match.end()
        new_content = content[:insert_pos] + POST_INSTALL_SNIPPET + content[insert_pos:]
        log("Mevcut 'post_install' bloguna kod imzalama devre disi birakma satirlari eklendi.")
    else:
        # post_install blogu hic yoksa, dosyanin sonuna yeni bir tane ekle
        new_content = content.rstrip() + "\n\npost_install do |installer|\n" + POST_INSTALL_SNIPPET + "end\n"
        log("Podfile'da 'post_install' blogu bulunamadi, yeni bir tane eklendi.")

    with open(PODFILE_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)

    log(f"{PODFILE_PATH} basariyla yamalandi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
