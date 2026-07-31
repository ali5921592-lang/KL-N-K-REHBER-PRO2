#!/usr/bin/env python3
"""
patch-podfile.py

Amac: ios/App/Podfile dosyasina, Pods hedeflerinde (CocoaPods ile eklenen
tum kutuphane target'larinda) kod imzalamayi devre disi birakan bir
post_install hook'u ekler.

Neden gerekli: Manuel imzalama (Manual signing, Distribution certificate +
provisioning profile) kullanildiginda, Xcode varsayilan olarak CocoaPods
tarafindan olusturulan her bir Pods hedefini de (orn. Capacitor eklentileri,
kutuphaneler) ayni sekilde imzalamaya calisir. Bu hedeflerin kendi
provisioning profili olmadigi icin "no signing certificate" / "requires a
provisioning profile" gibi hatalarla arsivleme (archive) adimi basarisiz
olur. Bu script, sadece Pods hedeflerinde CODE_SIGNING_ALLOWED = NO
ayarlayarak bu sorunu onler; ana uygulama hedefinin (App) imzalama
ayarlarina dokunmaz.

Idempotent: Script birden fazla kez calistirilsa bile Podfile'a ayni
blogu tekrar tekrar eklemez; onceden eklenmis oldugunu tespit ederse
hicbir degisiklik yapmadan cikar.
"""

import os
import sys

PODFILE_PATH = os.path.join("ios", "App", "Podfile")

# Podfile'a eklenecek post_install hook. Podfile Ruby syntax'i kullanir.
MARKER = "# >>> patch-podfile.py: disable codesign for Pods targets >>>"
END_MARKER = "# <<< patch-podfile.py: disable codesign for Pods targets <<<"

POST_INSTALL_BLOCK = f'''
{MARKER}
post_install do |installer|
  installer.pods_project.targets.each do |target|
    target.build_configurations.each do |config|
      config.build_settings['CODE_SIGNING_ALLOWED'] = 'NO'
      config.build_settings['CODE_SIGNING_REQUIRED'] = 'NO'
      config.build_settings['CODE_SIGN_IDENTITY'] = ''
    end
  end
end
{END_MARKER}
'''


def main():
    if not os.path.isfile(PODFILE_PATH):
        print(f"HATA: Podfile bulunamadi: {PODFILE_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(PODFILE_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    if MARKER in content:
        print("Podfile zaten yamali (marker bulundu). Islem yapilmadi.")
        return

    # Podfile'da zaten bir post_install bloğu varsa, kullanıcıyı uyar
    # ama yine de kendi bloğumuzu ayrı olarak sona ekleyelim (Ruby birden
    # fazla post_install do..end blogunu ayni Podfile icinde calistirmaz,
    # bu yuzden mevcut bir post_install varsa onun icine enjekte etmemiz
    # daha guvenli olur).
    if "post_install do |installer|" in content:
        # Mevcut post_install blogunun ilk satirindan hemen sonra
        # kendi kod imzalama ayarlarimizi enjekte ediyoruz.
        injection = (
            "\n    # >>> patch-podfile.py: disable codesign for Pods targets >>>\n"
            "    installer.pods_project.targets.each do |target|\n"
            "      target.build_configurations.each do |config|\n"
            "        config.build_settings['CODE_SIGNING_ALLOWED'] = 'NO'\n"
            "        config.build_settings['CODE_SIGNING_REQUIRED'] = 'NO'\n"
            "        config.build_settings['CODE_SIGN_IDENTITY'] = ''\n"
            "      end\n"
            "    end\n"
            "    # <<< patch-podfile.py: disable codesign for Pods targets <<<\n"
        )
        content = content.replace(
            "post_install do |installer|",
            "post_install do |installer|" + injection,
            1,
        )
        print("Mevcut post_install blogu bulundu, kod imzalama ayarlari icine enjekte edildi.")
    else:
        content = content.rstrip("\n") + "\n" + POST_INSTALL_BLOCK
        print("Podfile'in sonuna yeni post_install blogu eklendi.")

    with open(PODFILE_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Basariyla yamalandi: {PODFILE_PATH}")


if __name__ == "__main__":
    main()
