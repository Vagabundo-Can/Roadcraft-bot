# -*- coding: utf-8 -*-
"""Haftalık: önümüzdeki günlerin senaryoları + haftalık rapor.  python -m bot.adapt weekly
   Aylık: performansa ve yorumlara göre esnek slotları yeniden yazar.  python -m bot.adapt monthly"""
import csv, datetime as dt, json, logging, sys
from collections import Counter, defaultdict
from .config import CFG, DATA, today, day_no, date_of, load_plan, save_plan, append_csv
from . import scripts, safety, insights

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("adapt")
SABLON_SUTUN = {"dogru_yanlis": "Doğru / Yanlış", "teknik": "Teknik Kontrol", "quiz": "Sen Olsan?", "cevap": "Cevap + Kural",
                "tehlike": "Tehlike Avı", "challenge": "Beceri Challenge", "efsane": "Topluluk", "ekipman": "Topluluk",
                "yorum_soru": "Topluluk", "mini_sinav": "Topluluk"}


def comments_since(days):
    p = DATA / "comments_log.csv"
    if not p.exists(): return []
    cut = (dt.datetime.utcnow() - dt.timedelta(days=days)).isoformat()
    with open(p, encoding="utf-8") as f: return [r for r in csv.DictReader(f) if r["zaman"] >= cut]


def performance():
    rows = list(insights.load().values()); A = CFG["adaptasyon"]
    by = defaultdict(list)
    for r in rows:
        if insights.num(r.get("views")) > 0: by[r["sablon"]].append(r)
    allr = [r for v in by.values() for r in v]
    g_er = sum(insights.num(r["etkilesim_orani"]) for r in allr) / len(allr) if allr else 0
    table = {}
    for sb, rs in by.items():
        er = sum(insights.num(r["etkilesim_orani"]) for r in rs) / len(rs)
        sv = sum(insights.num(r["kaydetme_orani"]) for r in rs) / len(rs)
        vw = sum(insights.num(r["views"]) for r in rs) / len(rs)
        oran = er / g_er if g_er else 0
        karar = ("veri az" if len(rs) < A["min_yayin"] else "büyüt" if oran >= A["buyut_esik"] else
                 "formatı değiştir" if oran < A["kucult_esik"] else "koru")
        table[sb] = {"yayin": len(rs), "ort_izlenme": round(vw), "etkilesim": round(er, 4), "kaydetme": round(sv, 4),
                     "genele_oran": round(oran, 2), "karar": karar}
    return table, g_er


def top_questions(days=7, k=8):
    qs = [r["yorum"] for r in comments_since(days) if r["kategori"] in ("soru", "emin_degil") and len(r["yorum"]) > 15]
    return qs[:60]


def weekly(llm=None):
    plan = load_plan(); n0 = max(1, day_no(today()) + 1)
    if llm is None:
        from . import llm as llm_; llm = llm_
    qs = top_questions()
    for n in range(n0, min(700, n0 + CFG["adaptasyon"]["senaryo_ileri_gun"] - 1) + 1):
        row = plan[n]; extra = ""
        if row["sablon"] == "yorum_soru" and qs:
            extra = ("Bu hafta takipçilerden gelen sorular (birini seç, anonimleştir, eğitim sınırı içinde cevapla):\n- " + "\n- ".join(qs[:20]))
        scripts.ensure(n, plan, llm, extra=extra)
    report()


def report():
    from .config import state
    st = state(); t = today(); wk = t - dt.timedelta(days=7)
    posts = sorted([p for p in st["yayinlar"].values() if dt.date.fromisoformat(p["tarih"]) > wk], key=lambda p: p["tarih"])
    met = insights.load()
    lines = [f"# Haftalık rapor — {t.isoformat()}", "", "## Bu haftanın gönderileri", "",
             "| Gün | Tarih | Seri | Konu | İzlenme | Etkileşim | Kaydetme |", "|---|---|---|---|---|---|---|"]
    for p in posts:
        m = met.get(p["media_id"], {})
        lines.append(f"| {p['gun_no']} | {p['tarih']} | {p['sutun']} | [{p['konu']}]({p.get('permalink','')}) | {m.get('views','–')} | "
                     f"{_pct(m.get('etkilesim_orani'))} | {_pct(m.get('kaydetme_orani'))} |")
    tb, g = performance()
    lines += ["", f"## Şablon performansı (genel etkileşim {_pct(g)})", "", "| Şablon | Yayın | Ort. izlenme | Etkileşim | Kaydetme | Genele oran | Karar |", "|---|---|---|---|---|---|---|"]
    for sb, r in sorted(tb.items(), key=lambda x: -x[1]["genele_oran"]):
        lines.append(f"| {sb} | {r['yayin']} | {r['ort_izlenme']} | {_pct(r['etkilesim'])} | {_pct(r['kaydetme'])} | {r['genele_oran']}x | {r['karar']} |")
    cs = comments_since(7); cnt = Counter(r["islem"] for r in cs)
    lines += ["", "## Yorumlar", "", f"Cevaplanan: {cnt.get('cevaplandı', 0)} · Rapora düşen: {cnt.get('rapor', 0)} · "
              f"Spam/gizlenen: {cnt.get('gizlendi', 0) + cnt.get('spam', 0)} · Engellenen taslak: {cnt.get('engellendi', 0)}"]
    flag = [r for r in cs if r["islem"] == "rapor"]
    if flag:
        lines += ["", "### Otomatik cevaplanmayanlar (istersen sen bak)", ""]
        for r in flag[:40]: lines.append(f"- **{r['kategori']}** · [gönderi]({r['permalink']}) · {r['yorum'][:200]}")
    yedek = [p for p in posts if p.get("yedek")]
    if yedek: lines += ["", f"Not: {len(yedek)} gönderi yedek senaryoyla üretildi (API hatası)."]
    (DATA / "reports").mkdir(exist_ok=True)
    path = DATA / "reports" / f"{t.isoformat()}.md"; path.write_text("\n".join(lines), encoding="utf-8")
    log.info("Rapor: %s", path)
    return path


