"""Telifsiz, prosedürel ses: enerjik müzik yatağı + ekran olaylarına senkron ses efektleri.
make(path, dur, seed, events=[(t, "whoosh"|"impact"|"ding"|"buzz"|"tick"|"screech"|"horn"|"riser"), ...])"""
import wave
import numpy as np

SR = 44100
PROGS = [[0, 5, 3, 4], [0, 3, 5, 4], [5, 3, 0, 4], [0, 4, 5, 3]]
SCALE = [0, 2, 3, 5, 7, 8, 10]  # doğal minör: daha gergin, "aksiyon" hissi


def _note(deg, root, octv=0):
    return root * 2 ** ((SCALE[deg % 7] + 12 * (deg // 7 + octv)) / 12)


def _env(n, a=0.005, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / max(d, 1e-4))


def _noise(n, rng):
    return rng.standard_normal(n)


def _lp(x, k):
    """Basit tek kutuplu alçak geçiren (k: 0..1, küçük = daha karanlık)."""
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc += k * (x[i] - acc); y[i] = acc
    return y


def _add(out, s0, sig, gain=1.0):
    if s0 >= len(out): return
    n = min(len(sig), len(out) - s0)
    out[s0:s0 + n] += sig[:n] * gain


# ---------------- ses efektleri ----------------
def sfx(kind, rng):
    if kind == "whoosh":
        n = int(0.35 * SR); t = np.arange(n) / SR
        x = _noise(n, rng); f = np.linspace(0.02, 0.35, n) * np.sin(np.pi * t / t[-1])
        y = np.empty(n); acc = 0.0
        for i in range(n): acc += f[i] * (x[i] - acc); y[i] = acc
        return y * np.sin(np.pi * t / t[-1]) * 1.6
    if kind == "impact":
        n = int(0.6 * SR); t = np.arange(n) / SR
        sub = np.sin(2 * np.pi * (45 + 110 * np.exp(-t * 18)) * t) * np.exp(-t * 6)
        crack = _lp(_noise(n, rng), 0.5) * np.exp(-t * 40)
        return sub * 1.0 + crack * 0.6
    if kind == "ding":
        n = int(0.9 * SR); t = np.arange(n) / SR
        return sum(a * np.sin(2 * np.pi * f * t) for f, a in ((1318.5, .5), (1975.5, .3), (2637, .15))) * np.exp(-t * 5) * 0.9
    if kind == "buzz":
        n = int(0.45 * SR); t = np.arange(n) / SR
        sq = np.sign(np.sin(2 * np.pi * 98 * t)) + 0.6 * np.sign(np.sin(2 * np.pi * 103.6 * t))
        return _lp(sq, 0.25) * np.minimum(1, t / 0.01) * np.exp(-t * 3) * 0.55
    if kind == "tick":
        n = int(0.05 * SR); t = np.arange(n) / SR
        return np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 120) * 0.7
    if kind == "screech":
        n = int(0.9 * SR); t = np.arange(n) / SR
        tone = np.sin(2 * np.pi * (2900 + 250 * np.sin(2 * np.pi * 9 * t)) * t)
        hiss = _noise(n, rng) * 0.3
        return (tone * 0.5 + hiss) * np.minimum(1, t / 0.03) * np.exp(-t * 2.2) * 0.45
    if kind == "horn":
        n = int(0.55 * SR); t = np.arange(n) / SR
        h = np.sign(np.sin(2 * np.pi * 420 * t)) + np.sign(np.sin(2 * np.pi * 530 * t))
        return _lp(h, 0.3) * np.minimum(1, t / 0.01) * np.minimum(1, (t[-1] - t) / 0.05) * 0.35
    if kind == "riser":
        n = int(1.2 * SR); t = np.arange(n) / SR
        x = _noise(n, rng); f = np.linspace(0.01, 0.5, n)
        y = np.empty(n); acc = 0.0
        for i in range(n): acc += f[i] * (x[i] - acc); y[i] = acc
        return y * (t / t[-1]) ** 2 * 1.4
    return np.zeros(1)


# ---------------- müzik ----------------
def music(dur, seed):
    rng = np.random.default_rng(seed)
    bpm = int(rng.integers(116, 128)); beat = 60 / bpm; bar = 4 * beat
    root = 110 * 2 ** (int(rng.integers(-2, 4)) / 12)
    prog = PROGS[seed % len(PROGS)]
    n = int(dur * SR); out = np.zeros(n); duck = np.ones(n)
    kick = None
    for b in range(int(dur / bar) + 2):
        deg = prog[b % 4]; s0 = int(b * bar * SR)
        if s0 >= n: break
        # pad (sidechain pompalı)
        L = int(bar * SR); t = np.arange(L) / SR
        pad = sum(np.sin(2 * np.pi * _note(deg + k, root, 1) * t) + 0.25 * np.sin(4 * np.pi * _note(deg + k, root, 1) * t) for k in (0, 2, 4))
        _add(out, s0, pad * 0.05)
        # bas: sekizlik
        for e in range(8):
            Ln = int(beat / 2 * SR); tt = np.arange(Ln) / SR
            f = _note(deg, root, -1) * (2 if e % 4 == 3 else 1)
            bs = np.tanh(2.5 * np.sin(2 * np.pi * f * tt)) * _env(Ln, 0.003, 0.12)
            _add(out, s0 + int(e * beat / 2 * SR), bs * 0.16)
        # arp (ikinci yarıdan itibaren hareket)
        if b % 2 == 1:
            for e in range(16):
                Ln = int(beat / 4 * SR); tt = np.arange(Ln) / SR
                f = _note(deg + (0, 2, 4, 7)[e % 4], root, 2)
                _add(out, s0 + int(e * beat / 4 * SR), np.sign(np.sin(2 * np.pi * f * tt)) * _env(Ln, 0.002, 0.05) * 0.03)
    for k in range(int(dur / beat) + 1):
        s0 = int(k * beat * SR)
        if s0 >= n: break
        L = int(0.3 * SR); tt = np.arange(L) / SR
        kick = np.sin(2 * np.pi * (48 + 120 * np.exp(-tt * 35)) * tt) * np.exp(-tt * 9)
        _add(out, s0, kick * 0.55)
        dl = min(int(0.22 * SR), n - s0); duck[s0:s0 + dl] = np.minimum(duck[s0:s0 + dl], 0.45 + 0.55 * (np.arange(dl) / dl))
        if k % 2 == 1:  # snare / clap
            Ls = int(0.2 * SR); ts = np.arange(Ls) / SR
            sn = _lp(rng.standard_normal(Ls), 0.6) * np.exp(-ts * 22) + np.sin(2 * np.pi * 190 * ts) * np.exp(-ts * 30) * 0.4
            _add(out, s0, sn * 0.28)
        for h in (0.5,):  # açık hi-hat
            hs = int((k + h) * beat * SR); Lh = int(0.06 * SR)
            hh = np.diff(rng.standard_normal(Lh + 1)) * np.exp(-np.arange(Lh) / SR * 60)
            _add(out, hs, hh * 0.06)
    return out * duck + 0  # pad pompa


def make(path, dur, seed=0, events=()):
    rng = np.random.default_rng(seed + 1000)
    n = int(dur * SR)
    m = music(dur, seed)[:n]
    fx = np.zeros(n); duck = np.ones(n)
    last = {}
    for t, kind in sorted(events):
        if t < 0 or t > dur - 0.05: continue
        if kind in last and t - last[kind] < 0.18: continue  # aynı efekt üst üste binmesin
        last[kind] = t
        s = sfx(kind, rng); s0 = int(t * SR)
        g = {"whoosh": 0.35, "impact": 0.9, "ding": 0.6, "buzz": 0.7, "tick": 0.5, "screech": 0.6, "horn": 0.6, "riser": 0.4}.get(kind, 0.5)
        _add(fx, s0, s, g)
        if kind in ("impact", "buzz", "screech", "horn", "ding"):
            dl = min(int(0.5 * SR), n - s0)
            if dl > 0: duck[s0:s0 + dl] = np.minimum(duck[s0:s0 + dl], 0.5 + 0.5 * (np.arange(dl) / dl))
    mix = m * duck + fx
    fade = int(0.25 * SR); mix[:fade] *= np.linspace(0, 1, fade); mix[-int(0.6 * SR):] *= np.linspace(1, 0, int(0.6 * SR))
    # loudness: RMS hedefi ~ -13 dBFS, yumuşak limiter
    rms = np.sqrt(np.mean(mix ** 2)) + 1e-9
    mix = mix * (10 ** (-14.5 / 20) / rms)
    mix = np.tanh(mix * 1.2) / np.tanh(1.2)
    mix = np.clip(mix * 0.84, -0.84, 0.84)  # AAC sonrası tepe ≈ -1 dBTP
    pcm = (np.stack([mix, mix], axis=1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
