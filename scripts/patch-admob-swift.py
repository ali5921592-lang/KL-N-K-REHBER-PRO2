import os
import re

# 1. ConsentExecutor.swift'i Düzenleme
consent_file = "node_modules/@capacitor-community/admob/ios/Sources/AdMobPlugin/Consent/ConsentExecutor.swift"

if os.path.exists(consent_file):
    with open(consent_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Önce eski yama kurallarını (özel durumlar) uygulayalım
    content = content.replace("parameters.tagForUnderAgeOfConsent =", "parameters.isTaggedForUnderAgeOfConsent =")
    content = content.replace("ConsentForm.load(completionHandler:", "ConsentForm.load(with:")
    content = content.replace("sharedInstance", "shared")

    # Sonra en kritik kısım: Sınıf isimlerindeki "UMP" önekini temizleyelim.
    # UMPRequestParameters, UMPDebugSettings, vb. hepsi düzeltilecek.
    # (Regex kullanarak kelime içindeki 'UMP'leri siliyoruz, böylece sadece UMP takısını kaldırır, başka bir şeye dokunmaz)
    content = re.sub(r'\bUMP([A-Z])', r'\1', content)

    with open(consent_file, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Başarılı: {consent_file} yamalandı.")
else:
    print(f"Hata: {consent_file} bulunamadı.")


# 2. BannerExecutor.swift'i Düzenleme (Sarı uyarıyı gidermek için)
banner_file = "node_modules/@capacitor-community/admob/ios/Sources/AdMobPlugin/Banner/BannerExecutor.swift"

if os.path.exists(banner_file):
    with open(banner_file, "r", encoding="utf-8") as f:
        banner_content = f.read()

    # Uyarı veren kGADAdSizeSmartBannerPortrait'i yeni kullanım şekli ile değiştiriyoruz.
    # Genişliği cihaz ekran genişliğine sabitlemek standart adaptif banner yöntemidir.
    banner_content = banner_content.replace(
        "kGADAdSizeSmartBannerPortrait",
        "GADPortraitAnchoredAdaptiveBannerAdSizeWithWidth(UIScreen.main.bounds.size.width)"
    )

    with open(banner_file, "w", encoding="utf-8") as f:
        f.write(banner_content)
    print(f"Başarılı: {banner_file} yamalandı.")
else:
    print(f"Hata: {banner_file} bulunamadı.")

print("Tüm AdMob yamaları başarıyla uygulandı!")