def _pct(x):
    try: return f"{float(x) * 100:.1f}%"
    except (TypeError, ValueError): return "–"


def monthly(llm=None):
    plan = load_plan(); n0 = max(1, day_no(today()) + 2)
    n1 = min(700, n0 + CFG["adaptasyon"]["esnek_ileri_gun"] - 1)
    flex = [plan[n] for n in range(n0, n1 + 1) if plan[n]["esnek"] == "Esnek"]
    if not flex: log.info("Esnek slot yok."); return
    if llm is None:
        from . import llm as llm_; llm = llm_
    tb, g = performance()
    themes = Counter(r["kategori"] for r in comments_since(30))
    qs = top_questions(30)
    recent = [plan[n]["konu"] for n in range(max(1, n0 - 60), n1 + 1)]
    sys_ = safety.SINIRLAR + """

Görevin: Takvimdeki ESNEK slotları, izleyici verisine göre yeniden yazmak. Kurallar:
- Sadece verilen gün numaralarını değiştir. Her biri için şablonu şu listeden seç: dogru_yanlis, teknik, tehlike, challenge, efsane, ekipman, yorum_soru, mini_sinav
  (quiz ve cevap seçme; onlar sabit eşlerle çalışır).
- Performansı "büyüt" olan şablonlara daha çok yer ver, "formatı değiştir" olanlardan kaçın; ama aynı şablonu art arda 3 günden fazla koyma.
- Konular yinelenmemeli (son konular listesi verildi), ay temasına ve izleyici sorularına uygun olmalı.
- Tüm konular motosiklet eğitimi sınırları içinde kalmalı.
Çıktı: [{"gun_no": n, "sablon": "...", "seri": "kısa seri adı", "konu": "...", "kanca": "≤8 kelime", "ana_mesaj": "≤20 kelime", "roadcraft": "alan"}]"""
    user = json.dumps({"esnek_slotlar": [{"gun_no": int(r["gun_no"]), "gun": r["gun_adi"], "ay_temasi": r["ay_temasi"],
                                          "mevcut": f"{r['sablon']}: {r['konu']}"} for r in flex],
                       "performans": tb, "genel_etkilesim": g, "yorum_kategorileri": themes.most_common(),
                       "izleyici_sorulari": qs[:40], "son_konular": recent}, ensure_ascii=False)
    try:
        out = llm.ask_json(sys_, user, max_tokens=6000, temperature=0.6)
    except Exception as ex:
        log.warning("Aylık adaptasyon başarısız, plan değişmedi: %s", ex); return
    ok_ids = {int(r["gun_no"]) for r in flex}; allowed = set(SABLON_SUTUN) - {"quiz", "cevap"}; changed = 0
    for o in out if isinstance(out, list) else []:
        try: n = int(o["gun_no"])
        except (KeyError, ValueError, TypeError): continue
        if n not in ok_ids or o.get("sablon") not in allowed: continue
        if safety.YASAK.search(json.dumps(o, ensure_ascii=False)): continue
        if not all(str(o.get(k, "")).strip() for k in ("konu", "kanca", "ana_mesaj")): continue
        old = dict(plan[n])
        plan[n].update(sablon=o["sablon"], sutun=SABLON_SUTUN[o["sablon"]], seri=o.get("seri") or plan[n]["seri"], konu=o["konu"],
                       kanca=o["kanca"], ana_mesaj=o["ana_mesaj"], roadcraft=o.get("roadcraft", ""), kaynak_gun="")
        sp = scripts.path(n)
        if sp.exists(): sp.unlink()
        append_csv(DATA / "plan_degisiklikleri.csv", ["tarih", "gun_no", "eski", "yeni"],
                   {"tarih": today().isoformat(), "gun_no": n, "eski": f"{old['sablon']}: {old['konu']}", "yeni": f"{o['sablon']}: {o['konu']}"})
        changed += 1
    save_plan(plan); log.info("%s esnek slot güncellendi.", changed)


if __name__ == "__main__":
    {"weekly": weekly, "monthly": monthly, "report": report}[sys.argv[1]]()
