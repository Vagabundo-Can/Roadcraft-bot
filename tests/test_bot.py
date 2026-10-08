"""Uçtan uca kuru test: Instagram ve Claude API taklit edilir.  python -m tests.test_bot"""
import json, os, re, shutil, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp()); shutil.copytree(ROOT, TMP / "repo", ignore=shutil.ignore_patterns("out", ".git"))
os.chdir(TMP / "repo"); sys.path.insert(0, str(TMP / "repo"))
for f in (TMP / "repo/data").glob("*.csv"):
    if f.name != "plan.csv": f.unlink()
(TMP / "repo/data/state.json").write_text('{"yayinlar": {}, "cevaplanan_yorumlar": [], "gunluk_cevap": {}}')

SAMPLES = {p.stem: json.loads(p.read_text()) for p in (TMP / "repo/tests/samples").glob("*.json")}
for n in range(2, 8):
    s = json.loads((TMP / f"repo/data/scripts/gun{n:03d}.json").read_text()); SAMPLES.setdefault(s["sablon"], s)

class FakeLLM:
    calls = []
    @staticmethod
    def ask_json(system, user, **kw):
        FakeLLM.calls.append(system[:40])
        if "editörüsün" in system: return {"onay": True}
        if "yorumları sınıflandırıp" in system:
            items = json.loads(user.split("Yorumlar (JSON):\n")[1].split("\nHer yorum için")[0])
            out = []
            for it in items:
                y = it["yorum"].lower()
                if "avukat" in y: out.append({"id": it["id"], "kategori": "hukuki", "cevap": ""})
                elif "?" in y: out.append({"id": it["id"], "kategori": "soru", "cevap": "Kısa bakış, gevşek kollar."})
                else: out.append({"id": it["id"], "kategori": "tesekkur", "cevap": "Teşekkürler, iyi sürüşler!"})
            return out
        if "ESNEK slotları" in system:
            d = json.loads(user); return [{"gun_no": s["gun_no"], "sablon": "efsane", "seri": "Efsane", "konu": f"Test konusu {s['gun_no']}",
                                           "kanca": "Test kanca", "ana_mesaj": "Test mesaj", "roadcraft": "Gözlem"} for s in d["esnek_slotlar"]]
        m = re.search(r"Şablon: (\w+)", user); t = m.group(1)
        s = dict(SAMPLES[t]); s["caption"] = "Test açıklama"; return s

class FakeIG:
    def __init__(self): self.posted, self.replies, self.hidden = [], [], []
    def me(self): return {"username": "hesabim"}
    def publish_reel(self, url, caption, **kw):
        assert kw.get("cover_url", "").endswith(".jpg") or kw == {}, kw
        self.posted.append((url, caption)); n = len(self.posted)
        return {"container_id": f"c{n}", "media_id": f"m{n}", "permalink": f"https://instagram.com/reel/x{n}"}
    def comments(self, mid):
        return [{"id": mid + "_1", "text": "Harika anlatım", "username": "a"},
                {"id": mid + "_2", "text": "Omuz kontrolünde motor kaymıyor mu?", "username": "b"},
                {"id": mid + "_3", "text": "Avukatım dava açalım diyor", "username": "c"},
                {"id": mid + "_4", "text": "takipçi sat www.spam.com", "username": "d"},
                {"id": mid + "_5", "text": "Zaten cevapladım", "username": "e", "replies": {"data": [{"username": "hesabim"}]}}]
    def publish_story(self, u): return "s"
    def reply(self, cid, msg): self.replies.append((cid, msg))
    def hide(self, cid): self.hidden.append(cid)
    def insights(self, mid): return {"views": 1000, "reach": 800, "likes": 60, "comments": 8, "saved": 25, "shares": 7}

from bot import publish, comments, insights, adapt, scripts, config
ig = FakeIG()
for d in ["2026-10-12", "2026-10-14", "2026-10-16"]:
    os.environ["BOT_DATE"] = d
    publish.cmd_render(); publish.cmd_post("https://ornek.github.io/roadcraft-bot", client=ig)
    t = json.loads(Path("out/today.json").read_text()); assert Path("out/site/" + t["dosya"]).stat().st_size > 100000, "video küçük"
publish.cmd_render(); t = json.loads(Path("out/today.json").read_text()); assert t is None, "aynı gün iki kez"
print("Yayın:", [p[0].split('/')[-1] for p in ig.posted]); print("Açıklama örneği:\n", ig.posted[0][1][:300])

os.environ["BOT_DATE"] = "2026-10-17"
comments.run(client=ig, llm=FakeLLM)
print("Cevaplar:", len(ig.replies), "Gizlenen:", len(ig.hidden))
assert len(ig.replies) == 6 and len(ig.hidden) == 3
comments.run(client=ig, llm=FakeLLM); assert len(ig.replies) == 6, "aynı yorum iki kez cevaplandı"
insights.run(client=ig); m = insights.load(); assert len(m) == 3; print("Metrik:", list(m.values())[0]["etkilesim_orani"])

os.environ["BOT_DATE"] = "2026-10-18"
adapt.weekly(llm=FakeLLM)
made = sorted(p.name for p in config.SCRIPTS.glob("gun*.json")); print("Senaryolar:", made[:3], "...", made[-1], len(made))
n0 = config.day_no(config.today()) + 1
for n in range(n0, n0 + 13):
    s = scripts.get(n); assert s and not s.get("_yedek"), n
    if s["sablon"] == "cevap": assert s["soru"] == scripts.get(n - 1)["soru"]
os.environ["BOT_DATE"] = "2026-10-31"
before = config.load_plan(); adapt.monthly(llm=FakeLLM); after = config.load_plan()
ch = [n for n in before if before[n]["konu"] != after[n]["konu"]]
assert ch and all(before[n]["esnek"] == "Esnek" for n in ch); print("Değişen esnek gün:", ch[:6], len(ch))
r = adapt.report(); print("Rapor:", r.read_text()[:400])
# Render every template once more via fallback (LLM yok)
from bot import render
plan = config.load_plan(); seen = set()
for n, row in plan.items():
    if row["sablon"] in seen: continue
    seen.add(row["sablon"]); s = scripts.fallback(row, plan); render.still(s, 3.0, str(TMP / f"fb_{row['sablon']}.png"))
print("Yedek şablonlar render edildi:", sorted(seen))
print("TÜM TESTLER GEÇTİ")
