"""Original soundtrack for the reels: a 160 BPM trap/hyperpop beat in F minor ("Leo style") plus comic sound effects
that land exactly on the animation events in posts.json (bursts, slams, chat pops, counters, cuts).

Usage: python3 templates/sound.py [id ...]   -> posts/<id>/sound.wav, then muxed into posts/<id>/reel.mp4
Needs numpy, scipy and ffmpeg. Everything is synthesised here: no samples, no third-party music, no licences.
"""
import json
import os
import subprocess
import sys

import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
BPM = 160
BEAT = 60 / BPM
STEP = BEAT / 4
BAR = BEAT * 4
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
rng = np.random.default_rng(7)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def t_(n):
    return np.arange(int(n)) / SR


def env_exp(n, decay):
    return np.exp(-t_(n) / decay)


def filt(x, kind, f, order=2):
    f = np.clip(np.atleast_1d(f), 20, SR / 2 - 100)
    sos = butter(order, f if len(f) > 1 else f[0], btype=kind, fs=SR, output='sos')
    return sosfilt(sos, x)


def sweep_filter(x, kind, f0, f1, chunks=24):
    """Time-varying filter, approximated chunk by chunk (good enough for risers and splashes)."""
    out = np.zeros_like(x)
    edges = np.linspace(0, len(x), chunks + 1).astype(int)
    for i in range(chunks):
        a, b = edges[i], edges[i + 1]
        f = f0 * (f1 / f0) ** (i / max(1, chunks - 1))
        out[a:b] = filt(x[max(0, a - 512):b], kind, f)[a - max(0, a - 512):]
    return out


def noise(n):
    return rng.standard_normal(int(n))


def saw(freq, n, harmonics=24):
    t = t_(n)
    s = np.zeros(int(n))
    for k in range(1, harmonics + 1):
        if freq * k > 9000:
            break
        s += np.sin(2 * np.pi * freq * k * t) / k
    return s * 0.6


# ---------------- drums ----------------
def kick(gain=1.0):
    n = int(0.45 * SR)
    t = t_(n)
    f = 45 + 110 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * env_exp(n, 0.22)
    click = filt(noise(n), 'highpass', 2000) * env_exp(n, 0.004) * 0.4
    return np.tanh(1.6 * (body + click)) * gain


def clap(gain=0.6):
    n = int(0.35 * SR)
    x = filt(noise(n), 'bandpass', [900, 4500])
    e = np.zeros(n)
    for d in (0, 0.011, 0.022):
        i = int(d * SR)
        e[i:] += env_exp(n - i, 0.012 if d < 0.02 else 0.14)
    tone = np.sin(2 * np.pi * 190 * t_(n)) * env_exp(n, 0.05) * 0.5
    return (x * e * 0.8 + tone) * gain


def hat(gain=0.18, open_=False):
    n = int((0.25 if open_ else 0.06) * SR)
    x = filt(noise(n), 'highpass', 7000)
    return x * env_exp(n, 0.09 if open_ else 0.018) * gain


def bass808(freq, dur, gain=0.9, glide_from=None):
    n = int(dur * SR)
    t = t_(n)
    f = np.full(n, freq)
    if glide_from:
        f = freq + (glide_from - freq) * np.exp(-t / 0.06)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.minimum(1, t / 0.005) * np.exp(-t / max(0.25, dur * 0.9))
    return np.tanh(2.6 * x) * gain  # saturation: harmonics so phones can hear it


# ---------------- tonal ----------------
CHORDS = [[53, 56, 60, 65], [49, 53, 56, 60], [56, 60, 63, 68], [51, 55, 58, 63]]  # Fm  Db  Ab  Eb
ROOTS = [41, 37, 44, 39]  # F2 Db2 Ab2 Eb2


def supersaw_chord(notes, dur, cutoff, gain=0.10):
    n = int(dur * SR)
    L = np.zeros(n)
    R = np.zeros(n)
    for m in notes:
        for d, side in ((-0.12, 0), (0.0, 2), (0.12, 1)):
            v = saw(mtof(m + d), n, 18)
            if side in (0, 2):
                L += v
            if side in (1, 2):
                R += v
    a = np.minimum(1, t_(n) / 0.01) * np.minimum(1, (n - np.arange(n)) / (0.05 * SR))
    L = filt(L * a, 'lowpass', cutoff)
    R = filt(R * a, 'lowpass', cutoff)
    return np.stack([L, R]) * gain


