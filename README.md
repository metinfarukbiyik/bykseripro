# BYK Seri Baskı Pro

**Excel’den seri barkod / seri no etiketlerini okuyup termal yazıcıya basan masaüstü uygulaması.**  
Geliştirici: [BIYIK.DEV](https://biyik.dev) · İletişim: [metin@biyik.dev](mailto:metin@biyik.dev)

Sürüm: **1.1.1**

---

## Program ne işe yarar?

Üretim, depo veya satış süreçlerinde **seri numarası / barkod etiketlerini** toplu basmak için tasarlandı.

1. Excel dosyasındaki satırları okur  
2. Etiketi ekranda **önizler**  
3. **TSPL** komutlarıyla termal yazıcıya (ör. Xprinter XP-490B) gönderir  

Python kurulumu gerekmez (hazır kurulum paketleriyle). İnternet bağlantısı kurulum sonrası zorunlu değildir.

---

## Öne çıkan özellikler

- Excel’den toplu etiket listesi (seri no / barkod + ikinci barkod + metin alanları)
- Canlı etiket önizlemesi
- Seçili satırları veya tüm listeyi basma
- Test baskı (örnek etiket)
- Barkod tipi seçimi (Code 128 vb.) ve QR desteği
- Marka / firma metni (üst veya alt konum)
- Etiket boyutu, boşluk, DPI, hız, yoğunluk ayarları
- Yazıcı seçimi (Windows / macOS)
- Ayarların kaydı (`config.json`)
- Windows kurulum sihirbazı + macOS `.app` paketi

---

## Nasıl çalışır?

```text
Excel (.xlsx)
    ↓
Sütun eşleme (Barkod, A-K Barkod, ItemNo, ParcaAd …)
    ↓
Önizleme (ekran)
    ↓
TSPL komutları
    ↓
Termal yazıcı (raw / CUPS)
```

### Excel formatı

- **1. satır** sütun başlığıdır  
- Sonraki satırlar etiket verisidir  

Varsayılan sütun rolleri:

| Rol | Örnek başlık | Zorunlu? |
|-----|--------------|----------|
| Ana barkod / seri no | `Barkod` | Evet |
| İkinci barkod | `A-K Barkod` | Hayır |
| Orta metin | `ItemNo` | Hayır |
| Alt metin | `ParcaAd` | Hayır |

Başlık adları biraz farklı olsa da program bilinen eş anlamlıları tanır (`Seri No`, `Barcode`, `Item No` vb.). Bulamazsa sütunları soldan sağa A–D sırasıyla kullanır.

Örnek dosya projede: `Barkod.xlsx`

### Tipik kullanım adımları

1. Programı aç  
2. Excel dosyasını seç / yükle  
3. Yazıcıyı seç (Xprinter veya TSPL uyumlu)  
4. Önizlemeyi kontrol et  
5. **Seçilileri Bas** veya **Tümünü Bas**  
6. İstersen **Ayarları Kaydet**

Program içindeki **Kullanım** butonu da aynı kılavuzu gösterir.

---

## Gereksinimler

| | |
|---|---|
| İşletim sistemi | Windows 10/11 veya macOS 12+ |
| Yazıcı | Xprinter XP-490B veya **TSPL** uyumlu termal etiket yazıcısı |
| Excel | `.xlsx` (Microsoft Excel / uyumlu) |
| Ağ | Kurulum sonrası gerekmez |

**macOS yazıcı:** Sistem Ayarları → Yazıcılar ve Tarayıcılar → yazıcıyı ekleyin. Uygulama baskıyı CUPS üzerinden **raw TSPL** olarak gönderir.

---

## İndirme ve kurulum

### Windows (önerilen setup)

1. `BYKSeriBaskiPro_vX.X.X_Kurulum.zip` dosyasını indirin  
2. Zip’i açın  
3. `BYKSeriBaskiPro_Kurulum.exe` dosyasına çift tıklayın  
4. Kurulum klasörünü seçin → **Kurulumu Başlat**  

Varsayılan klasör:

```text
%LOCALAPPDATA%\BiyikDev\BYKSeriBaskiPro
```

İsterseniz Program Files altına da kurabilirsiniz (yönetici onayı gerekebilir).

**SmartScreen uyarısı** çıkarsa: *Ek bilgi* → *Yine de çalıştır*.

### macOS

1. `BYKSeriBaskiPro_vX.X.X_macOS.zip` dosyasını indirin  
2. Zip’i açın  
3. `BYKSeriBaskiPro.app` dosyasına çift tıklayın  
   **veya** `KURULUM.command` ile `/Applications` altına kurun  

İlk açılışta Gatekeeper engellerse: uygulamaya **sağ tık → Aç → Aç**.

Veri / ayar klasörü:

```text
~/Library/Application Support/BiyikDev/BYKSeriBaskiPro
```

### GitHub Releases (otomatik paketler)

Sürüm etiketi (`v1.1.1` vb.) push edildiğinde **GitHub Actions** hem Windows hem macOS zip üretir:

- Windows: `…_Kurulum.zip` (+ isteğe bağlı `…_Portable.zip`)  
- macOS: `…_macOS.zip`  

İndirme sayfası örneği:

```text
https://github.com/<KULLANICI>/<REPO>/releases/latest
```

Aynı zip dosyalarını kendi web sitenize de koyabilirsiniz.

> **Not:** Mac bilgisayarda Windows `.exe` üretilemez. Windows paketi Windows’ta veya GitHub Actions Windows runner’ında derlenir.

---

## Kaldırma

| Platform | Nasıl |
|----------|--------|
| Windows | Ayarlar → Uygulamalar, veya kurulum klasöründeki `KALDIR.bat` |
| macOS | `KALDIR.command` / `KALDIR.sh`, veya Applications’tan `.app` silme |

---

## Ayarlar (özet)

Program `config.json` ile kaydeder. Tipik alanlar:

- Yazıcı adı  
- Etiket genişlik / yükseklik / boşluk (mm)  
- DPI, kopya, hız, yoğunluk  
- Barkod tipi ve yükseklikleri  
- Marka metni ve konumu (`top` / `bottom`)  
- Excel sütun eşlemeleri  

Varsayılan örnek etiket boyutu: **98 × 98 mm**, **203 DPI**, yazıcı: **Xprinter XP-490B**.

---

## Kaynaktan çalıştırma (geliştirici)

```bash
# Bağımlılıklar
pip install -r requirements.txt

# Windows
BASLAT.bat

# macOS
./BASLAT.command
# veya
./BASLAT.sh
```

### Paketleme

| Platform | Komut | Çıktı |
|----------|--------|--------|
| Windows | `BUILD_RELEASE.bat` | `release\BYKSeriBaskiPro_v…_Kurulum.zip` |
| macOS | `BUILD_RELEASE_MAC.command` | `release/BYKSeriBaskiPro_v…_macOS.zip` |

Yalnızca uygulama (geliştirme):

- Windows: `BUILD_EXE.bat` → `dist\BYKSeriBaskiPro\`  
- macOS: `BUILD_APP.command` → `dist/BYKSeriBaskiPro.app`

### İsimlendirme

| | |
|---|---|
| Görünen ad | BYK Seri Baskı Pro |
| Kısa ad | `BYKSeriBaskiPro` |
| Windows exe | `BYKSeriBaskiPro.exe` |
| Kurulum exe | `BYKSeriBaskiPro_Kurulum.exe` |
| macOS | `BYKSeriBaskiPro.app` |
| Bundle ID | `dev.biyik.seribaskipro` |

Tek kaynak: `branding.py`

### İkonlar

Tek tasarım kaynağı: `assets/app.png` (önerilen **1024×1024**).

```bash
python tools/prepare_icons.py
# macOS:
iconutil -c icns assets/app.iconset -o assets/app.icns
```

UI rozeti: `assets/biyik_badge.png` (sistem ikonu değil).

---

## Web sitenize eklerken

Bu README’yi olduğu gibi veya bölümler halinde kullanabilirsiniz. Sitede özellikle şu bloklar yeterlidir:

1. **Ne işe yarar?** (üst özet)  
2. **Özellikler**  
3. **Nasıl çalışır?** + Excel tablosu  
4. **İndir** (Windows / macOS butonları → zip linkleri)  
5. **Kurulum adımları**  
6. **Gereksinimler**  
7. **İletişim**  

İndirme butonları için örnek metin:

- **Windows için indir** → `BYKSeriBaskiPro_v1.1.1_Kurulum.zip`  
- **macOS için indir** → `BYKSeriBaskiPro_v1.1.1_macOS.zip`  

---

## Destek

- E-posta: [metin@biyik.dev](mailto:metin@biyik.dev)  
- Geliştirici: Metin Faruk BIYIK · **BIYIK.DEV**  
- WhatsApp: +90 (540) 461 35 43  

---

© BIYIK.DEV — BYK Seri Baskı Pro
