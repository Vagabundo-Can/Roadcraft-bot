"""Telifsiz, prosedürel arka plan müziği (kick + hi-hat + akor pad). Her gün farklı seed = farklı akor/tempo."""
import wave
import numpy as np

SR = 44100
PROGS = [[0, 5, 3, 4], [0, 3, 5, 4], [0, 4, 5, 3], [5, 3, 0, 4]]
SCALE = [0, 2, 4, 5, 7, 9, 11]


def _chord(deg, root):
    return [root * 2 ** (SCALE[(deg + k) % 7] / 12 + (deg + k) // 7) for k in (0, 2, 4)]


def make(path, dur, seed=0):
    rng = np.random.default_rng(seed)
    bpm = int(rng.integers(92, 112)); beat = 60 / bpm
    root = 110 * 2 ** (int(rng.integers(0, 7)) / 12)
    prog = PROGS[seed % len(PROGS)]
    n = int(dur * SR); t = np.arange(n) / SR; out = np.zeros(n)
    bar = 4 * beat
    for b in range(int(dur / bar) + 1):
        f = _chord(prog[b % 4], root); s0 = int(b * bar * SR); s1 = min(n, int((b + 1) * bar * SR))
        if s0 >= n: break
        tt = t[s0:s1] - b * bar
        env = np.minimum(1, tt / 0.3) * np.minimum(1, (bar - tt) / 0.3)
        out[s0:s1] += sum(np.sin(2 * np.pi * fr * tt) + 0.3 * np.sin(4 * np.pi * fr * tt) for fr in f) * env * 0.07
        bs = _chord(prog[b % 4], root / 2)[0]
        out[s0:s1] += np.sin(2 * np.pi * bs * tt) * env * 0.10
    for k in range(int(dur / beat) + 1):
        s0 = int(k * beat * SR)
        if s0 >= n: break
        L = min(int(0.25 * SR), n - s0); tt = np.arange(L) / SR
        out[s0:s0 + L] += np.sin(2 * np.pi * (50 + 90 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 14) * 0.35
        h0 = int((k + 0.5) * beat * SR)
        if h0 < n:
            Lh = min(int(0.05 * SR), n - h0)
            out[h0:h0 + Lh] += rng.standard_normal(Lh) * np.exp(-np.arange(Lh) / SR * 90) * 0.05
    fade = int(0.8 * SR)
    out[:fade] *= np.linspace(0, 1, fade); out[-fade:] *= np.linspace(1, 0, fade)
    out = out / (np.max(np.abs(out)) + 1e-9) * 0.5
    pcm = (np.stack([out, out], axis=1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