def pluck(m, gain=0.12, dur=0.22):
    n = int(dur * SR)
    x = saw(mtof(m), n, 14) * env_exp(n, 0.07)
    return filt(x, 'lowpass', 3500) * gain


# ---------------- comic sound effects ----------------
def impact(gain=1.0):
    n = int(1.4 * SR)
    t = t_(n)
    f = 30 + 70 * np.exp(-t / 0.15)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, 0.5)
    crack = filt(noise(n), 'bandpass', [300, 6000]) * env_exp(n, 0.05)
    return np.tanh(2.0 * (boom * 0.9 + crack * 0.6)) * gain


def klonk(gain=0.8):
    n = int(0.9 * SR)
    t = t_(n)
    parts = [(310, 1), (743, .7), (1187, .5), (1873, .35), (2711, .25)]
    x = sum(a * np.sin(2 * np.pi * f * t) * env_exp(n, 0.25 / (1 + i * .4)) for i, (f, a) in enumerate(parts))
    thud = np.sin(2 * np.pi * 80 * t) * env_exp(n, 0.08)
    return np.tanh(1.2 * (x * 0.5 + thud)) * gain


def splash(gain=0.9):
    n = int(1.1 * SR)
    x = sweep_filter(noise(n), 'lowpass', 9000, 600) * env_exp(n, 0.3)
    plop = np.sin(2 * np.pi * np.cumsum(140 + 300 * np.exp(-t_(n) / 0.03)) / SR) * env_exp(n, 0.08)
    return (x * 0.7 + plop * 0.6) * gain


def kaching(gain=0.6):
    n = int(1.0 * SR)
    t = t_(n)
    ka = filt(noise(n), 'bandpass', [2000, 7000]) * env_exp(n, 0.01)
    bell = np.zeros(n)
    i = int(0.08 * SR)
    for f, a in ((2093, 1), (2637, .8), (3136, .6), (4186, .4)):
        bell[i:] += a * np.sin(2 * np.pi * f * t[:n - i]) * env_exp(n - i, 0.35)
    return (ka * 0.8 + bell * 0.35) * gain


def bloop(gain=0.35):
    n = int(0.12 * SR)
    f = 500 + 900 * (t_(n) / 0.12)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, 0.04) * gain


def vibrate(gain=0.35, dur=0.4):
    n = int(dur * SR)
    t = t_(n)
    x = np.sign(np.sin(2 * np.pi * 150 * t)) * (np.sin(2 * np.pi * 18 * t) > 0)
    return filt(x, 'lowpass', 900) * gain


def whoosh(gain=0.35, dur=0.35, up=True):
    n = int(dur * SR)
    x = sweep_filter(noise(n), 'bandpass' if False else 'lowpass', 600 if up else 6000, 6000 if up else 600, 12)
    e = np.sin(np.pi * t_(n) / dur) ** 2
    return x * e * gain


def tick(gain=0.25):
    n = int(0.03 * SR)
    return filt(noise(n), 'highpass', 3000) * env_exp(n, 0.004) * gain


def creak(gain=0.5, dur=1.2):
    n = int(dur * SR)
    t = t_(n)
    f = 90 + 40 * np.sin(2 * np.pi * 1.3 * t)
    pulses = (np.sin(2 * np.pi * np.cumsum(f) / SR) > 0.7).astype(float)
    return filt(pulses, 'bandpass', [400, 2500]) * np.minimum(1, t / 0.1) * env_exp(n, dur) * gain


def riser(dur=1.5, gain=0.35):
    n = int(dur * SR)
    t = t_(n)
    x = sweep_filter(noise(n), 'highpass', 300, 8000) * (t / dur) ** 2
    f = 200 * (6 ** (t / dur))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * (t / dur) ** 2 * 0.3
    return (x + tone) * gain


def flash(gain=0.4):
    n = int(0.5 * SR)
    return filt(noise(n), 'highpass', 4000) * env_exp(n, 0.12) * gain


