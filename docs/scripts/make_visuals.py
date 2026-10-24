"""README 그림 · 움짤 · 소리 영상을 만든다(make_audio.py 결과로).

사용(저장소 루트에서):
    python -I -B docs/scripts/make_visuals.py <작업 폴더(make_audio 결과)> docs <ko|en> [hero,distance,denoise,mp4,gifs]
언어별 그림(hero.png · distance.png · denoise.png)과 소리 영상(listen-*.mp4)은 docs/<언어>/ 에, 글자 없는 움짤
(spaces.gif · room-wave.gif)은 두 언어가 같이 쓰도록 docs/ 에 쓴다. 움짤은 언어와 상관없으니 한 번만 만들면 된다.
"""
import importlib.util
import os
import subprocess
import sys

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from scipy.signal import stft  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
audio_dir, docs, lang = sys.argv[1:4]
out = os.path.join(docs, lang)
os.makedirs(out, exist_ok=True)
spec = importlib.util.spec_from_file_location("ra_main", os.path.join(ROOT, "nodes", "main.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

for w in ("Regular", "SemiBold", "Bold"):
    font_manager.fontManager.addfont(os.path.join(C.FONT_DIR, f"Pretendard-{w}.otf"))
HEX = C.hex_color
plt.rcParams.update({
    "font.family": "Pretendard", "font.size": 13, "axes.unicode_minus": False,
    "figure.facecolor": HEX(C.BG), "axes.facecolor": HEX(C.BG), "savefig.facecolor": HEX(C.BG),
    "text.color": "white", "axes.labelcolor": HEX(C.MUTED), "xtick.color": HEX(C.MUTED), "ytick.color": HEX(C.MUTED),
    "axes.edgecolor": HEX(C.LINE),
})

T = {
    "ko": {
        "original": "원래 소리", "reverb": "공간 울림", "denoise": "잡음 줄이기", "noisy": "잡음 섞인 소리",
        "spaces": {"bathroom": "욕실", "small-room": "작은 방", "living-room": "거실", "hall": "강당",
                   "cathedral": "성당", "tunnel": "터널"},
        "dist": {"near": "가까이", "mid": "보통", "far": "멀리"},
        "strength": {"light": "약하게", "normal": "보통", "strong": "강하게"},
        "sec": "초", "khz": "kHz", "tail": "울림 꼬리 {v:.1f}초",
        "hero_after": "공간 울림 · 성당 · 거리 보통",
        "dist_title": "강당에서 거리만 바꾸면 · 손뼉 한 번의 방 울림",
        "direct": "바로 온 소리", "reflect": "벽에서 돌아온 울림", "ratio": "바로 온 소리 비중 {v}%",
        "dist_panel": "{name} · {m}m",
        "denoise_title": "'쉬—' 잡음을 섞은 말소리 → 잡음 줄이기 세기별",
        "seg": "{i} / {n}",
    },
    "en": {
        "original": "Original", "reverb": "Room reverb", "denoise": "Noise reduction", "noisy": "Noisy speech",
        "spaces": {"bathroom": "Bathroom", "small-room": "Small room", "living-room": "Living room", "hall": "Hall",
                   "cathedral": "Cathedral", "tunnel": "Tunnel"},
        "dist": {"near": "Near", "mid": "Medium", "far": "Far"},
        "strength": {"light": "Light", "normal": "Normal", "strong": "Strong"},
        "sec": "s", "khz": "kHz", "tail": "reverb tail {v:.1f} s",
        "hero_after": "Room reverb · Cathedral · Medium distance",
        "dist_title": "Same hall, different distance · room response to one clap",
        "direct": "direct sound", "reflect": "reflections from the walls", "ratio": "direct sound {v}% of energy",
        "dist_panel": "{name} · {m} m",
        "denoise_title": "Speech with added hiss → noise reduction by strength",
        "seg": "{i} / {n}",
    },
}[lang]

SPACE_IDS = list(mod.SPACES)
PURPLE = HEX(C.PURPLE_TEXT)
WHITE = "#e8e8e8"


def load(name):
    x, fs = sf.read(os.path.join(audio_dir, name + ".wav"), dtype="float64", always_2d=True)
    return x.mean(axis=1), fs


def spec_db(x, fs):
    f, t, Z = stft(x, fs=fs, nperseg=512, noverlap=448)
    return f, t, 20 * np.log10(np.abs(Z) + 1e-9)


def draw_wave(ax, x, fs, tmax, color, ylim=1.0):
    n = 1600
    edges = np.linspace(0, len(x), n + 1).astype(int)
    lo = np.array([x[a:b].min() if b > a else 0 for a, b in zip(edges[:-1], edges[1:])])
    hi = np.array([x[a:b].max() if b > a else 0 for a, b in zip(edges[:-1], edges[1:])])
    ax.fill_between(edges[:-1] / fs, lo, hi, color=color, linewidth=0)
    ax.set_xlim(0, tmax)
    ax.set_ylim(-ylim, ylim)
    ax.axis("off")


def draw_spec(ax, x, fs, tmax, ref, xlabel=True):
    f, t, D = spec_db(x, fs)
    ax.imshow(D, origin="lower", aspect="auto", extent=[t[0], t[-1], 0, f[-1] / 1000], cmap="magma",
              vmin=ref - 75, vmax=ref, interpolation="bilinear")
    ax.set_xlim(0, tmax)
    ax.set_ylim(0, 12)
    ax.set_yticks([0, 4, 8, 12])
    ax.set_ylabel(T["khz"])
    for s in ax.spines.values():
        s.set_visible(False)
    if xlabel:
        ax.set_xlabel(T["sec"], loc="right")
    else:
        ax.set_xticklabels([])


def save_png(fig, path):
    fig.savefig(path, dpi=100)
    plt.close(fig)
    im = Image.open(path).convert("RGB")
    im.quantize(colors=256, method=Image.MEDIANCUT, dither=Image.NONE).save(path, optimize=True)
    return os.path.getsize(path)


def env_db(ir, fs, tmax, width, win=0.02, ref=None):
    """방 울림의 크기(dB, win 초 평균 에너지)를 가로 픽셀마다. ref 가 없으면 자기 최댓값이 0dB."""
    e = np.convolve(ir**2, np.ones(max(1, int(win * fs))) / max(1, int(win * fs)), mode="full")[: len(ir)]
    ref = e.max() if ref is None else ref
    db = 10 * np.log10(e / ref + 1e-12)
    cols = np.full(width, -120.0)
    for px in range(width):
        a = int(px / width * tmax * fs)
        b = int((px + 1) / width * tmax * fs)
        if a < len(db):
            cols[px] = db[a:max(a + 1, min(b, len(db)))].max()
    return cols


# ── 대표 그림: 원래 소리 vs 성당 ─────────────────────────────────────────────
def hero():
    a, fs = load("original")
    b, _ = load("reverb-cathedral")
    tmax = len(b) / fs
    ref = spec_db(a, fs)[2].max()
    peak = max(np.abs(a).max(), np.abs(b).max())
    fig = plt.figure(figsize=(16, 8.2))
    for x, title, color, y0 in [(a, T["original"], WHITE, 0.53), (b, T["hero_after"], PURPLE, 0.06)]:
        fig.text(0.055, y0 + 0.405, title, fontsize=20, fontweight="semibold", color=color)
        draw_wave(fig.add_axes([0.055, y0 + 0.29, 0.92, 0.1]), x, fs, tmax, color, peak)
        draw_spec(fig.add_axes([0.055, y0 + 0.03, 0.92, 0.25]), x, fs, tmax, ref, xlabel=(y0 < 0.3))
    t0 = len(a) / fs
    ax = fig.add_axes([0.055, 0.09, 0.92, 0.37], facecolor="none")
    ax.set_xlim(0, tmax)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.axvspan(t0, tmax, color=HEX(C.PURPLE), alpha=0.16, linewidth=0)
    ax.axvline(t0, color=PURPLE, linewidth=1.5, linestyle=(0, (4, 3)))
    ax.text(t0 + 0.08, 0.6, T["tail"].format(v=tmax - t0), color=PURPLE, fontsize=17, fontweight="semibold", va="top")
    return save_png(fig, os.path.join(out, "hero.png"))


# ── 거리 비교 ────────────────────────────────────────────────────────────────
def distance_png():
    data = np.load(os.path.join(audio_dir, "irs.npz"))
    fs = int(data["fs"])
    dists = mod.SPACES["hall"][2]
    fig = plt.figure(figsize=(16, 5.4))
    fig.text(0.04, 0.9, T["dist_title"], fontsize=20, fontweight="semibold", color="white")
    tmax, width, floor, win = 1.0, 500, 50, 0.003
    normed = [ir / np.sqrt(np.sum(ir**2)) for ir in (data[f"hall|{d}"][0] for d in mod.DISTANCES)]
    k_ = max(1, int(win * fs))
    ref = max(np.convolve(n**2, np.ones(k_) / k_, mode="full").max() for n in normed)
    direct_px = int(width * 0.006 / tmax) + 1
    for k, (d, ir) in enumerate(zip(mod.DISTANCES, normed)):
        ax = fig.add_axes([0.04 + k * 0.322, 0.16, 0.29, 0.6])
        e = np.clip((env_db(ir, fs, tmax, width, win=win, ref=ref) + floor) / floor, 0, None)
        tt = np.arange(width) / width * tmax
        ax.fill_between(tt[direct_px:], -e[direct_px:], e[direct_px:], color=PURPLE, linewidth=0, step="mid")
        ax.fill_between(tt[: direct_px + 1], -e[: direct_px + 1], e[: direct_px + 1], color=WHITE, linewidth=0, step="mid")
        ratio = 100 * np.sum(ir[: int(0.005 * fs)] ** 2) / np.sum(ir**2)
        ax.set_xlim(-0.01, tmax)
        ax.set_ylim(-1.05, 1.05)
        ax.set_yticks([])
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.set_xlabel(T["sec"], loc="right")
        ax.set_title(T["dist_panel"].format(name=T["dist"][d], m=f"{dists[k]:g}"), loc="left", fontsize=17,
                     fontweight="semibold", color="white", pad=26)
        ax.text(0, 1.03, T["ratio"].format(v=round(ratio)), transform=ax.transAxes, fontsize=13, color=HEX(C.MUTED))
        if k == 0:
            ax.annotate(T["direct"], xy=(0.006, e[:direct_px + 1].max() * 0.95), xytext=(0.12, 0.92), color=WHITE,
                        fontsize=13, arrowprops=dict(arrowstyle="->", color=WHITE, lw=1))
        if k == 2:
            ax.annotate(T["reflect"], xy=(0.25, e[int(width * 0.25 / tmax)] * 0.9), xytext=(0.36, 0.92), color=PURPLE,
                        fontsize=13, arrowprops=dict(arrowstyle="->", color=PURPLE, lw=1))
    return save_png(fig, os.path.join(out, "distance.png"))


# ── 잡음 줄이기 전후 ─────────────────────────────────────────────────────────
def denoise_png():
    names = [("noisy", T["noisy"], WHITE)] + [(f"denoise-{s}", f"{T['denoise']} · {T['strength'][s]}", PURPLE)
                                              for s in ("light", "normal", "strong")]
    xs = [load(n)[0] for n, _, _ in names]
    fs = load("noisy")[1]
    tmax = len(xs[0]) / fs
    ref = spec_db(xs[0], fs)[2].max()
    peak = max(np.abs(x).max() for x in xs)
    fig = plt.figure(figsize=(16, 8.8))
    fig.text(0.04, 0.95, T["denoise_title"], fontsize=20, fontweight="semibold", color="white")
    for k, ((n, title, color), x) in enumerate(zip(names, xs)):
        cx = 0.045 + (k % 2) * 0.485
        cy = 0.5 - (k // 2) * 0.45
        fig.text(cx, cy + 0.36, title, fontsize=16, fontweight="semibold", color=color)
        draw_wave(fig.add_axes([cx, cy + 0.27, 0.44, 0.075]), x, fs, tmax, color, peak)
        draw_spec(fig.add_axes([cx, cy + 0.03, 0.44, 0.23]), x, fs, tmax, ref, xlabel=(k >= 2))
    return save_png(fig, os.path.join(out, "denoise.png"))


# ── 움짤(글자 없음): 손뼉 한 번이 공간 6가지에서 울리는 모습 ──────────────────────
def spaces_gif():
    """왼쪽 위부터 욕실 · 작은 방 · 거실 / 강당 · 성당 · 터널(거리 보통). 세로 = 크기(dB, 위아래 대칭, -60dB 까지),
    가로 = 0 ~ 3초(눈금 1초마다). 흰 선 = 재생 위치."""
    data = np.load(os.path.join(audio_dir, "irs.npz"))
    fs = int(data["fs"])
    tmax, fps = 3.0, 15
    W, H, cols, pad = 960, 470, 3, 20
    pw = (W - pad * (cols + 1)) // cols
    ph = (H - pad * 3) // 2
    plot_h = ph - 40
    env = {s: env_db(data[f"{s}|mid"][0], fs, tmax, pw - 24, win=0.05) for s in SPACE_IDS}
    frames = []
    for fi in range(int((tmax + 1.2) * fps)):
        t = min(tmax, fi / fps)
        im = Image.new("RGB", (W, H), C.BG)
        d = ImageDraw.Draw(im)
        for i, s in enumerate(SPACE_IDS):
            x0 = pad + (i % cols) * (pw + pad)
            y0 = pad + (i // cols) * (ph + pad)
            d.rounded_rectangle((x0, y0, x0 + pw, y0 + ph), radius=14, fill=C.CARD)
            top = y0 + 14
            cy = top + plot_h // 2
            d.line((x0 + 12, cy, x0 + pw - 12, cy), fill=C.LINE, width=1)
            e = env[s]
            reveal = int(len(e) * t / tmax)
            for px in range(reveal):
                v = (e[px] + 60) / 60
                if v > 0:
                    hh = v * (plot_h / 2 - 4)
                    d.line((x0 + 12 + px, cy - hh, x0 + 12 + px, cy + hh), fill=C.PURPLE_TEXT)
            if t < tmax:
                d.line((x0 + 12 + reveal, top, x0 + 12 + reveal, top + plot_h), fill=C.TEXT, width=2)
            for sec in (1, 2, 3):
                gx = x0 + 12 + int(len(e) * sec / tmax) - (1 if sec == 3 else 0)
                d.line((gx, top + plot_h + 4, gx, top + plot_h + 12), fill=C.MUTED, width=2)
        frames.append(im)
    return C.save_gif(frames, os.path.join(docs, "spaces.gif"), fps, colors=64, stats="full")


# ── 움짤(글자 없음): 위에서 본 거실에서 소리가 퍼지는 모습(설명용 2D 파동 계산) ────────
def wave_gif():
    """거실 6m × 4.5m 를 위에서 본 2D 파동 계산. 흰 점 = 소리 나는 곳, 노란 점 = 듣는 자리(플러그인의 거실 · 거리 보통 자리).
    아래 노란 선 = 듣는 자리에 도착한 소리, 눈금 = 바로 온 소리가 닿는 때. 60ms 를 약 4.7초에 보인다(약 80배 느리게)."""
    Lx, Ly, dx, c = 6.0, 4.5, 0.025, 343.0
    nx, ny = int(Lx / dx), int(Ly / dx)
    dt = 0.7 * dx / (c * np.sqrt(2))
    src, mic = (0.5, 2.0), (2.7, 2.25)
    si, sj = int(src[0] / dx), int(src[1] / dx)
    mi, mj = int(mic[0] / dx), int(mic[1] / dx)
    u_prev, u = np.zeros((ny, nx)), np.zeros((ny, nx))
    sim_t, fps, nframes = 0.06, 12, 56
    steps = int(sim_t / dt)
    every = steps // nframes
    f0 = 1000.0
    t0 = 1.2 / f0
    lam = (c * dt / dx) ** 2
    trace, fields = [], []
    for n in range(steps):
        lap = np.zeros_like(u)
        lap[1:-1, 1:-1] = u[2:, 1:-1] + u[:-2, 1:-1] + u[1:-1, 2:] + u[1:-1, :-2] - 4 * u[1:-1, 1:-1]
        u_next = (2 * u - u_prev + lam * lap) * (1.0 - 4e-5)
        arg = (np.pi * f0 * (n * dt - t0)) ** 2
        u_next[sj - 1:sj + 2, si - 1:si + 2] += (1 - 2 * arg) * np.exp(-arg) * 0.5
        u_next[0, :], u_next[-1, :] = u_next[1, :], u_next[-2, :]  # 단단한 벽: 소리를 되돌린다
        u_next[:, 0], u_next[:, -1] = u_next[:, 1], u_next[:, -2]
        u_prev, u = u, u_next
        trace.append(u[mj, mi])
        if n % every == 0 and len(fields) < nframes:
            fields.append((u.copy(), len(trace)))
    trace = np.array(trace)
    rw = 480
    rh = int(rw * Ly / Lx)
    m, th = 24, 86
    W, H = rw + 2 * m, m + rh + 18 + th + m
    scale = np.percentile(np.abs(fields[len(fields) // 3][0]), 99.5)
    tr_scale = np.abs(trace).max()
    first = np.hypot(mic[0] - src[0], mic[1] - src[1]) / c
    bg = np.array(C.BG) / 255
    pos, neg = np.array(C.PURPLE_TEXT) / 255, np.array([110, 200, 220]) / 255
    frames = []
    for fld, ntr in fields + [fields[-1]] * int(fps * 1.2):
        v = np.clip(fld / scale, -1, 1)
        v = np.round(np.sign(v) * np.abs(v) ** 0.6 * 8) / 8  # 계단으로 — GIF 를 작게
        p, q = np.clip(v, 0, 1)[..., None], np.clip(-v, 0, 1)[..., None]
        rgb = bg * (1 - p - q) + pos * p + neg * q
        field = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)[::-1]).resize((rw, rh), Image.NEAREST)
        im = Image.new("RGB", (W, H), C.BG)
        d = ImageDraw.Draw(im)
        im.paste(field, (m, m))
        d.rectangle((m - 3, m - 3, m + rw + 2, m + rh + 2), outline=(200, 200, 200), width=3)
        for (x, y), col in ((src, C.TEXT), (mic, C.YELLOW)):
            px, py = m + x / Lx * rw, m + rh - y / Ly * rh
            d.ellipse((px - 8, py - 8, px + 8, py + 8), fill=col, outline=(0, 0, 0), width=2)
        py0 = m + rh + 18
        cy = py0 + th // 2
        d.rectangle((m, py0, m + rw, py0 + th), fill=C.CARD)
        d.line((m, cy, m + rw, cy), fill=C.LINE)
        seg = trace[:ntr]
        xs = (m + np.arange(len(seg)) / len(trace) * rw).astype(int)
        ys = cy - seg / tr_scale * (th / 2 - 6)
        if len(seg) > 1:
            d.line(list(zip(xs.tolist(), ys.tolist())), fill=C.YELLOW, width=2)
        fx = m + first / sim_t * rw
        d.line((fx, py0 + th - 8, fx, py0 + th), fill=C.TEXT, width=2)
        frames.append(im)
    return C.save_gif(frames, os.path.join(docs, "room-wave.gif"), fps, colors=48)


# ── 소리 + 파형 영상(mp4, 언어별) ────────────────────────────────────────────
def listen_mp4(name, items):
    """items = [(소리 이름, 제목, 색)]. 한 장면씩 이어 붙인다 — 재생 위치 선이 움직인다."""
    W, H, fps, gap = 1280, 720, 25, 0.8
    xs = [load(n)[0] for n, _, _ in items]
    stereo = [sf.read(os.path.join(audio_dir, n + ".wav"), dtype="float64", always_2d=True)[0] for n, _, _ in items]
    fs = load(items[0][0])[1]
    tmax = max(len(x) for x in xs) / fs + 0.1
    ref = spec_db(xs[0], fs)[2].max()
    peak = max(np.abs(x).max() for x in xs)
    tmp = os.path.join(audio_dir, "_mp4")
    os.makedirs(tmp, exist_ok=True)
    left, width = 0.07, 0.88
    bgs = []
    for i, ((n, title, color), x) in enumerate(zip(items, xs)):
        fig = plt.figure(figsize=(W / 100, H / 100))
        fig.text(left, 0.88, T["seg"].format(i=i + 1, n=len(items)), fontsize=16, color=HEX(C.MUTED))
        fig.text(left, 0.81, title, fontsize=30, fontweight="semibold", color=color)
        draw_wave(fig.add_axes([left, 0.56, width, 0.17]), x, fs, tmax, color, peak)
        draw_spec(fig.add_axes([left, 0.1, width, 0.42]), x, fs, tmax, ref)
        p = os.path.join(tmp, f"bg{i}.png")
        fig.savefig(p, dpi=100)
        plt.close(fig)
        bgs.append(Image.open(p).convert("RGB"))
    x_left, x_right = left * W, (left + width) * W
    y_top, y_bot = (1 - 0.73) * H, (1 - 0.1) * H
    video = os.path.join(tmp, "v.mp4")
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(fps), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "30",
                             "-preset", "slow", "-tune", "stillimage", "-g", "600", video], stdin=subprocess.PIPE)
    audio = []
    for bg, x, st in zip(bgs, xs, stereo):
        dur = len(x) / fs
        nf = int(round((dur + gap) * fps))
        for k in range(nf):
            fr = bg.copy()
            if k / fps <= dur:
                px = x_left + (x_right - x_left) * (k / fps) / tmax
                ImageDraw.Draw(fr).line((px, y_top, px, y_bot), fill=(255, 255, 255), width=3)
            proc.stdin.write(fr.tobytes())
        a = np.zeros((int(round(nf / fps * fs)), 2))
        a[: len(st)] = st[: len(a)]
        audio.append(a)
    proc.stdin.close()
    proc.wait()
    sf.write(os.path.join(tmp, "a.wav"), np.concatenate(audio), fs, subtype="PCM_16")
    dst = os.path.join(out, name)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", os.path.join(tmp, "a.wav"), "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "96k", "-shortest", "-movflags", "+faststart", dst], check=True)
    return os.path.getsize(dst)


jobs = sys.argv[4].split(",") if len(sys.argv) > 4 else ["hero", "distance", "denoise", "mp4", "gifs"]
if "hero" in jobs:
    print("hero.png", hero())
if "distance" in jobs:
    print("distance.png", distance_png())
if "denoise" in jobs:
    print("denoise.png", denoise_png())
if "mp4" in jobs:
    items = [("original", T["original"], WHITE)] + [(f"reverb-{s}", f"{T['reverb']} · {T['spaces'][s]}", PURPLE)
                                                     for s in SPACE_IDS]
    print("listen-spaces.mp4", listen_mp4("listen-spaces.mp4", items))
    items = [("noisy", T["noisy"], WHITE)] + [(f"denoise-{s}", f"{T['denoise']} · {T['strength'][s]}", PURPLE)
                                              for s in ("light", "normal", "strong")]
    print("listen-denoise.mp4", listen_mp4("listen-denoise.mp4", items))
if "gifs" in jobs:
    print("spaces.gif", spaces_gif())
    print("room-wave.gif", wave_gif())
