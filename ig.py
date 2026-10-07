"""Instagram API (Instagram Login, graph.instagram.com) istemcisi.
Gerekli izinler: instagram_business_basic, instagram_business_content_publish,
instagram_business_manage_comments, instagram_business_manage_insights."""
import os, time, requests

API = os.environ.get("IG_API_BASE", "https://graph.instagram.com")
VER = os.environ.get("IG_API_VERSION", "v23.0")


class IGError(RuntimeError):
    pass


class IG:
    def __init__(self, token=None, user_id=None, session=None):
        self.token = token or os.environ["IG_ACCESS_TOKEN"]
        self.user_id = user_id or os.environ.get("IG_USER_ID") or "me"
        self.s = session or requests.Session()

    def _req(self, method, path, **params):
        url = path if path.startswith("http") else f"{API}/{VER}/{path.lstrip('/')}"
        params["access_token"] = self.token
        for attempt in range(4):
            r = self.s.request(method, url, params=params if method == "GET" else None,
                               data=params if method != "GET" else None, timeout=60)
            if r.status_code < 500 and r.status_code != 429:
                break
            time.sleep(5 * (attempt + 1))
        try:
            j = r.json()
        except ValueError:
            raise IGError(f"{r.status_code} {r.text[:300]}")
        if r.status_code >= 400 or "error" in j:
            raise IGError(f"{r.status_code} {j.get('error', j)}")
        return j

    # --- hesap ---
    def me(self):
        return self._req("GET", "me", fields="user_id,username")

    def publishing_limit(self):
        return self._req("GET", f"{self.user_id}/content_publishing_limit", fields="quota_usage,config")

    # --- yayın ---
    def publish_reel(self, video_url, caption, wait_s=600, poll=20):
        c = self._req("POST", f"{self.user_id}/media", media_type="REELS", video_url=video_url, caption=caption)
        cid = c["id"]
        t0 = time.time()
        while True:
            st = self._req("GET", cid, fields="status_code,status")
            code = st.get("status_code")
            if code == "FINISHED":
                break
            if code in ("ERROR", "EXPIRED"):
                raise IGError(f"Konteyner {code}: {st.get('status')}")
            if time.time() - t0 > wait_s:
                raise IGError("Konteyner zaman aşımı")
            time.sleep(poll)
        m = self._req("POST", f"{self.user_id}/media_publish", creation_id=cid)
        mid = m["id"]
        info = self._req("GET", mid, fields="id,permalink,timestamp")
        return {"container_id": cid, "media_id": mid, "permalink": info.get("permalink", "")}

    # --- yorumlar ---
    def comments(self, media_id):
        out, j = [], self._req("GET", f"{media_id}/comments",
                                fields="id,text,username,timestamp,like_count,replies{id,username,text}")
        while True:
            out += j.get("data", [])
            nxt = j.get("paging", {}).get("next")
            if not nxt:
                return out
            j = self.s.get(nxt, timeout=60).json()

    def reply(self, comment_id, message):
        return self._req("POST", f"{comment_id}/replies", message=message)

    def hide(self, comment_id, hide=True):
        return self._req("POST", comment_id, hide="true" if hide else "false")

    # --- metrikler ---
    REEL_METRICS = ["views", "reach", "likes", "comments", "saved", "shares", "total_interactions",
                    "ig_reels_avg_watch_time", "ig_reels_video_view_total_time"]

    def insights(self, media_id):
        res = {}
        try:
            j = self._req("GET", f"{media_id}/insights", metric=",".join(self.REEL_METRICS))
            for m in j.get("data", []):
                res[m["name"]] = (m.get("values") or [{}])[0].get("value", m.get("total_value", {}).get("value"))
        except IGError:
            # Bir metrik desteklenmiyorsa tek tek dene
            for name in self.REEL_METRICS:
                try:
                    j = self._req("GET", f"{media_id}/insights", metric=name)
                    m = j["data"][0]; res[name] = (m.get("values") or [{}])[0].get("value")
                except (IGError, KeyError, IndexError):
                    pass
        return res

    # --- token ---
    def refresh_token(self):
        j = self._req("GET", f"{API}/refresh_access_token", grant_type="ig_refresh_token")
        return j["access_token"], j.get("expires_in")
