import csv, json, os, datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo
import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SCRIPTS = DATA / "scripts"
PREMADE = ROOT / "assets" / "premade"
OUT = ROOT / "out"
FONTS = ROOT / "assets" / "fonts"

CFG = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
TZ = ZoneInfo(CFG["hesap"]["saat_dilimi"])
START = dt.date.fromisoformat(CFG["hesap"]["baslangic_tarihi"])

PLAN_FIELDS = ["gun_no", "varsayilan_tarih", "gun_adi", "faz", "ay_temasi", "sutun", "seri", "sablon", "konu",
               "kanca", "ana_mesaj", "roadcraft", "esnek", "kaynak_gun"]


def today():
    override = os.environ.get("BOT_DATE")  # test / elle çalıştırma için
    return dt.date.fromisoformat(override) if override else dt.datetime.now(TZ).date()


def day_no(d):
    return (d - START).days + 1


def date_of(n):
    return START + dt.timedelta(days=int(n) - 1)


def load_plan():
    with open(DATA / "plan.csv", encoding="utf-8") as f:
        return {int(r["gun_no"]): r for r in csv.DictReader(f)}


def save_plan(plan):
    with open(DATA / "plan.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=PLAN_FIELDS)
        w.writeheader()
        for n in sorted(plan):
            w.writerow({k: plan[n].get(k, "") for k in PLAN_FIELDS})


def load_json(path, default):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def save_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def state():
    return load_json(DATA / "state.json", {"yayinlar": {}, "cevaplanan_yorumlar": [], "gunluk_cevap": {}})


def save_state(s):
    save_json(DATA / "state.json", s)


def append_csv(path, fields, row):
    p = Path(path); new = not p.exists()
    with open(p, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new: w.writeheader()
        w.writerow({k: row.get(k, "") for k in fields})
