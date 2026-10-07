"""Haftalık anahtar kontrolü. Süresiz Sayfa anahtarı kullanıldığı için yenileme gerekmez;
anahtar geçersizleşirse iş akışı hata verir ve GitHub e-posta ile haber verir."""
import logging
from .ig import IG

logging.basicConfig(level=logging.INFO)
if __name__ == "__main__":
    me = IG().check_token()
    logging.info("Anahtar geçerli: @%s", me.get("username"))
