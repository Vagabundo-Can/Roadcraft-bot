# -*- coding: utf-8 -*-
"""Yorum izleme ve cevaplama.  python -m bot.comments"""
import datetime as dt, json, logging, os, re
from .config import CFG, DATA, today, state, save_state, append_csv
from . import safety

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("comments")
LOG_FIELDS = ["zaman", "gun_no", "media_id", "comment_id", "kategori", "yorum", "cevap", "islem", "permalink"]
SPAM = re.compile(r"(https?://|www\.|wa\.me|t\.me/|dm for promo|takipçi sat|follow back|onlyfans)", re.I)


def classify(llm, post, items):
    user = (f"Gönderi konusu: {post.get('konu')} (seri: {post.get('sutun')})\n"
            "Yorumlar (JSON):\n" + json.dumps([{"id": c["id"], "yorum": c["text"]} for c in items], ensure_ascii=False) +
            '\nHer yorum için: [{"id": "...", "kategori": "...", "cevap": "..." veya ""}]')
    out = llm.ask_json(safety.YORUM_SISTEM, user, max_tokens=3000, temperature=0.5)
    return {o["id"]: o for o in out if isinstance(o, dict) and "id" in o}


def run(client=None, llm=None):
    cfg = CFG["yorum"]
    if not cfg.get("aktif"): return
    st = state(); handled = set(st.get("cevaplanan_yorumlar", []))
    key = today().isoformat(); used = st.setdefault("gunluk_cevap", {}).get(key, 0)
    budget = min(cfg["calisma_basina_en_fazla"], cfg["gunluk_en_fazla"] - used)
    if budget <= 0: log.info("Günlük cevap sınırı doldu."); return
    from .ig import IG
    ig = client or IG()
    if llm is None:
        from . import llm as llm_; llm = llm_
    me = (ig.me() or {}).get("username", "")
    cutoff = today() - dt.timedelta(days=cfg["son_kac_gun"])
    posts = [p for p in st["yayinlar"].values() if dt.date.fromisoformat(p["tarih"]) >= cutoff]
    posts.sort(key=lambda p: p["tarih"], reverse=True)
    replied = 0
    for p in posts:
        if replied >= budget: break
        try: cs = ig.comments(p["media_id"])
        except Exception as ex: log.warning("Yorumlar alınamadı %s: %s", p["media_id"], ex); continue
        new = [c for c in cs if c["id"] not in handled and c.get("username") != me
               and not any(r.get("username") == me for r in (c.get("replies") or {}).get("data", []))]
        if not new: continue
        spam = [c for c in new if SPAM.search(c.get("text", ""))]
        rest = [c for c in new if c not in spam]
        for c in spam:
            act = "gizlendi" if cfg.get("spam_gizle") else "spam"
            if cfg.get("spam_gizle"):
                try: ig.hide(c["id"])
                except Exception as ex: act = f"gizlenemedi: {ex}"
            _log(p, c, "spam", "", act); handled.add(c["id"])
        for i in range(0, len(rest), 20):
            chunk = rest[i:i + 20]
            try: res = classify(llm, p, chunk)
            except Exception as ex: log.warning("Sınıflandırma hatası: %s", ex); break
            for c in chunk:
                r = res.get(c["id"], {"kategori": "emin_degil", "cevap": ""})
                kat, cev = r.get("kategori", "emin_degil"), (r.get("cevap") or "").strip()
                if kat in cfg["cevaplanmayan"] or kat in ("spam", "cevapsiz_gec") or not cev:
                    _log(p, c, kat, "", "rapor" if kat in cfg["cevaplanmayan"] else "geçildi")
                    handled.add(c["id"]); continue
                if replied >= budget:
                    continue  # bütçe doldu: bir sonraki çalışmada cevaplanır
                if safety.YASAK.search(cev) or len(cev) > 300:
                    _log(p, c, kat, cev, "engellendi"); handled.add(c["id"]); continue
                cev = cev + (cfg.get("cevap_imzasi") or "")
                try:
                    ig.reply(c["id"], cev); replied += 1; _log(p, c, kat, cev, "cevaplandı")
                except Exception as ex:
                    _log(p, c, kat, cev, f"hata: {ex}")
                handled.add(c["id"])
    st["cevaplanan_yorumlar"] = list(handled)[-20000:]
    st["gunluk_cevap"] = {key: used + replied}
    save_state(st)
    log.info("%s cevap gönderildi.", replied)


def _log(p, c, kat, cev, islem):
    append_csv(DATA / "comments_log.csv", LOG_FIELDS, {
        "zaman": dt.datetime.utcnow().isoformat(timespec="seconds"), "gun_no": p["gun_no"], "media_id": p["media_id"],
        "comment_id": c["id"], "kategori": kat, "yorum": c.get("text", "")[:500], "cevap": cev, "islem": islem,
        "permalink": p.get("permalink", "")})


if __name__ == "__main__":
    run()
