# -*- coding: utf-8 -*-
"""Gönderi metriklerini toplar → data/metrics.csv (gönderi başına en güncel değerler).  python -m bot.insights"""
import csv, datetime as dt, logging
from .config import DATA, today, state

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("insights")
FIELDS = ["gun_no", "tarih", "sutun", "sablon", "konu", "media_id", "views", "reach", "likes", "comments", "saved", "shares",
          "total_interactions", "ig_reels_avg_watch_time", "etkilesim_orani", "kaydetme_orani", "guncelleme"]


def load():
    p = DATA / "metrics.csv"
    if not p.exists(): return {}
    with open(p, encoding="utf-8") as f: return {r["media_id"]: r for r in csv.DictReader(f)}


def save(rows):
    with open(DATA / "metrics.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader()
        for r in sorted(rows.values(), key=lambda r: (0, int(r["gun_no"])) if str(r["gun_no"]).isdigit() else (1, 0)): w.writerow({k: r.get(k, "") for k in FIELDS})


def num(x):
    try: return float(x)
    except (TypeError, ValueError): return 0.0


def run(client=None, max_age_days=35):
    from .ig import IG
    ig = client or IG(); st = state(); rows = load(); n = 0
    for p in st["yayinlar"].values():
        age = (today() - dt.date.fromisoformat(p["tarih"])).days
        if age < 1 or age > max_age_days: continue
        try: m = ig.insights(p["media_id"])
        except Exception as ex: log.warning("%s: %s", p["media_id"], ex); continue
        v = num(m.get("views")) or num(m.get("reach"))
        inter = num(m.get("likes")) + num(m.get("comments")) + num(m.get("saved")) + num(m.get("shares"))
        rows[p["media_id"]] = {**{k: p.get(k, "") for k in ("gun_no", "tarih", "sutun", "sablon", "konu", "media_id")}, **m,
                               "etkilesim_orani": round(inter / v, 4) if v else "", "kaydetme_orani": round(num(m.get("saved")) / v, 4) if v else "",
                               "guncelleme": today().isoformat()}
        n += 1
    save(rows); log.info("%s gönderi güncellendi.", n)


if __name__ == "__main__":
    run()
