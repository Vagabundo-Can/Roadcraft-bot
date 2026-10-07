"""Claude API (Anthropic Messages API) — ince istemci."""
import json, os, re, time, requests
from .config import CFG

URL = os.environ.get("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages")


def ask(system, user, max_tokens=None, temperature=0.4):
    key = os.environ["ANTHROPIC_API_KEY"]
    body = {"model": CFG["model"]["isim"], "max_tokens": max_tokens or CFG["model"]["max_tokens"],
            "temperature": temperature, "system": system, "messages": [{"role": "user", "content": user}]}
    for attempt in range(4):
        r = requests.post(URL, json=body, timeout=180,
                          headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        if r.status_code in (429, 500, 502, 503, 529):
            time.sleep(10 * (attempt + 1)); continue
        r.raise_for_status()
        return "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text")
    r.raise_for_status()


def ask_json(system, user, **kw):
    txt = ask(system + "\n\nYalnızca geçerli JSON döndür; açıklama, kod bloğu işareti ekleme.", user, **kw)
    m = re.search(r"\{.*\}|\[.*\]", txt, re.S)
    if not m:
        raise ValueError("JSON bulunamadı: " + txt[:200])
    return json.loads(m.group(0))
