# -*- coding: utf-8 -*-
"""İçerik sınırları, LLM sistem talimatları ve doğrulayıcılar."""
import re

SINIRLAR = """Sen, Türkiye'de motosiklet ileri sürüş eğitmeni olmaya hazırlanan bir eğitmenin Instagram hesabı için içerik yazıyorsun.
Kaynak çerçeve: Motorcycle Roadcraft (İngiltere polisi sürüş sistemi: IPSGA – Bilgi, Pozisyon, Hız, Vites, Hızlanma).
Türkiye SAĞDAN trafiktir: Roadcraft'taki sol/sağ konumlandırma önerilerini aynala.

DIŞ SINIR: Sadece motosiklet eğitimi ve sürüş güvenliği. Şunlar ASLA yok:
- Hız, stunt, wheelie, drift övgüsü; yasa dışı davranışın teşviki
- Trafikte kurgulanmış tehlike, kişi/marka/kurum karalama, siyaset, din, eğitim dışı trend
- Hukuki, sigorta, tıbbi tavsiye; ceza miktarı gibi doğrulanmamış rakam
- Emin olmadığın teknik iddia. Tartışmalı bir konuda en temkinli ve yaygın kabul gören yaklaşımı yaz.
- Kesin rakam (ör. fren mesafesi metre) ancak çok yaygın kabul gören kurallarda (2 sn kuralı gibi).
Dil: Türkçe, sade, akranla konuşur gibi ama otoriter; emoji yok (açıklama metninde en fazla 1). Ünlem az.
Videolarda kısa cümleler: ekrana sığmalı."""

SCHEMA = {
 "dogru_yanlis": '{"sablon":"dogru_yanlis","kanca":"≤8 kelime","yanlis":{"durum":"≤22 kelime yanlış davranış","sonuc":"≤4 kelime, ör. RAMAK KALA!"},"dogru":{"adimlar":["2-4 adım, her biri ≤8 kelime"]},"kural":"≤14 kelime tek cümle","sahne":SAHNE,"caption":"2-4 cümle + soru","hashtags":["2-4 konuya özel"]}',
 "teknik": '{"sablon":"teknik","kanca":"≤8 kelime","baslik":"konu","hata":"≤18 kelime yaygın hata","adimlar":["2-4 adım ≤10 kelime"],"ipucu":"≤22 kelime","caption":"...","hashtags":[...]}',
 "quiz": '{"sablon":"quiz","kanca":"≤6 kelime","soru":"≤26 kelime somut durum + soru","secenekler":{"A":"≤8 kelime","B":"≤8 kelime"},"dogru":"A veya B","sahne":SAHNE,"caption":"cevabı yorumla daveti","hashtags":[...]}',
 "cevap": '{"sablon":"cevap","kanca":"Dünkü sorunun cevabı","soru":"(quiz ile aynı)","secenekler":"(quiz ile aynı)","dogru":"(aynı)","aciklama":["2-3 madde ≤12 kelime"],"kural":"≤14 kelime","caption":"...","hashtags":[...]}',
 "tehlike": '{"sablon":"tehlike","kanca":"≤8 kelime","sahne":SAHNE (3-5 öğenin "tehlike" alanı dolu, ≤9 kelime),"kapanis":"≤12 kelime Roadcraft gözlem dersi","caption":"...","hashtags":[...]}',
 "challenge": '{"sablon":"challenge","kanca":"≤6 kelime","baslik":"drill adı","seviye":"Seviye 1/2/3","duzen":DUZEN,"kurallar":["2-3 madde ≤10 kelime"],"caption":"kapalı ve güvenli alan vurgusu + denemeyi yorumla daveti","hashtags":[...]}',
 "efsane": '{"sablon":"efsane","kanca":"","iddia":"≤8 kelime yaygın inanış","hukum":"EFSANE | GERÇEK | KISMEN","aciklama":["2-3 madde ≤12 kelime"],"caption":"...","hashtags":[...]}',
 "ekipman": '{"sablon":"ekipman","kanca":"≤7 kelime","baslik":"konu","maddeler":["3 madde ≤12 kelime"],"ipucu":"≤18 kelime","caption":"...","hashtags":[...]}',
 "yorum_soru": '{"sablon":"yorum_soru","kanca":"≤8 kelime","soru":"motosikletçilerin sık sorduğu bir soru (≤22 kelime; gerçek yorumlardan gelmiyorsa takipçi sordu deme)","cevap":["2-3 madde ≤12 kelime"],"caption":"...","hashtags":[...]}',
 "mini_sinav": '{"sablon":"mini_sinav","kanca":"≤8 kelime","sorular":[{"s":"≤14 kelime","c":"≤6 kelime"}, ... tam 3 adet],"caption":"...","hashtags":[...]}',
}
SAHNE = ('{"ogeler":[{"tip":"araba|park|kamyon|otobus|yaya|cocuk|bisiklet|top|motosiklet|yan_yol_araba",'
         '"serit":"sag|sol|sag_park|sol_park|kaldirim_sag|kaldirim_sol|yan_yol_sag|yan_yol_sol","y":0.0-1.0 (0=ileride, 1=yakında),'
         '"tehlike":"opsiyonel"}] (en fazla 7 öğe), "kavsak": false veya 0.2-0.7 (yan yol konumu), "yaya_gecidi": false veya 0.1-0.6,'
         ' "yuzey": "normal|islak|yaprak|cakil|mazot"}. İzleyicinin motosikleti her zaman sağ şeritte en altta; sol şerit karşı yön. '
         'yan_yol_* öğeler kavsak doluysa kullanılır ve y değeri kavsak ile aynı olmalı.')
