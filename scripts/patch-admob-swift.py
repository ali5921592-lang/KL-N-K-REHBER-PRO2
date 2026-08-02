import os

# Hata veren Swift dosyasının tam yolu
consent_file = "node_modules/@capacitor-community/admob/ios/Sources/AdMobPlugin/Consent/ConsentExecutor.swift"

if os.path.exists(consent_file):
    with open(consent_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Aşama: Parametre ve Fonksiyon Çağrısı Hataları (Önceki çözdüklerimiz)
    content = content.replace("parameters.tagForUnderAgeOfConsent =", "parameters.isTaggedForUnderAgeOfConsent =")
    content = content.replace("ConsentForm.load(completionHandler:", "ConsentForm.load(with:")

    # 2. Aşama: Yeni Çıkan Sınıf İsmi (UMP Takısı) ve Değişken Hataları
    content = content.replace("UMPConsentInformation", "ConsentInformation")
    content = content.replace("sharedInstance", "shared")
    content = content.replace("UMPConsentStatus", "ConsentStatus")

    with open(consent_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("ConsentExecutor.swift içindeki TÜM eski Google SDK referansları başarıyla güncellendi!")
else:
    print(f"Hata: Dosya bulunamadı -> {consent_file}")
