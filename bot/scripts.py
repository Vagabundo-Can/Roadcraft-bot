# -*- coding: utf-8 -*-
"""Plan satırı -> video senaryosu (JSON). LLM ile üretilir, doğrulanır, ikinci bir LLM geçişiyle denetlenir.
Herhangi bir adım başarısız olursa plan alanlarından güvenli bir yedek senaryo kurulur — yayın asla durmaz."""
import json, logging
from .config import SCRIPTS, load_plan, load_json, save_json
from . import safety

log = logging.getLogger("scripts")


def path(n):
    return SCRIPTS / f"gun{int(n):03d}.json"


def get(n):
    return load_json(path(n), None)


def fallback(row, plan=None):
    """LLM olmadan, plan alanlarından basit ama doğru bir senaryo."""
    t = row["sablon"]; k = row["kanca"]; m = row["ana_mesaj"]; konu = row["konu"]
    base = {"sablon": t, "kanca": k, "caption": f"{konu}. {m}", "hashtags": [], "_yedek": True}
    if t == "dogru_yanlis":
        base.update(yanlis={"durum": k, "sonuc": "RAMAK KALA!"}, dogru={"adimlar": [konu, "Erken gör, erken karar ver"]}, kural=m)
    elif t == "teknik":
        base.update(baslik=konu, hata="Tekniği acele ve gergin uygulamak.", adimlar=["Bakış ileri", "Kollar gevşek", "Yavaş başla, kademeli artır"], ipucu="Önce kapalı alanda, düşük hızda dene.")
    elif t in ("quiz", "cevap"):
        src = (plan or {}).get(int(row["kaynak_gun"] or 0)) if row.get("kaynak_gun") else None
        mesaj = src["ana_mesaj"] if src else m
        base.update(kanca="Doğru mu, yanlış mı?" if t == "quiz" else "Dünkü sorunun cevabı",
                    soru=f"Doğru mu? {mesaj}", secenekler={"A": "Doğru", "B": "Yanlış"}, dogru="A",
                    aciklama=[mesaj], kural=mesaj)
    elif t == "tehlike":
        base.update(sahne={"ogeler": [{"tip": "park", "serit": "sag_park", "y": 0.35, "tehlike": "Park halindeki araç: kapı açılabilir"},
                                       {"tip": "yan_yol_araba", "serit": "yan_yol_sag", "y": 0.55, "tehlike": "Yan yoldan çıkabilecek araç"},
                                       {"tip": "yaya", "serit": "kaldirim_sag", "y": 0.2, "tehlike": "Yola inebilecek yaya"}], "kavsak": 0.55},
                    kapanis="Gözlem uzaktan başlar, tahminle biter.")
    elif t == "challenge":
        base.update(baslik=konu, seviye="", duzen={"tip": "slalom", "koni": 6, "aralik_m": 6},
                    kurallar=["Kapalı ve güvenli alanda dene", "Bakış iki koni ileride", "Ayak yere değmeden tamamla"])
    elif t == "efsane":
        base.update(iddia=konu, hukum="KISMEN", aciklama=[m])
    elif t == "ekipman":
        base.update(baslik=konu, maddeler=[m, "Sürüş öncesi kontrol et", "Şüphedeysen uzmana danış"], ipucu="")
    elif t == "yorum_soru":
        base.update(soru=konu, cevap=[m])
    elif t == "mini_sinav":
        base.update(sorular=[{"s": "Şerit değiştirmeden önceki son bakış?", "c": "Omuz kontrolü"},
                             {"s": "Kuru zeminde en az takip mesafesi?", "c": "2 saniye"},
                             {"s": "Virajda nereye bakarsın?", "c": "Gitmek istediğin yere"}])
    return base


def _context(row, plan, extra=""):
    return (f"Gün {row['gun_no']} · {row['gun_adi']} · Ay teması: {row['ay_temasi']}\n"
            f"Seri: {row['seri']} · Şablon: {row['sablon']}\nKonu: {row['konu']}\nKanca önerisi: {row['kanca']}\n"
            f"Ana mesaj: {row['ana_mesaj']}\nRoadcraft alanı: {row['roadcraft']}\n{extra}")


def generate(row, plan, llm, extra=""):
    t = row["sablon"]
    sys_ = safety.SINIRLAR + "\n\nBir Reels videosunun senaryosunu şu JSON şemasına birebir uyarak yaz:\n" + safety.schema_for(t)
    user = _context(row, plan, extra)
    for attempt in range(2):
        try:
            s = llm.ask_json(sys_, user + ("\nÖnceki deneme hatalı, şemaya ve kelime sınırlarına uy." if attempt else ""))
            s["sablon"] = t
            err = safety.validate(s, t)
            if err:
                log.warning("Gün %s doğrulama: %s", row["gun_no"], err); continue
            rv = llm.ask_json(safety.SINIRLAR + "\n\nSen bir sürüş güvenliği editörüsün. Aşağıdaki senaryoyu denetle: teknik olarak yanlış, "
                              "riskli, sağdan trafiğe uymayan, sınır dışı ya da yanıltıcı bir ifade var mı? "
                              '{"onay": true/false, "sorun": "kısa açıklama", "duzeltilmis": (onay false ise düzeltilmiş tam senaryo JSON, yoksa null)}',
                              json.dumps(s, ensure_ascii=False))
            if rv.get("onay"): return s
            fixed = rv.get("duzeltilmis")
            if fixed and not safety.validate(fixed, t):
                fixed["sablon"] = t; fixed["_duzeltildi"] = rv.get("sorun", ""); return fixed
            log.warning("Gün %s editör reddi: %s", row["gun_no"], rv.get("sorun"))
        except Exception as ex:  # ağ, JSON vb.
            log.warning("Gün %s LLM hatası: %s", row["gun_no"], ex)
    return None


def ensure(n, plan=None, llm=None, force=False, extra=""):
    """Gün n için senaryo yoksa üretir. Quiz üretildiğinde ertesi günün cevap senaryosu da aynı soruyla yazılır."""
    plan = plan or load_plan(); row = plan[int(n)]
    cur = get(n)
    if cur and not force and not (llm and cur.get("_yedek")): return cur  # yedek senaryo varsa LLM ile yeniden dene
    s = None
    if row["sablon"] == "cevap":
        q = get(int(n) - 1)
        if q and q.get("sablon") == "quiz" and llm:
            s = generate(row, plan, llm, extra="Dünkü quiz (soru, seçenekler ve doğru cevap AYNEN korunacak):\n" + json.dumps(
                {k: q[k] for k in ("soru", "secenekler", "dogru")}, ensure_ascii=False))
            if s: s.update({k: q[k] for k in ("soru", "secenekler", "dogru")})
        elif q and q.get("sablon") == "quiz":
            s = fallback(row, plan); s.update({k: q[k] for k in ("soru", "secenekler", "dogru")})
    if s is None and llm:
        ex = extra
        if row.get("kaynak_gun"):
            src = plan.get(int(row["kaynak_gun"]))
            if src: ex += f"\nBu quiz şu dersi pekiştirir: {src['konu']} — {src['ana_mesaj']}"
        s = generate(row, plan, llm, ex)
    if s is None: s = fallback(row, plan)
    save_json(path(n), s)
    return s
