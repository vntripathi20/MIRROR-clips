"""Build a MIRROR daily clip (1080x1920, ~20s) from the /daily.json brief.

usage: python3 make_clip.py brief.json OUTDIR   -> OUTDIR/MIRROR_<date>.mp4
Needs: ffmpeg, Pillow, numpy, and the Silkscreen + Poppins TTF fonts (paths below).
"""
import os, sys, json, subprocess, wave, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
BG, CREAM, LIME = (17, 17, 17), (240, 236, 225), (212, 255, 58)
PINK = (255, 92, 172)
DIM, CARD = (120, 118, 110), (30, 30, 28)
PIX = os.path.join(HERE, "Silkscreen-700.ttf")
POP = os.environ.get("POPPINS", "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf")
if not os.path.exists(POP):
    POP = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
POPM = POP.replace("Bold", "Medium") if "Poppins" in POP else POP
RANK = {"INSANE": 4, "HOT": 3, "WARM": 2, "OBVIOUS": 1}

brief = json.load(open(sys.argv[1]))
OUT = os.path.abspath(sys.argv[2])
os.makedirs(OUT, exist_ok=True)

def pick(b):
    qs = [q for q in b["questions"] if q.get("difficulty") and not q.get("forming") and q["totalVotes"] > 0]
    def key(q):
        p = sorted([c["percent"] for c in q["choices"]], reverse=True)
        return (RANK.get(q["difficulty"], 0), -(p[0] - p[1]), -q["number"] if not q["isFinal"] else 0)
    return max(qs, key=key)

