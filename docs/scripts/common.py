"""README 그림 공통 — 색 · 글꼴 · GIF 저장. make_audio.py · make_visuals.py 가 쓴다.

글꼴은 Pretendard(한글) 를 쓴다. README_FONT_DIR 에 Pretendard-*.otf 가 든 폴더를 주거나, Windows 사용자 글꼴 폴더에 설치해 둔다.
GIF · 영상 · mp3 는 ffmpeg(PATH)로 만든다.
"""
import os
import subprocess
import tempfile

from PIL import ImageFont

FONT_DIR = os.environ.get("README_FONT_DIR") or os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts")

BG = (23, 23, 23)
CARD = (35, 35, 35)
LINE = (58, 58, 58)
TEXT = (255, 255, 255)
MUTED = (165, 165, 165)
PURPLE = (136, 63, 215)
PURPLE_TEXT = (187, 134, 252)
YELLOW = (255, 196, 0)

_fonts = {}


def font(size, weight="SemiBold"):
    key = (size, weight)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(os.path.join(FONT_DIR, f"Pretendard-{weight}.otf"), size)
    return _fonts[key]


def text_size(draw, s, f):
    l, t, r, b = draw.textbbox((0, 0), s, font=f)
    return r - l, b - t


def hex_color(c):
    return "#%02x%02x%02x" % c


def save_gif(frames, path, fps, colors=64, dither="none", stats="diff"):
    """프레임(PIL RGB) → ffmpeg 팔레트 두 번 → GIF. 파일 크기를 돌려준다.
    stats="diff" 는 바뀌는 부분 색을 우선한다. 조금씩 자라는 면은 색이 빠질 수 있어 그런 그림은 "full" 을 쓴다."""
    with tempfile.TemporaryDirectory() as tmp:
        for i, fr in enumerate(frames):
            fr.convert("RGB").save(os.path.join(tmp, f"f{i:05d}.png"))
        pat = os.path.join(tmp, "f%05d.png")
        pal = os.path.join(tmp, "pal.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", pat,
                        "-vf", f"palettegen=max_colors={colors}:stats_mode={stats}", pal], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", pat, "-i", pal,
                        "-lavfi", f"paletteuse=dither={dither}:diff_mode=rectangle", "-loop", "0", path], check=True)
    return os.path.getsize(path)