# ---------------- arrangement ----------------
class Mix:
    def __init__(self, seconds):
        self.n = int(seconds * SR)
        self.music = np.zeros((2, self.n))
        self.fx = np.zeros((2, self.n))
        self.duck = np.ones(self.n)

    def add(self, bus, x, at, pan=0.0, gain=1.0):
        i = int(at * SR)
        if i >= self.n:
            return
        x = np.atleast_2d(x)
        if x.shape[0] == 1:
            x = np.stack([x[0] * (1 - max(0, pan)), x[0] * (1 + min(0, pan))])
        j = min(self.n, i + x.shape[1])
        getattr(self, bus)[:, i:j] += x[:, :j - i] * gain

    def sidechain(self, at, depth=0.6, rel=0.18):
        i = int(at * SR)
        n = int(0.4 * SR)
        j = min(self.n, i + n)
        self.duck[i:j] = np.minimum(self.duck[i:j], 1 - depth * np.exp(-t_(j - i) / rel))


def beat(mix, start, end, mood='hype', bar0=0):
    """Full beat from start to end, bar by bar."""
    t = start
    b = bar0
    while t < end - 0.05:
        ch = CHORDS[b % 4]
        root = ROOTS[b % 4]
        bar_end = min(end, t + BAR)
        # pad chord (bright after the drop, darker for 'dark')
        mix.add('music', supersaw_chord(ch, bar_end - t, 2600 if mood == 'hype' else 1200, 0.07), t)
        kicks = [0, 6, 10] if b % 2 == 0 else [0, 3, 10, 14]
        for s in range(16):
            at = t + s * STEP
            if at >= end:
                break
            if s in kicks:
                mix.add('music', kick(0.9), at)
                mix.sidechain(at, 0.55)
                nxt = [k for k in kicks if k > s]
                dur = ((nxt[0] if nxt else 16) - s) * STEP
                mix.add('music', bass808(mtof(root), dur, 0.55, glide_from=mtof(root + 12) if s == 0 and b % 4 == 2 else None), at)
            if s == 8:
                mix.add('music', clap(0.55), at, pan=0.0)
            if s % 2 == 0:
                mix.add('music', hat(0.14), at, pan=0.25)
            if b % 2 == 1 and s >= 12:  # hi-hat roll into the next bar
                for r in range(2):
                    mix.add('music', hat(0.10), at + r * STEP / 2, pan=0.25)
            if mood == 'hype' and s % 2 == 1:  # pluck arpeggio, the "Leo" sparkle
                m = ch[(s // 2) % 4] + 12
                mix.add('music', pluck(m, 0.08), at, pan=-0.3 if s % 4 == 1 else 0.3)
        t += BAR
        b += 1


def intro(mix, start, end, mood):
    if end - start < 0.2:
        return
    cutoff = 700 if mood == 'hype' else 450
    t = start
    b = 0
    while t < end - 0.05:
        d = min(BAR, end - t)
        mix.add('music', supersaw_chord(CHORDS[b % 4], d, cutoff, 0.06), t)
        if mood != 'hype':  # heartbeat in the dark intros
            for k in (0, 0.28):
                if t + k < end:
                    mix.add('music', kick(0.45), t + k)
        else:
            for s in range(0, 16, 4):
                if t + s * STEP < end:
                    mix.add('music', hat(0.07), t + s * STEP, pan=0.2)
        t += BAR
        b += 1
    r = min(1.6, end - start)
    mix.add('music', riser(r, 0.3), end - r)


def outro(mix, at, total):
    mix.add('fx', impact(0.9), at)
    mix.sidechain(at, 0.8, 0.3)
    d = total - at
    pad = supersaw_chord(CHORDS[0], d, 1800, 0.08)
    pad *= np.linspace(1, 0, pad.shape[1]) ** 1.5
    mix.add('music', pad, at)
    mix.add('music', bass808(mtof(ROOTS[0]), min(d, 1.5), 0.5), at)


def fx_for(e, at, mix):
    k, text = e.get('k'), str(e.get('text', '')).upper()
    anims = [a for a in e.get('a', []) if isinstance(a, list)]
    for a in anims:
        name = a[0] if isinstance(a[0], str) else 'custom'
        if name == 'count':
            frm, to, delay, dur = a[1], a[2], a[3], a[4]
            n = 14
            for i in range(n):
                p = 1 - (1 - i / n) ** (1 / 3)
                mix.add('fx', tick(0.22), at + (delay + dur * p) / 1000, pan=0.1)
            continue
        delay = (a[1] if len(a) > 1 else 0) / 1000
        when = at + delay
        if name in ('slam', 'pop') and k == 'burst':
            if 'KLONK' in text or 'KNA' in text:
                mix.add('fx', klonk(0.8) if 'KLONK' in text else creak(0.5), when)
            elif 'PLATSCH' in text:
                mix.add('fx', splash(0.9), when)
            elif 'CHING' in text:
                mix.add('fx', kaching(0.6), when)
            else:
                mix.add('fx', impact(0.75 if name == 'slam' else 0.45), when)
            mix.sidechain(when, 0.7, 0.25)
        elif name == 'slam' and k in ('big', 'brand', 'scene'):
            mix.add('fx', impact(0.55), when)
            mix.sidechain(when, 0.6)
        elif name == 'pop' and k == 'msg':
            mix.add('fx', bloop(0.35), when)
        elif name == 'pop' and k in ('head', 'box', 'balloon'):
            mix.add('fx', bloop(0.22), when, pan=-0.2)
        elif name == 'shake' and k == 'msg':
            mix.add('fx', vibrate(0.35), when)
        elif name in ('up', 'left', 'right', 'down'):
            mix.add('fx', whoosh(0.28, 0.35), when, pan=0.3 if name == 'left' else -0.3 if name == 'right' else 0)
        elif name == 'flash':
            mix.add('fx', flash(0.4), when)
        elif name == 'custom':  # the fall in the badi reel: a falling whistle
            dur = a[2] / 1000
            n = int(dur * SR)
            f = 1800 * (0.25 ** (t_(n) / dur))
            mix.add('fx', np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.12 * np.minimum(1, t_(n) / 0.1), when)
            mix.add('fx', whoosh(0.3, dur, up=False), when)


def render(post):
    shots = post['shots']
    total = sum(s['dur'] for s in shots) / 1000
    mix = Mix(total)
    snd = post.get('sound', {})
    drop = snd.get('drop', 2.0)
    mood = snd.get('mood', 'hype')
    starts = np.cumsum([0] + [s['dur'] for s in shots]) / 1000
    out_at = snd.get('outro', starts[-2])
    intro(mix, 0, drop, mood)
    mix.add('fx', impact(0.9), drop)
    mix.sidechain(drop, 0.8, 0.3)
    beat(mix, drop, out_at, snd.get('beatMood', 'hype'))
    outro(mix, out_at, total)
    for s, at in zip(shots, starts):
        if s['dur'] <= 1000:
            mix.add('fx', whoosh(0.22, 0.25), max(0, at - 0.12))
        for e in s.get('els', []):
            fx_for(e, at, mix)
    music = mix.music * mix.duck
    out = music * 0.8 + mix.fx * 0.9
    fade = int(0.25 * SR)
    out[:, -fade:] *= np.linspace(1, 0, fade)
    out = np.tanh(out * 1.1) * 0.9
    return out, total


def write_wav(path, x):
    import wave
    x = np.clip(x, -1, 1)
    data = (x.T * 32767).astype('<i2').tobytes()
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data)


def main():
    data = json.load(open(os.path.join(ROOT, 'posts.json'), encoding='utf-8'))
    only = sys.argv[1:]
    for post in data['posts']:
        if post.get('format') != 'reel' or (only and post['id'] not in only):
            continue
        d = os.path.join(ROOT, 'posts', post['id'])
        wav = os.path.join(d, 'sound.wav')
        x, total = render(post)
        write_wav(wav, x)
        video = os.path.join(d, 'reel.mp4')
        tmp = os.path.join(d, 'reel.tmp.mp4')
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', video, '-i', wav, '-map', '0:v', '-map', '1:a',
                        '-c:v', 'copy', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=9', '-c:a', 'aac', '-b:a', '192k', '-ar', '44100',
                        '-shortest', '-movflags', '+faststart', tmp], check=True)
        os.replace(tmp, video)
        print('sound', post['id'], round(total, 1), 's')


if __name__ == '__main__':
    main()
