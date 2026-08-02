import os

# Hata veren Swift dosyasının tam yolu
consent_file = "node_modules/@capacitor-community/admob/ios/Sources/AdMobPlugin/Consent/ConsentExecutor.swift"

if os.path.exists(consent_file):
    with open(consent_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. HATA ÇÖZÜMÜ: Sadece UMPRequestParameters objesinin özelliğini değiştiriyoruz. 
    # JS'den gelen değişken adını bozmamak için '=' işaretini referans alıyoruz.
    content = content.replace("parameters.tagForUnderAgeOfConsent =", "parameters.isTaggedForUnderAgeOfConsent =")

    # 2. HATA ÇÖZÜMÜ: Fonksiyon çağrısındaki parametre adını güncelliyoruz.
    content = content.replace("ConsentForm.load(completionHandler:", "ConsentForm.load(with:")

    with open(consent_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("ConsentExecutor.swift başarıyla yamalandı!")
else:
    print(f"Hata: Dosya bulunamadı -> {consent_file}")
