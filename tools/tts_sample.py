"""Türkçe Piper seslerinden örnek üretir → data/ses_dene/*.m4a"""
import subprocess, sys, wave, pathlib
from piper import PiperVoice
TEXT = ("Öğlenki sorunun cevabı: B. Ayna, sol arka çaprazı tam göstermez. "
        "Kör noktadaki araç aynada görünmeyebilir. Şerit değiştirmeden önce: ayna, sinyal, omuz kontrolü. "
        "Sen doğru bildin mi? Yorumlara yaz.")
out = pathlib.Path("data/ses_dene"); out.mkdir(parents=True, exist_ok=True)
for name in sys.argv[1:]:
    m = pathlib.Path(f"voices/{name}.onnx")
    if not m.exists(): print("yok", name); continue
    v = PiperVoice.load(str(m))
    wp = out / f"{name}.wav"
    with wave.open(str(wp), "wb") as w:
        if hasattr(v, "synthesize_wav"): v.synthesize_wav(TEXT, w)
        else: v.synthesize(TEXT, w)
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wp), "-af", "loudnorm=I=-14", "-c:a", "aac", "-b:a", "128k", str(out / f"{name}.m4a")])
    wp.unlink(); print("ok", name)
