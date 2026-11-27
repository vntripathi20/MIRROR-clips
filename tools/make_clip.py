"""Build a MIRROR daily clip (1080x1920, 24s) from the /daily.json brief.

usage: python3 make_clip.py brief.json OUTDIR   -> OUTDIR/MIRROR_<date>.mp4
Needs: ffmpeg, Pillow, numpy, and the Silkscreen + Poppins TTF fonts (paths below).
"""
import os, sys, json, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
BG, CREAM, LIME = (17, 17, 17), (240, 236, 225), (212, 255, 58)
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
    im, d = base(); logo(d, 170)
    off = int((1 - ease(t / 0.5)) * 60)
    tc(d, 640 + off, "WHAT DID", F(120), CREAM)
    if t > 0.6: tc(d, 790, "MOST PEOPLE", F(120), CREAM)
    if t > 1.2: tc(d, 940, "PICK?", F(190), LIME)
    if t > 2.0: tc(d, 1250, f"Today's {Q['difficulty']} question", F(54, "popm"), CREAM)
    return im

def s_question(t):
    im, d = base(); logo(d, 170)
    tc(d, 330, "QUESTION", F(40, "pix"), DIM, sp=8)
    y = 410
    for ln in wrap(d, Q["question"], F(58), W - 180):
        tc(d, y, ln, F(58), CREAM); y += 78
    tc(d, y + 20, "Pick what MOST people choose.", F(38, "popm"), LIME)
    for i in range(4):
        a = ease((t - 0.3 - i * 0.25) / 0.35)
        if a > 0: card(d, i, 790 + i * 200 + int((1 - a) * 40))
    return im

def s_count(t):
    im, d = base(); logo(d, 170)
    tc(d, 330, "LOCK IT IN", F(44, "pix"), DIM, sp=8)
    for i in range(4): card(d, i, 560 + i * 200)
    n = 5 - int(t); fr = t - int(t)
    tc(d, 1380, str(max(n, 1)), F(int(260 + 60 * (1 - ease(fr * 3))), "pix"), LIME)
    return im

def s_reveal(t):
    im, d = base(); logo(d, 170)
    tc(d, 330, "THE CROWD SAID", F(44, "pix"), DIM, sp=8)
    r, done = ease(t / 2.2), t > 2.4
    for i in range(4):
        hl = done and i in WIN
        card(d, i, 560 + i * 200, reveal=r, hl=hl, dim=(done and not hl))
    if done:
        if len(WIN) > 1:
            tc(d, 1380, "TIE", F(170, "pix"), LIME)
            if t > 3.6: tc(d, 1570, f"Two answers. {PCT[WIN[0]]}% each.", F(52, "popm"), CREAM)
        else:
            pct_draw(d, 0, 1380, PCT[WIN[0]], 170, LIME, center=True)
            if t > 3.6:
                wt = CH[WIN[0]]["text"]
                tc(d, 1580, wt, fit(d, wt, "popm", 52, W - 200), CREAM)
    return im

def s_cta(t):
    im, d = base(); logo(d, 360)
    tc(d, 640, "COULD YOU", F(110), CREAM); tc(d, 770, "READ THE", F(110), CREAM); tc(d, 900, "ROOM?", F(150), LIME)
    tc(d, 1180, "New questions every day", F(52, "popm"), CREAM)
    d.rectangle([140, 1300, W - 140, 1470], fill=LIME)
    tc(d, 1340, "mirror.vednt.com", F(78), BG)
    tc(d, 1530, "Beat my score. Link in bio.", F(46, "popm"), CREAM)
    return im

SCENES = [("hook", s_hook, 3.0), ("question", s_question, 5.0), ("count", s_count, 5.0),
          ("reveal", s_reveal, 6.0), ("cta", s_cta, 5.0)]

def render(name, fn, dur):
    final, tmp = f"{OUT}/{name}.mp4", f"{OUT}/{name}.tmp.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
        "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    for k in range(int(round(dur * FPS))): p.stdin.write(fn(k / FPS).tobytes())
    p.stdin.close()
    if p.wait() != 0: raise SystemExit("ffmpeg failed: " + name)
    os.replace(tmp, final)

def sfx(path):
    SR = 44100; a = np.zeros(SR * 24)
    def blip(t0, f, dur=0.12, vol=0.35, decay=18):
        n = int(SR * dur); t = np.arange(n) / SR
        w = np.sign(np.sin(2 * np.pi * f * t)) * np.exp(-decay * t) * vol
        i = int(SR * t0); a[i:i + n] += w[:len(a) - i]
    blip(0, 330, .2); blip(3, 520, .1)
    for k in range(5): blip(8 + k, 880 if k < 4 else 1320, .15)
    for k, f in enumerate([440, 554, 659, 880]): blip(13 + k * .5, f, .15)
    blip(15.5, 1047, .3, .4, 8); blip(15.5, 1319, .3, .3, 8)
    blip(19, 660, .15); blip(19.25, 880, .3)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())

if __name__ == "__main__":
    for name, fn, dur in SCENES: render(name, fn, dur)
    lst = f"{OUT}/list.txt"
    open(lst, "w").write("".join(f"file '{OUT}/{n}.mp4'\n" for n, _, _ in SCENES))
    sfx(f"{OUT}/sfx.wav")
    silent, final = f"{OUT}/silent.tmp.mp4", f"{OUT}/MIRROR_{brief['date']}.mp4"
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent])
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", f"{OUT}/sfx.wav", "-map", "0:v",
        "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", final + ".tmp.mp4"])
    os.replace(final + ".tmp.mp4", final)
    print("picked Q%d (%s) -> %s" % (Q["number"], Q["difficulty"], final))
