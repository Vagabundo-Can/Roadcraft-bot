# -*- coding: utf-8 -*-
"""Günlük yayın.  python -m bot.publish render   → out/site/ (video) + out/today.json
                   python -m bot.publish post URL → Instagram'a Reels olarak yayınlar"""
import json, os, sys, logging, shutil
from .config import CFG, ROOT, OUT, DATA, today, day_no, load_plan, state, save_state, append_csv
from . import scripts, render

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("publish")


def caption_for(s, row):
    tags = []
    for t in (s.get("hashtags") or []) + CFG["yayin"]["sabit_hashtagler"]:
        t = t if t.startswith("#") else "#" + t
        if t.lower() not in [x.lower() for x in tags]: tags.append(t)
    parts = [s.get("caption") or f"{row['konu']}. {row['ana_mesaj']}"]
    if CFG["yayin"].get("imza"): parts.append(CFG["yayin"]["imza"])
    parts.append(" ".join(tags[:12]))
    return "\n\n".join(parts)[:2150]


def cmd_render():
    d = today(); n = day_no(d); st = state()
    if n < 1 or n > 700:
        log.info("Plan dışı gün (%s). Çıkılıyor.", n); return write_today(None)
    if str(n) in st["yayinlar"]:
        log.info("Gün %s zaten yayınlandı.", n); return write_today(None)
    plan = load_plan(); row = plan[n]
    llm = None
    if os.environ.get("ANTHROPIC_API_KEY"):
        from . import llm as llm_
        llm = llm_
    s = scripts.ensure(n, plan, llm)
    if row["sablon"] == "quiz" and n + 1 in plan:   # cevabı hemen sabitle
        scripts.ensure(n + 1, plan, llm)
    site = OUT / "site" / "v"; site.mkdir(parents=True, exist_ok=True)
    name = f"gun{n:03d}.mp4"; vp = site / name
    if s.get("premade") and (ROOT / s["premade"]).exists():
        render.add_music(ROOT / s["premade"], vp, seed=n)
    else:
        render.render(s, vp, seed=n)
    (OUT / "site" / "index.html").write_text("<!doctype html><title>roadcraft-bot</title>ok", encoding="utf-8")
    write_today({"gun_no": n, "tarih": d.isoformat(), "dosya": f"v/{name}", "caption": caption_for(s, row),
                 "sablon": row["sablon"], "sutun": row["sutun"], "konu": row["konu"], "yedek": bool(s.get("_yedek"))})


def write_today(obj):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "today.json").write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    gh = os.environ.get("GITHUB_OUTPUT")
    if gh:
        with open(gh, "a") as f: f.write(f"var={'1' if obj else '0'}\n")


def cmd_post(base_url, client=None):
    t = json.loads((OUT / "today.json").read_text(encoding="utf-8"))
    if not t: log.info("Yayınlanacak bir şey yok."); return
    st = state(); n = t["gun_no"]
    if str(n) in st["yayinlar"]: log.info("Zaten yayınlandı."); return
    from .ig import IG
    ig = client or IG()
    url = base_url.rstrip("/") + "/" + t["dosya"]
    log.info("Yayınlanıyor: %s", url)
    res = ig.publish_reel(url, t["caption"])
    rec = {**res, "gun_no": n, "tarih": t["tarih"], "sablon": t["sablon"], "sutun": t["sutun"], "konu": t["konu"], "yedek": t["yedek"]}
    st["yayinlar"][str(n)] = rec; save_state(st)
    append_csv(DATA / "posts.csv", ["gun_no", "tarih", "sutun", "sablon", "konu", "media_id", "permalink", "yedek"], rec)
    log.info("Yayınlandı: %s", res.get("permalink"))


if __name__ == "__main__":
    if sys.argv[1] == "render": cmd_render()
    elif sys.argv[1] == "post": cmd_post(sys.argv[2])