DUZEN = ('{"tip":"slalom","koni":4-8,"aralik_m":4-10} | {"tip":"ofset","koni":5-8,"aralik_m":5-10,"ofset_m":1-3} | '
         '{"tip":"u_donus","genislik_m":5-9,"uzunluk_m":8-14} | {"tip":"sekiz","mesafe_m":6-12} | '
         '{"tip":"fren","fren_noktasi_m":15-30,"durma_kutusu_m":3-6} | {"tip":"koridor","genislik_m":0.8-1.5,"uzunluk_m":10-20} | '
         '{"tip":"spiral","yaricap_m":4-8,"koni":6-10}')

YASAK = re.compile(r"\b(wheelie|drift|stunt|tek teker|yarış yap|makas at|polisten kaç|ceza almadan)\b", re.I)


def schema_for(sablon):
    sc = SCHEMA[sablon].replace("SAHNE", SAHNE).replace("DUZEN", DUZEN)
    return sc.replace('"caption"', '"kapak":"≤5 kelime kapak başlığı: merak uyandıran, iddialı ama yanıltmayan; uydurma istatistik yok",'
                      ' "caption"', 1)


def _words(x):
    return len(str(x).split())


def validate(s, sablon):
    """Hata listesi döndürür (boş = geçerli)."""
    e = []
    if s.get("sablon") != sablon: e.append("sablon yanlış")
    blob = str(s)
    if YASAK.search(blob): e.append("sınır dışı ifade")
    need = {"dogru_yanlis": ["kanca", "yanlis", "dogru", "kural"], "teknik": ["baslik", "hata", "adimlar", "ipucu"],
            "quiz": ["soru", "secenekler", "dogru"], "cevap": ["soru", "secenekler", "dogru", "aciklama", "kural"],
            "tehlike": ["sahne"], "challenge": ["baslik", "duzen", "kurallar"], "efsane": ["iddia", "hukum", "aciklama"],
            "ekipman": ["baslik", "maddeler"], "yorum_soru": ["soru", "cevap"], "mini_sinav": ["sorular"]}[sablon]
    for k in need:
        if not s.get(k): e.append(f"eksik: {k}")
    if e: return e
    if sablon in ("quiz", "cevap"):
        if s["dogru"] not in s["secenekler"]: e.append("dogru seçenek yok")
        if _words(s["soru"]) > 34: e.append("soru uzun")
    if sablon == "dogru_yanlis":
        if not 2 <= len(s["dogru"].get("adimlar", [])) <= 4: e.append("adım sayısı")
        if _words(s["yanlis"].get("durum", "")) > 28: e.append("durum uzun")
    if sablon == "tehlike":
        hz = [o for o in s["sahne"].get("ogeler", []) if o.get("tehlike")]
        if not 2 <= len(hz) <= 5: e.append("tehlike sayısı 2-5 olmalı")
    if sablon == "mini_sinav" and len(s["sorular"]) != 3: e.append("3 soru olmalı")
    if sablon == "efsane" and str(s["hukum"]).upper() not in ("EFSANE", "GERÇEK", "KISMEN"): e.append("hüküm")
    if sablon == "challenge" and s["duzen"].get("tip") not in ("slalom", "ofset", "u_donus", "kutu", "sekiz", "fren", "koridor", "spiral"): e.append("düzen tipi")
    if _words(s.get("caption", "")) > 120: e.append("caption uzun")
    return e


YORUM_SISTEM = SINIRLAR + """

Görevin: Bu hesabın gönderilerine gelen yorumları sınıflandırıp, uygunsa hesap sahibinin ağzından kısa bir cevap yazmak.
Kategoriler: soru, tesekkur, itiraz, tehlikeli_ovgu, egitim_talebi, hukuki, kaza_yaralanma, hakaret, spam, emin_degil, cevapsiz_gec
Kurallar:
- soru: 1-2 cümle, Roadcraft'a dayalı net cevap. Uzun konuysa "Bunu bir videoda detaylı anlatacağım" ekle.
- tesekkur: çok kısa, samimi, tekrarlamayan bir cevap (her seferinde aynı kalıp olmasın).
- itiraz: teşekkür + tek cümle gerekçe; tartışmaya girme.
- tehlikeli_ovgu (hız/stunt övgüsü vb.): yargılamadan güvenli davranışı tek cümleyle hatırlat.
- egitim_talebi: hesabı takip etmesini ve gönderileri kaydetmesini öner; ücret, tarih, yer verme.
- hukuki, kaza_yaralanma, hakaret, spam, emin_degil: cevap YAZMA (cevap alanı boş).
- cevapsiz_gec: sadece emoji, etiketleme vb. — cevap yazma.
- Emin olmadığın teknik bir şey sorulursa: emin_degil.
- Kişisel bilgi, iletişim, fiyat, randevu verme. Konuyla ilgisiz şey yazma.
- Asla insan olduğunu ya da hesap sahibinin kendisi olduğunu iddia etme; "bot musun / sen mi yazıyorsun" gibi sorular → emin_degil.
- Cevap ≤ 220 karakter. Kullanıcı adını yazma."""
