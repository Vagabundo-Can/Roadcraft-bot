# roadcraft-bot

700 gün boyunca her gün bir Roadcraft Reels'i **kendi kendine** üretir, Instagram'a yayınlar, yorumları cevaplar, metrikleri toplar ve planı izleyici verisine göre günceller. GitHub Actions üzerinde çalışır; bilgisayarının açık olması gerekmez.

## Ne zaman ne yapar

| Ne zaman (TR saati) | İş |
|---|---|
| Her gün ~19:05 (hafta içi) / ~10:35 (hafta sonu) | Günün senaryosu → video render → GitHub Pages'e koy → Reels olarak yayınla. 2 saat sonra yedek deneme |
| 08:00–00:00 arası 2 saatte bir | Son 14 günün yorumlarını okur, sınıflandırır, uygun olanları cevaplar, spam'i gizler |
| Her gün 06:40 | İzlenme, beğeni, yorum, kaydetme, paylaşım metriklerini `data/metrics.csv`'ye yazar |
| Her Pazar 21:10 | Önümüzdeki 14 günün senaryolarını yazar (Pazar "Siz sordunuz" videosu o haftanın yorumlarından), haftalık raporu **Issue** olarak açar, Instagram anahtarını yeniler |
| Her ayın 1'i 21:25 | Şablon performansına ve yorumlara göre önümüzdeki 30 günün **esnek** slotlarını yeniden yazar |

**Güvenlik kuralları sabittir** (`bot/safety.py`): içerik yalnızca motosiklet eğitimi; her senaryo şemaya göre doğrulanır ve ikinci bir "editör" geçişinden geçer; hukuki, kaza/yaralanma, hakaret ve emin olunmayan yorumlar **otomatik cevaplanmaz**, haftalık rapora düşer. Claude API'ye ulaşılamazsa video plandaki bilgilerle yedek senaryodan üretilir, yani yayın aksamaz.

---

## Bir kerelik kurulum (~1 saat)

Meta ve GitHub arayüzlerindeki menü adları zamanla küçük değişiklikler gösterebilir; adımların özü aynıdır.

### 1. Instagram hesabını profesyonel yap
Instagram → Ayarlar → **Hesap türü ve araçlar** → **Profesyonel hesaba geç** → *İçerik Üreticisi* (veya İşletme). Facebook sayfası gerekmez.

### 2. Meta geliştirici uygulaması ve erişim anahtarı
1. https://developers.facebook.com → **Uygulamalarım** → **Uygulama oluştur**.
2. Kullanım durumu olarak Instagram'daki içerik ve mesajları yönetmeyi seç (**Instagram API'si / Instagram ile giriş**).
3. Uygulama panelinde **Instagram API with Instagram Login → API setup** bölümüne gir.
4. İzinler: `instagram_business_basic`, `instagram_business_content_publish`, `instagram_business_manage_comments`, `instagram_business_manage_insights`.
5. **Generate access tokens** → **Add account** → Instagram hesabınla giriş yap ve izin ver.
6. Ekranda çıkan **erişim anahtarını (access token)** ve hesabın yanındaki **Instagram kullanıcı ID**'sini bir kenara kopyala.

Uygulama "geliştirme modunda" kalabilir; kendi hesabında kullanmak için Meta incelemesi gerekmez.

### 3. Claude API anahtarı
https://console.anthropic.com → **API Keys** → **Create Key**. **Billing** bölümünden kredi yükle ve aylık harcama sınırı koy (öneri: başlangıçta düşük bir sınır, rapordaki yorum sayısına göre ayarla).

### 4. GitHub deposu
1. https://github.com hesabı aç → **New repository** → ad: `roadcraft-bot` → **Public** (GitHub Pages ücretsiz planda yalnızca herkese açık depolarda çalışır; şifreler ayrı ve gizli saklanır).
2. Bu klasörün **tüm içeriğini** depoya yükle (**Add file → Upload files**, klasörü sürükle-bırak). `.github/workflows/` klasörünün de yüklendiğini kontrol et.
3. **Settings → Pages → Build and deployment → Source: GitHub Actions**.
4. **Settings → Actions → General → Workflow permissions: Read and write permissions** → Save.
5. **Settings → Secrets and variables → Actions → New repository secret** ile şunları ekle:

| Ad | Değer |
|---|---|
| `IG_ACCESS_TOKEN` | 2. adımdaki erişim anahtarı |
| `IG_USER_ID` | 2. adımdaki Instagram kullanıcı ID |
| `ANTHROPIC_API_KEY` | 3. adımdaki anahtar |
| (GH_PAT artık gerekmiyor: Sayfa anahtarı süresiz) | |

### 5. Ayarlar
`config.yaml` dosyasını GitHub'da düzenle:
- `handle`: Instagram kullanıcı adın (videoların altında görünür)
- `baslangic_tarihi`: Gün 1'in yayınlanacağı tarih. Kurulumu 12.10.2026'dan sonra yaparsan buraya kurulumdan sonraki ilk Pazartesi'yi yaz.

### 6. Başlat
**Actions** sekmesi → **Plan, rapor ve anahtar yenileme** → **Run workflow** (mod: `weekly`). Bu adım ilk 14 günün senaryolarını yazar ve ilk raporu açar. Başka bir şey yapman gerekmez; ilk video başlangıç tarihinde kendiliğinden yayınlanır.

> **Dikkat:** "Günlük Reels" iş akışını elle çalıştırmak **gerçekten yayın yapar**.

Önerim: Instagram biyografine "Yorum cevaplarında yapay zekâ asistanı kullanılır" gibi bir satır ekle. Bot hiçbir zaman kendini sen gibi tanıtmaz; "bot musun?" sorularını cevaplamadan rapora bırakır.

---

## Dosyalar

| Yol | İçerik |
|---|---|
| `data/plan.csv` | 700 günlük plan (esnek slotlar aylık güncellenir) |
| `data/scripts/gunNNN.json` | Video senaryoları (ilk 7 gün elle yazıldı) |
| `data/posts.csv`, `data/state.json` | Yayın kayıtları |
| `data/metrics.csv` | Gönderi metrikleri |
| `data/comments_log.csv` | Tüm yorumlar ve bottaki işlem |
| `data/plan_degisiklikleri.csv` | Aylık adaptasyonun değiştirdiği günler |
| `data/reports/` | Haftalık raporlar (ayrıca Issue olarak açılır) |
| `assets/premade/` | Elle hazırlanmış videolar (senaryoda `"premade"` alanıyla kullanılır) |

## Durdurmak / müdahale etmek
- Her şeyi durdurmak: **Actions** → iş akışını seç → **⋯ → Disable workflow**.
- Sadece yorum cevaplarını kapatmak: `config.yaml` → `yorum.aktif: false`.
- Bir videoyu kendin değiştirmek: ilgili `data/scripts/gunNNN.json` dosyasını düzenle, ya da kendi videonu `assets/premade/` klasörüne koyup senaryoya `"premade": "assets/premade/dosya.mp4"` ekle.

## Yerel test
```bash
pip install -r requirements.txt   # ffmpeg de gerekir
python -m tests.test_bot          # Instagram ve Claude taklit edilerek uçtan uca test
```

Fontlar: DejaVu (lisansı `assets/fonts/DejaVu-LICENSE.txt`). Müzik bot tarafından prosedürel olarak üretilir, telif sorunu yoktur.
