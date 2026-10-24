"""이 저장소의 nodes/main.py 를 서버 없이 그대로 돌려 README 용 소리 · 방 울림을 만든다.

사용(저장소 루트에서, nodes/requirements.in 의 패키지를 깐 파이썬으로):
    python -I -B docs/scripts/make_audio.py <원래 소리 mp3> <작업 폴더>
원래 소리는 PromBoard 앱 저장소의 public/assets/tutorial/narration-ko.mp3 · narration-en.mp3 다(튜토리얼 내레이션, Seed Audio).
작업 폴더에 wav · mp3 와 방 울림(irs.npz)을 쓴다. README 에 올리는 mp3 는 여기서 docs/<언어>/audio/ 로 옮긴다.
"""
import importlib.util
import os
import subprocess
import sys

import numpy as np
import soundfile as sf

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src, out = sys.argv[1:3]
os.makedirs(out, exist_ok=True)
spec = importlib.util.spec_from_file_location("ra_main", os.path.join(ROOT, "nodes", "main.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class Ctx:
    def __init__(self, name):
        self.name = name

    def progress(self, *_a, **_k):
        return True

    def check_cancel(self):
        pass

    def log(self, *_a, **_k):
        pass

    def out_path(self, _name):
        return os.path.join(out, self.name + ".wav")


def run(name, path, settings):
    return mod.NODES["room-acoustics"](Ctx(name), {"audio": path}, settings)["audio"]


def mp3(wav):
    dst = wav[:-4] + ".mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-c:a", "libmp3lame", "-b:a", "96k", dst], check=True)
    return dst


orig = os.path.join(out, "original.wav")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, orig], check=True)
mp3(orig)

for space in mod.SPACES:
    mp3(run(f"reverb-{space}", src, {"mode": "reverb", "space": space, "distance": "mid"}))
for d in ("near", "far"):
    mp3(run(f"reverb-hall-{d}", src, {"mode": "reverb", "space": "hall", "distance": d}))

# 잡음 섞기 — 깨끗한 말소리 앞뒤에 0.6초씩 빈 곳을 두고, 말소리보다 10dB 작은 '쉬—' 잡음(높은 쪽을 조금 줄인 고른 잡음)을 섞는다.
x, fs = sf.read(orig, dtype="float64", always_2d=True)
rng = np.random.default_rng(7)
pad = int(0.6 * fs)
x = np.concatenate([np.zeros((pad, x.shape[1])), x, np.zeros((pad, x.shape[1]))])
noise = rng.standard_normal(x.shape)
k = np.exp(-np.arange(64) / 6.0)
k /= k.sum()
noise = np.stack([np.convolve(noise[:, c], k, mode="same") for c in range(x.shape[1])], axis=1)
noise *= np.sqrt(np.mean(x[pad:-pad] ** 2)) / np.sqrt(np.mean(noise**2)) / (10 ** (10 / 20))
noisy = os.path.join(out, "noisy.wav")
sf.write(noisy, np.clip(x + noise, -1, 1), fs, subtype="PCM_16")
mp3(noisy)
for s in ("light", "normal", "strong"):
    mp3(run(f"denoise-{s}", noisy, {"mode": "denoise", "strength": s}))

# 방 울림(임펄스 응답) — 손뼉 한 번이 공간마다 어떻게 울리는지 그림용
irs = {}
for space in mod.SPACES:
    for d in mod.DISTANCES:
        irs[f"{space}|{d}"], _ = mod._room_impulse(space, d, fs)
np.savez_compressed(os.path.join(out, "irs.npz"), fs=fs, **irs)
print("done", fs, len(os.listdir(out)), "files")
