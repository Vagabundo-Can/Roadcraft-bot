"""Instagram uzun ömürlü erişim anahtarını yeniler ve GitHub secret'ını günceller (gh CLI + GH_PAT)."""
import os, subprocess, logging
from .ig import IG

logging.basicConfig(level=logging.INFO)
if __name__ == "__main__":
    tok, exp = IG().refresh_token()
    env = {**os.environ, "GH_TOKEN": os.environ["GH_PAT"]}
    subprocess.run(["gh", "secret", "set", "IG_ACCESS_TOKEN", "--body", tok, "--repo", os.environ["GITHUB_REPOSITORY"]], check=True, env=env)
    logging.info("Anahtar yenilendi, geçerlilik: %s gün", round((exp or 0) / 86400))
