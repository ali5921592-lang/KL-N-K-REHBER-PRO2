# Klinik Rehber Pro — Android + iOS Uygulaması

Bu klasör, mevcut **Klinik Rehber Pro** web uygulamasını (`www/index.html`),
hiçbir iç kodu değiştirmeden, [Capacitor](https://capacitorjs.com/) ile hem
**Android** hem **iOS** uygulamasına dönüştürür. APK, AAB ve IPA dosyaları
**GitHub Actions** üzerinden otomatik olarak derlenir — Android Studio veya
Xcode kurmanıza ya da elle bir işlem yapmanıza gerek yoktur (iOS derlemesi
GitHub'ın bulut üzerindeki macOS runner'ında, Xcode önceden kurulu şekilde
çalışır).

## 📢 AdMob Reklamları ve Firebase Analytics

Uygulamaya Google AdMob (banner + geçiş + ödüllü reklam) ve Firebase Analytics
altyapısı entegre edilmiştir. **Varsayılan olarak Google'ın resmi TEST reklam
kimlikleri** kullanılır — bunlar gerçek para kazandırmaz ama güvenle test
edilebilir, App Store/Play Store politikalarını ihlal etmez.

### Gerçek reklam kimliklerinizi tek dosyadan değiştirme

Proje kökündeki **`ad-config.json`** dosyası tüm reklam kimliklerinin TEK
kaynağıdır:

```json
{
  "android": {
    "appId": "ca-app-pub-XXXXXXXX~XXXXXXXX",
    "bannerId": "ca-app-pub-XXXXXXXX/XXXXXXXX",
    "interstitialId": "ca-app-pub-XXXXXXXX/XXXXXXXX",
    "rewardedId": "ca-app-pub-XXXXXXXX/XXXXXXXX"
  },
  "ios": { "...aynı yapı..." }
}
```

Kendi [AdMob hesabınızdan](https://apps.admob.com) aldığınız gerçek kimliklerle
bu dosyayı güncelleyip commit ettiğinizde, `scripts/patch-ads.py` bir sonraki
derlemede bu değerleri otomatik olarak:
- Android Manifest'e (`APPLICATION_ID` meta-data),
- iOS Info.plist'e (`GADApplicationIdentifier` + `SKAdNetworkItems`),
- Web uygulamasının reklam modülüne (banner/geçiş/ödüllü ID'leri),

işler. Başka hiçbir dosyayı elle düzenlemeniz gerekmez.

### GDPR/UMP Rıza Yönetimi (AB/İngiltere/İsviçre kullanıcıları için zorunlu)

Google, AB/İngiltere/İsviçre'deki kullanıcılara reklam gösterilmeden önce rıza (consent) formu gösterilmesini **zorunlu** kılar; aksi halde AdMob hesabınız politika ihlali nedeniyle askıya alınabilir. Kod tarafı tamamen hazır:
- Uygulama açılışında, kullanıcının konumuna göre rıza gerekip gerekmediği otomatik kontrol edilir ve gerekiyorsa Google'ın standart rıza formu gösterilir — reklam SDK'sı ancak bu adımdan SONRA başlatılır.
- Kullanıcılar Ayarlar ekranındaki **"Gizlilik Tercihlerini Yönet"** butonuyla rızalarını istedikleri zaman değiştirebilir (Google bunu da zorunlu tutar).

**Sizin yapmanız gereken tek şey:** [AdMob hesabınızda](https://apps.admob.com) **Gizlilik ve mesajlaşma (Privacy & messaging)** bölümünden bir "GDPR mesajı" (rıza formu şablonu) oluşturup yayınlamak. Bu, kod değişikliği gerektirmez — Google konsolunda birkaç dakikalık bir kurulumdur. Bu adım tamamlanmadan uygulama çökmez, sadece form gösterilmez ve reklamlar doğrudan başlatılır.

### Firebase Analytics kurulumu (elle yapmanız gereken tek adım)

Firebase Analytics çalışması için **kendi Firebase projenizi** oluşturup
yapılandırma dosyalarını eklemeniz gerekir (bunu sizin adınıza oluşturamam,
Google hesabınıza bağlıdır):

1. [Firebase Console](https://console.firebase.google.com) → yeni proje oluşturun.
2. Android uygulaması ekleyin (paket adı: `capacitor.config.json` içindeki `appId` ile birebir aynı olmalı) → **`google-services.json`** indirin → repoya `android/app/google-services.json` yoluna ekleyin (not: `android/` klasörü her derlemede yeniden üretildiği için, bu dosyayı **CI'da otomatik kopyalanacak şekilde** `resources/google-services.json` konumuna koyup `scripts/patch-ads.py`'ye bir kopyalama adımı eklemeniz gerekir — bu adımı isterseniz sizin için hazırlarım).
3. iOS uygulaması ekleyin → **`GoogleService-Info.plist`** indirin → benzer şekilde `resources/` altına eklenip CI'da kopyalanması gerekir.
4. Firebase Console'da Analytics'i etkinleştirin.

> **Not:** Bu adım tamamlanmadan uygulama **çökmez** — `FirebaseAnalytics`
> eklentisi bulunamazsa (Plugins.FirebaseAnalytics kontrolü ile) analytics
> çağrıları sessizce atlanır, reklam sistemi bundan etkilenmez.

### Takip edilen olaylar (Firebase Analytics)

`screen_view`, `banner_impression`, `interstitial_shown`, `rewarded_ad_completed`,
`premium_status_changed`, `session_duration` — bunlar mobil köprü scriptinin
AdMob modülünde otomatik loglanır.

### Reklam davranış kuralları (kod içinde uygulanmıştır)

- **Banner**: Ana sayfa dahil tüm sayfalarda ekranın en altında sabit, responsive, içeriği kapatmaz.
- **Geçiş reklamı**: Uygulama açılır açılmaz gösterilmez (20 saniye bekleme), en az 4-5 farklı bölüm gezildikten sonra, en az 3 dakika arayla, art arda gösterilmez. **CPR/acil müdahale (112/Ambulans ve Acil Servis klinikleri), ilaç dozu detay sayfaları ve hesaplama araçlarında (Hesaplama, Kan Gazı) ASLA gösterilmez.**
- **Ödüllü reklam**: `window.showRewardedAd(onReward, onUnavailable)` fonksiyonu üzerinden ileride "Premium içerik aç", "PDF indir" gibi özellikler için hazır; şu an hiçbir içerik buna bağlı değil.
- **Premium**: Ayarlar ekranından etkinleştirildiğinde tüm reklamlar (banner+geçiş+ödüllü) tamamen kapanır. Şu an bu bir geliştirici/test butonu; gerçek uygulama içi satın alma (App Store/Play Store IAP) entegrasyonu ayrı bir iş olarak eklenmelidir.
- **Performans**: Reklamlar önceden yüklenir (`prepareInterstitial`/`prepareRewardVideoAd`), sayfa geçişlerini bloklamaz, internet yoksa banner alanı otomatik gizlenir, reklam yüklenemezse uygulama hata vermez (tüm çağrılar try/catch içinde).

### Ayarlar ekranından yönetim

Uygulama içinde sağ üstteki ⚙️ ikonuna dokunarak: Premium aç/kapat (test),
reklamları geliştirici modunda tamamen kapatma, test/gerçek reklam modu
arasında geçiş ve güncel reklam durumunu görüntüleme mümkündür.

## Nasıl çalışır? (Android)

1. Bu repoyu GitHub'a yüklediğinizde (`main`/`master` dalına push), `.github/workflows/build-android.yml`
   iş akışı otomatik tetiklenir.
2. İş akışı sırasıyla:
   - Node.js ve JDK 17 kurar,
   - `npm install` ile Capacitor bağımlılıklarını indirir,
   - `npx cap add android` ile **native Android projesini o an taze olarak üretir**
     (bu klasör repoya commit edilmez — her zaman güncel ve tutarlı olması için
     CI'da yeniden oluşturulur),
   - `resources/icon.png` ve `resources/splash.png` kaynak görsellerinden tüm
     yoğunluklar için uygulama ikonu ve açılış ekranını otomatik üretir,
   - `scripts/patch-android.py` ile projeyi düzenler: gereksiz izinleri kaldırır,
     bildirim ikonunu yerleştirir, sürüm numarasını artırır, kod/kaynak
     küçültmeyi (R8/ProGuard) açar ve (varsa) release imzalamasını yapılandırır,
   - `./gradlew assembleRelease` ile **APK**, `./gradlew bundleRelease` ile
     **AAB** (Play Store formatı) üretir,
   - İkisini de iş akışının "Artifacts" (çıktılar) bölümüne yükler.
3. Derlenen dosyaları indirmek için: **Actions** sekmesi → ilgili çalıştırma →
   sayfanın altındaki **Artifacts** bölümü → `hemsire-rehberi-pro-apk` /
   `hemsire-rehberi-pro-aab` dosyalarını indirin.

## ⚠️ Play Store'a yüklemeden önce: gerçek imzalama şart

Varsayılan olarak (hiçbir "secret" eklemediyseniz) iş akışı, release build'i
**geçici olarak debug anahtarıyla imzalar**. Bu APK/AAB **telefonunuza kurulup
test edilebilir** ama **Play Store bunu kabul etmez**.

Play Store'a yüklenebilir, gerçek imzalı bir AAB almak için:

### 1) Bir imzalama anahtarı (keystore) oluşturun (bilgisayarınızda, bir kez)

```bash
keytool -genkey -v -keystore release.keystore -alias hemsire-rehberi \
  -keyalg RSA -keysize 2048 -validity 10000
```

Bu, sizden bir şifre ve birkaç bilgi (isim, kuruluş vb.) isteyecek ve
`release.keystore` dosyasını oluşturacaktır. **Bu dosyayı ve şifrelerini asla
kaybetmeyin / paylaşmayın** — Play Store'da uygulamanızı güncelleyebilmek için
her zaman aynı anahtara ihtiyacınız olacak.

### 2) Keystore dosyasını base64'e çevirin

```bash
base64 -w 0 release.keystore > release.keystore.base64.txt
```

(macOS'ta `base64 -w 0` yerine `base64` kullanın.)

### 3) GitHub reponuza 4 "secret" ekleyin

Repo sayfanızda: **Settings → Secrets and variables → Actions → New repository secret**

| Secret adı | Değeri |
|---|---|
| `KEYSTORE_BASE64` | `release.keystore.base64.txt` dosyasının içeriği |
| `KEYSTORE_PASSWORD` | `keytool` sırasında girdiğiniz keystore şifresi |
| `KEY_ALIAS` | `hemsire-rehberi` (yukarıdaki `-alias` değeri) |
| `KEY_PASSWORD` | Anahtar (key) şifresi (genelde keystore şifresiyle aynıdır) |

Bu 4 secret eklendikten sonra yapılan her push'ta iş akışı **otomatik olarak
gerçek imzalı, Play Store'a yüklenebilir bir AAB** üretecektir — başka hiçbir
işlem gerekmez.

### 4) Play Console'a yükleme

Üretilen `.aab` dosyasını [Google Play Console](https://play.google.com/console)
üzerinden yeni bir uygulama olarak (veya mevcut uygulamanıza yeni sürüm olarak)
yükleyebilirsiniz.

## 🍎 iOS (App Store) — Apple Developer hesabı gerektirir

Bu proje hem Android hem iOS'u **aynı repo, aynı web kodundan** üretir.
iOS derlemesi `.github/workflows/build-ios.yml` ile **macOS runner** üzerinde
(Xcode önceden kurulu gelir) otomatik çalışır.

### Android ile kritik fark: Apple Developer Program zorunlu

Android'de "secret" eklemeseniz bile her zaman kurulabilir bir debug-signed
APK üretilebiliyordu. **iOS'ta bu mümkün değil** — Apple, gerçek bir
`.ipa` üretebilmek için bile geçerli bir Apple Developer Program üyeliği
(yıllık $99) ve o hesaptan üretilmiş bir Distribution sertifikası +
provisioning profile ister. Bu bilgileri sizin için üretemem; yalnızca siz
Apple Developer hesabınızdan alabilirsiniz.

**5 secret tanımlanmadığı sürece** iş akışı, projenin Xcode'da sorunsuz
açıldığını ve derlendiğini doğrulamak için yalnızca bir **simulator duman
testi** yapar (gerçek bir .ipa üretmez). Secret'lar eklendiğinde otomatik
olarak gerçek, imzalı, App Store'a yüklenebilir bir `.ipa` üretir.

### Gerekli 5 GitHub secret'ı nasıl elde edilir

1. **Apple Developer hesabınızla** [developer.apple.com](https://developer.apple.com) → Certificates, Identifiers & Profiles bölümüne gidin.
2. **Distribution sertifikası** oluşturun (Certificates → + → Apple Distribution), indirin, Mac'inizde çift tıklayıp Keychain Access'e ekleyin, sonra Keychain Access'ten sağ tık > Export > `.p12` formatında dışa aktarın (bir şifre belirleyin).
3. **App ID** oluşturun (Identifiers → + → App IDs), `capacitor.config.json` içindeki `appId` (`com.hemsirerehberi.pro`) ile birebir aynı olmalı.
4. **Provisioning Profile** oluşturun (Profiles → + → App Store → yukarıdaki App ID'yi ve sertifikayı seçin), indirin (`.mobileprovision` dosyası), bir isim verin (bu isim `IOS_PROFILE_NAME` olacak).
5. **Team ID**'nizi bulun: developer.apple.com → Membership sayfasında görünür (10 karakterlik kod).
6. `.p12` ve `.mobileprovision` dosyalarını base64'e çevirin:
   ```bash
   base64 -i Certificates.p12 | pbcopy      # IOS_DIST_CERT_BASE64 icin
   base64 -i profile.mobileprovision | pbcopy  # IOS_PROVISION_PROFILE_BASE64 icin
   ```
7. Repo **Settings → Secrets and variables → Actions** bölümüne şu 5 secret'ı ekleyin:

| Secret adı | Değeri |
|---|---|
| `IOS_DIST_CERT_BASE64` | `.p12` dosyasının base64 hali |
| `IOS_DIST_CERT_PASSWORD` | `.p12` dışa aktarırken belirlediğiniz şifre |
| `IOS_PROVISION_PROFILE_BASE64` | `.mobileprovision` dosyasının base64 hali |
| `IOS_TEAM_ID` | Apple Developer Team ID (10 karakter) |
| `IOS_PROFILE_NAME` | Provisioning profile'a verdiğiniz isim |

Bu 5 secret eklendikten sonra her push'ta otomatik olarak imzalı `.ipa`
üretilir ve iş akışının **Artifacts** bölümünden indirilebilir.

### Bundle Identifier, Versiyon ve Build Number özelleştirme

Bu değerleri elle değiştirmeniz gerekmez — **Actions** sekmesinden workflow'u
elle tetiklediğinizde (workflow_dispatch) şu alanları girebilirsiniz:
- **Bundle Identifier** — boş bırakılırsa `capacitor.config.json` değeri kullanılır
- **Versiyon numarası** (örn. `1.2.0`)
- **Build numarası** — boş bırakılırsa GitHub çalıştırma numarası kullanılır (her seferinde otomatik artar, App Store Connect'in gereksinimini karşılar)

### App Store'a yükleme

Üretilen `.ipa` dosyasını **Transporter** uygulaması (Mac App Store'dan
ücretsiz indirilir) veya `xcrun altool`/`xcrun notarytool` ile
App Store Connect'e yükleyebilirsiniz.

### Apple Human Interface Guidelines uyumluluğu

- **Light/Dark Mode:** Uygulamanın kendi `data-theme` mekanizması korunur; mobil köprü scripti StatusBar'ı buna göre senkronize eder.
- **Safe Area (çentik/Dynamic Island):** `capacitor.config.json` içinde `ios.contentInset:"automatic"` ayarlanmıştır (Apple'ın önerdiği standart yöntem); ayrıca üst bar için `env(safe-area-inset-top)` ek güvence olarak enjekte edilir. Alt gezinme çubuğu zaten `env(safe-area-inset-bottom)` kullanıyordu (mevcut kodda).
- **Swipe Back:** Capacitor'ın WKWebView varsayılan `allowsBackForwardNavigationGestures` davranışı korunur; uygulama SPA olduğu için bu jest donanım geri tuşu mantığıyla çakışmaz (Android'deki gibi ayrı bir JS yönetimi gerekmez, iOS'ta kenar kaydırma hareketi native olarak çalışır).
- **iPad desteği:** `patch-ios.py`, iPad için 4 yönü de destekleyecek ve `UIRequiresFullScreen`'i kaldırarak Split View/Slide Over'a izin verecek şekilde `Info.plist`'i düzenler.
- **Privacy Manifest:** `ios-privacy/PrivacyInfo.xcprivacy` dosyası, hem diske kopyalanır hem de `scripts/add_privacy_manifest_to_xcodeproj.rb` ile Xcode projesinin gerçek "Copy Bundle Resources" derleme fazına kaydedilir (yalnızca dosyayı kopyalamak Xcode'un onu `.ipa` içine paketlemesi için yeterli değildir).
- **Gereksiz izin yok:** Varsayılan Capacitor şablonu kamera/konum/mikrofon gibi hiçbir izin açıklaması içermez; `patch-ios.py` bunu her derlemede doğrular.



Web uygulaması, yalnızca Claude.ai artifact ortamında bulunan özel bir
`window.storage` API'si kullanıyordu. Gerçek bir Android WebView'da bu API
mevcut olmadığı için favoriler/notlar/nöbet listesi hiç kaydedilmezdi.

`www/index.html` dosyasının sonuna, **mevcut uygulama kodunu hiç değiştirmeden**,
ayrı bir `<script>` bloğu eklendi. Bu script:
- `window.storage` yoksa, aynı arayüzü `localStorage` üzerinden sağlar (kalıcı
  depolama artık gerçekten çalışır),
- Android donanım geri tuşunu SPA içi gezinmeyle eşler (ana sayfada değilse
  ana sayfaya döner, ana sayfadaysa uygulamadan çıkar),
- Karanlık mod durumuna göre durum çubuğunu (status bar) senkronize eder,
- Açılış ekranını (splash screen) kapatır,
- Nöbet listesindeki vardiyalar için **gerçek native yerel bildirimler**
  zamanlar (web sürümünün aksine, uygulama kapalıyken de çalışır).

## İzinler

Uygulama tamamen çevrimdışı çalıştığı için `INTERNET` ve
`ACCESS_NETWORK_STATE` izinleri CI tarafından otomatik kaldırılır. Yalnızca
nöbet bildirimi özelliği için gerekli olan bildirim izni (Android 13+'ta
çalışma zamanında kullanıcıya sorulur) kalır. Bu özelliği hiç istemiyorsanız
`package.json` içinden `@capacitor/local-notifications` satırını silip
`www/index.html` sonundaki "VARDİYA HATIRLATMALARI" bölümünü kaldırabilirsiniz.

## Yerel olarak test etmek isterseniz (opsiyonel)

Android Studio kurmanıza gerek olmasa da, isterseniz kendi bilgisayarınızda
da aynı adımları çalıştırabilirsiniz (Node.js ve JDK 17 kuruluysa):

```bash
npm install
npx cap add android
npx capacitor-assets generate --android
npx cap sync android
cd android
./gradlew assembleDebug
```

Üretilen dosya: `android/app/build/outputs/apk/debug/app-debug.apk`

## Proje yapısı

```
├── .github/workflows/build-android.yml   # Android otomatik derleme iş akışı
├── .github/workflows/build-ios.yml       # iOS otomatik derleme iş akışı
├── ad-config.json                        # AdMob reklam kimlikleri (TEK dosyadan yönetim)
├── capacitor.config.json                 # Capacitor yapılandırması (Android+iOS)
├── package.json                          # Bağımlılıklar (Android+iOS+AdMob+Firebase)
├── resources/
│   ├── icon.png                          # Uygulama ikonu kaynağı (1024x1024)
│   ├── splash.png                        # Açılış ekranı kaynağı (2732x2732)
│   └── notification-icon.png             # Bildirim ikonu (beyaz siluet)
├── ios-privacy/PrivacyInfo.xcprivacy      # Apple Privacy Manifest kaynağı
├── scripts/
│   ├── patch-android.py                  # CI'da native Android projesini düzenleyen script
│   ├── patch-ios.py                      # CI'da native iOS projesini düzenleyen script (Info.plist, ekran yönleri)
│   ├── patch-ads.py                      # ad-config.json'ı Android/iOS/web uygulamasına işler
│   ├── add_privacy_manifest_to_xcodeproj.rb  # Privacy Manifest'i Xcode projesine gerçekten kaydeder
│   └── generate-export-options.py        # App Store export için exportOptions.plist üretir
└── www/index.html                        # Uygulamanın kendisi (DEĞİŞTİRİLMEDİ + ek köprü scripti + reklam modülü)
```

`android/` ve `ios/` klasörleri kasıtlı olarak repoya eklenmemiştir; her
derlemede `npx cap add android` / `npx cap add ios` ile sıfırdan ve güncel
Capacitor sürümüyle tutarlı şekilde üretilir. Bu, elle yazılmış/bakımı güç
bir native proje yerine, her zaman doğru ve güncel bir yapı garanti eder.

## Uygulama kimliği ve sürüm

- **Paket adı (applicationId):** `com.hemsirerehberi.pro`
- **Uygulama adı:** Klinik Rehber Pro
- **versionCode:** Her CI çalıştırmasında otomatik artar (GitHub Actions
  çalıştırma numarasına eşittir) — Play Store'un her yüklemede daha yüksek
  bir versionCode istemesi kuralını otomatik karşılar.

Paket adını değiştirmek isterseniz `capacitor.config.json` içindeki `appId`
alanını güncelleyin (Play Store'a ilk yüklemeden ÖNCE yapılmalıdır; sonradan
değiştirilemez).