Q = pick(brief)
CH = Q["choices"]
PCT = [c["percent"] for c in CH]
WIN = [i for i, c in enumerate(CH) if c["won"]]
SCALE = max(40, int(-(-max(PCT) // 10) * 10))

def F(sz, kind="pop"):
    return ImageFont.truetype({"pop": POP, "popm": POPM, "pix": PIX}[kind], sz)

def ease(x):
    x = max(0, min(1, x)); return 1 - (1 - x) ** 3

def tc(d, y, s, f, fill, sp=0, cx=W // 2):
    if sp:
        ws = [d.textlength(c, font=f) for c in s]
        x = cx - (sum(ws) + sp * (len(s) - 1)) / 2
        for c, w in zip(s, ws):
            d.text((x, y), c, font=f, fill=fill); x += w + sp
    else:
        d.text((cx - d.textlength(s, font=f) / 2, y), s, font=f, fill=fill)

def wrap(d, s, f, maxw):
    out, cur = [], ""
    for w in s.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw: cur = t
        else: out.append(cur); cur = w
    return out + [cur]

def fit(d, s, kind, size, maxw):
    while size > 24 and d.textlength(s, font=F(size, kind)) > maxw: size -= 2
    return F(size, kind)

def base():
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    for gx in range(60, W, 120):
        for gy in range(60, H, 120): d.rectangle([gx, gy, gx + 4, gy + 4], fill=(26, 26, 24))
    return im, d

def logo(d, y): tc(d, y, "MIRROR", F(92, "pix"), CREAM, sp=10)

def pct_draw(d, x_right, y, p, size, fill, center=False):
    nf, pf = F(size, "pix"), F(int(size * 0.8), "pop")
    dig = str(p); wd, wp = d.textlength(dig, font=nf), d.textlength("%", font=pf)
    x = (W // 2 - (wd + wp + 8) / 2) if center else (x_right - (wd + wp + 8))
    d.text((x, y), dig, font=nf, fill=fill)
    d.text((x + wd + 8, y + size * 0.1), "%", font=pf, fill=fill)

def card(d, i, y, reveal=0.0, hl=False, dim=False):
    x0, x1, h = 80, W - 80, 170
    d.rectangle([x0, y, x1, y + h], fill=CARD, outline=LIME if hl else (60, 60, 56), width=4 if hl else 3)
    col = DIM if dim else CREAM
    if reveal > 0:
        fw = int(((x1 - x0 - 16) * PCT[i] / SCALE * reveal) // 24) * 24
        if fw > 0: d.rectangle([x0 + 8, y + h - 34, x0 + 8 + fw - 4, y + h - 12], fill=LIME if hl else (90, 88, 80))
    d.text((x0 + 34, y + 30), "ABCD"[i], font=F(62, "pix"), fill=LIME if hl else col)
    txt = CH[i]["text"]
    d.text((x0 + 125, y + 40), txt, font=fit(d, txt, "popm", 44, x1 - x0 - 125 - 200), fill=col)
    if reveal > 0:
        pct_draw(d, x1 - 30, y + 34, int(round(PCT[i] * reveal)), 58, LIME if hl else col)

def s_hook(t):
    im, d = base(); logo(d, 190)
    off = int((1 - ease(t / 0.25)) * 50)
    tc(d, 600 + off, f"{Q['totalVotes']} PEOPLE", F(130), CREAM)
    tc(d, 750 + off, "ANSWERED THIS.", fit(d, "ANSWERED THIS.", "pop", 112, W - 200), CREAM)
    tc(d, 960, "CAN YOU GUESS", F(74, "popm"), CREAM)
    tc(d, 1050, "WHAT MOST PICKED?", F(92), LIME)
    tc(d, 1250, f"{Q['difficulty']} QUESTION", F(46, "pix"), PINK, sp=6)
    return im

def s_question(t):
    im, d = base(); logo(d, 190)
    tc(d, 340, "QUESTION", F(40, "pix"), DIM, sp=8)
    y = 420
    for ln in wrap(d, Q["question"], F(58), W - 180):
        tc(d, y, ln, F(58), CREAM); y += 78
    tc(d, y + 20, "Pick what MOST people choose.", F(38, "popm"), LIME)
    for i in range(4):
        a = ease((t - 0.2 - i * 0.15) / 0.3)
        if a > 0: card(d, i, 800 + i * 200 + int((1 - a) * 40))
    return im

def s_count(t):
    im, d = base(); logo(d, 190)
    tc(d, 340, "COMMENT YOUR GUESS", F(44, "pix"), LIME, sp=6)
    for i in range(4): card(d, i, 560 + i * 200)
    n = 4 - int(t); fr = t - int(t)
    tc(d, 1390, str(max(n, 1)), F(int(250 + 70 * (1 - ease(fr * 3))), "pix"), LIME if n > 1 else PINK)
    return im

def confetti(d, tt):
    rnd = random.Random(7)
    for i in range(80):
        x0, vy, sz = rnd.random() * W, 260 + rnd.random() * 520, rnd.choice([12, 16, 20])
        col = rnd.choice([LIME, CREAM, PINK, LIME])
        x = x0 + math.sin(tt * 4 + i) * 28; y = 520 + vy * tt * 0.9
        if 540 < y < H - 330: d.rectangle([x, y, x + sz, y + sz], fill=col)

def s_reveal(t):
    im, d = base(); logo(d, 190)
    tc(d, 340, "THE CROWD SAID", F(44, "pix"), DIM, sp=8)
    r, done = ease(t / 2.0), t > 2.2
    if done: confetti(d, t - 2.2)          # behind the cards so it never hides text
    for i in range(4):
        hl = done and i in WIN
        card(d, i, 560 + i * 200, reveal=r, hl=hl, dim=(done and not hl))
    if done:
        if len(WIN) > 1:
            tc(d, 1380, "TIE", F(170, "pix"), LIME)
            if t > 3.2: tc(d, 1570, f"Two answers. {PCT[WIN[0]]}% each.", F(52, "popm"), CREAM)
        else:
            pct_draw(d, 0, 1380, PCT[WIN[0]], 170, LIME, center=True)
            if t > 3.2:
                wt = CH[WIN[0]]["text"]
                tc(d, 1580, wt, fit(d, wt, "popm", 52, W - 200), CREAM)
        if t < 2.55:  # screen shake on the reveal
            k = 1 - (t - 2.2) / 0.35; dx = int(16 * math.sin(t * 90) * k); dy = int(12 * math.cos(t * 70) * k)
            im = ImageChops.offset(im, dx, dy)
    return im

def s_cta(t):
    im, d = base(); logo(d, 300)
    pop = 1 + 0.06 * math.sin(t * 8)
    tc(d, 560, "DROP A W", F(int(150 * pop)), LIME)
    tc(d, 740, "IF YOU GOT IT", F(96), CREAM)
    tc(d, 960, "New questions every day", F(52, "popm"), CREAM)
    d.rectangle([140, 1090, W - 140, 1260], fill=LIME)
    tc(d, 1130, "mirror.vednt.com", F(78), BG)
    tc(d, 1330, "Follow for tomorrow's", F(46, "popm"), PINK)
    return im

SCENES = [("hook", s_hook, 2.5), ("question", s_question, 7.0), ("count", s_count, 4.0),
          ("reveal", s_reveal, 5.5), ("cta", s_cta, 3.5)]
STARTS = {}
_t = 0.0
for _n, _f, _d in SCENES:
    STARTS[_n] = _t; _t += _d
TOTAL = _t

def with_progress(fn, t0):
    def g(t):
        im = fn(t); d = ImageDraw.Draw(im)
        d.rectangle([80, 150, W - 80, 158], fill=(46, 46, 42))
        d.rectangle([80, 150, 80 + (W - 160) * min(1, (t0 + t) / TOTAL), 158], fill=LIME)
        return im
    return g

def render(name, fn, dur):
    fn = with_progress(fn, STARTS[name])
    final, tmp = f"{OUT}/{name}.mp4", f"{OUT}/{name}.tmp.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
        "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    for k in range(int(round(dur * FPS))): p.stdin.write(fn(k / FPS).tobytes())
    p.stdin.close()
    if p.wait() != 0: raise SystemExit("ffmpeg failed: " + name)
    os.replace(tmp, final)

SR = 44100

def _note(f, n, kind="sq", duty=0.5):
    t = np.arange(n) / SR
    ph = (t * f) % 1.0
    return np.where(ph < duty, 1.0, -1.0) if kind == "sq" else np.sin(2 * np.pi * f * t)

def music(total):
    """Original royalty-free chill chiptune loop (A minor: Am-F-C-G), 88 BPM, soft and slow."""
    n_tot = int(SR * total); m = np.zeros(n_tot)
    beat = 60.0 / 88
    mf = lambda midi: 440.0 * 2 ** ((midi - 69) / 12)
    chords = [(45, [57, 60, 64]), (41, [57, 60, 65]), (48, [60, 64, 67]), (43, [59, 62, 67])]
    def add(t0, arr, vol):
        i = int(t0 * SR)
        if i >= n_tot: return
        j = min(n_tot, i + len(arr)); m[i:j] += arr[:j - i] * vol
    def sec(t0):
        for nme in ("cta", "reveal", "count", "question", "hook"):
            if t0 >= STARTS[nme]: return nme
    k = 0
    while k * beat / 2 < total:                      # 8th-note grid
        t0 = k * beat / 2
        root, tones = chords[int(t0 / (beat * 4)) % 4]
        s_ = sec(t0)
        nl = int(beat * 0.45 * SR); env = np.exp(-np.arange(nl) / SR * 9)
        av = {"hook": 0.05, "question": 0.06, "count": 0.07, "reveal": 0.08, "cta": 0.07}[s_]
        tone = tones[k % 3] + (12 if s_ in ("reveal", "cta") and (k // 3) % 2 else 0)
        add(t0, _note(mf(tone), nl, "sq", 0.25) * env, av)           # soft arp
        if k % 2 == 0 and s_ != "hook":                              # soft low-mid pad note, one octave up (no sub bass)
            bl = int(beat * 0.9 * SR)
            add(t0, _note(mf(root + 12), bl, "sin") * np.exp(-np.arange(bl) / SR * 3), 0.07)
        if s_ in ("reveal", "cta") and k % 4 == 2:                   # soft hat on beats 2 and 4
            hl = int(0.045 * SR)
            add(t0, (np.random.RandomState(k).rand(hl) * 2 - 1) * np.exp(-np.arange(hl) / SR * 80), 0.05)
        k += 1
    m *= np.minimum(1.0, np.maximum(0.0, (total - np.arange(n_tot) / SR) / 1.5))
    m *= np.minimum(1.0, np.arange(n_tot) / SR / 0.3)
    return m / max(1e-6, np.abs(m).max()) * 0.35

def sfx(path):
    a = np.zeros(int(SR * TOTAL))
    def blip(t0, f, dur=0.12, vol=0.30, decay=18):
        n = int(SR * dur); t = np.arange(n) / SR
        w = np.sign(np.sin(2 * np.pi * f * t)) * np.exp(-decay * t) * vol
        i = int(SR * t0); a[i:i + n] += w[:len(a) - i]
    blip(0, 330, .2); blip(STARTS["question"], 520, .1)
    for k in range(4): blip(STARTS["count"] + k, 784 if k < 3 else 1175, .14)
    r = STARTS["reveal"]
    for k, f in enumerate([440, 554, 659, 880]): blip(r + k * .5, f, .14)
    blip(r + 2.2, 1047, .3, .36, 8); blip(r + 2.2, 1319, .3, .26, 8)
    blip(STARTS["cta"], 660, .14); blip(STARTS["cta"] + .25, 880, .28)
    mix = music(TOTAL) + a * 0.7
    mix = mix / max(1.0, np.abs(mix).max() / 0.92)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())

if __name__ == "__main__":
    for name, fn, dur in SCENES: render(name, fn, dur)
    lst = f"{OUT}/list.txt"
    open(lst, "w").write("".join(f"file '{OUT}/{n}.mp4'\n" for n, _, _ in SCENES))
    sfx(f"{OUT}/sfx.wav")
    silent, final = f"{OUT}/silent.tmp.mp4", f"{OUT}/MIRROR_{brief['date']}.mp4"
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent])
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", f"{OUT}/sfx.wav", "-map", "0:v",
        "-map", "1:a", "-af", "highpass=f=260,highpass=f=260,lowpass=f=6000,loudnorm=I=-14.5:TP=-1.5:LRA=9", "-ar", "44100", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", final + ".tmp.mp4"])
    os.replace(final + ".tmp.mp4", final)
    print("picked Q%d (%s) -> %s" % (Q["number"], Q["difficulty"], final))
