# 공간 울림 · 잡음 줄이기 (PromBoard 플러그인)

[English](#english)

소리에 욕실 · 거실 · 성당 같은 실제 공간의 울림을 입히거나, 말소리 뒤의 잡음을 줄이는 PromBoard 커뮤니티 플러그인입니다. 오픈소스 [pyroomacoustics](https://github.com/LCAV/pyroomacoustics)(MIT)의 방 시뮬레이션과 잡음 줄이기 기능을 씁니다. AI 모델을 받지 않고, 그래픽카드 없이 이 PC 의 CPU 로 몇 초 안에 끝납니다.

- 플러그인 id: `promboard.room-acoustics`
- 필요한 앱: PromBoard 1.0.2 이상
- 라이선스: MIT

## 설치

1. PromBoard 홈 왼쪽 [플러그인] → 커뮤니티 플러그인에서 「공간 울림 · 잡음 줄이기」를 설치합니다.
2. 커뮤니티 플러그인이라 제한 모드를 끄고 플러그인을 켭니다.
3. 처음 한 번 [실행 준비]를 누릅니다. 파이썬과 패키지를 로컬 AI 모델 폴더에 받습니다(받는 양 약 100MB, 디스크 약 250MB — 다른 플러그인이 이미 받은 파이썬 · uv 는 다시 받지 않습니다). Windows PC 에서 10초 남짓 걸렸습니다.

## 쓰는 법

**캔버스 노드**: 노드 추가 목록에서 「공간 울림 · 잡음 줄이기」를 놓고 소리 노드를 연결한 뒤 ▷ 를 누릅니다.

**렌더 탭**: 소리 클립을 오른쪽 클릭 → [오디오 효과 ›] → 「공간 울림 · 잡음 줄이기」 → 설정을 고르고 [효과 입히기]. 효과를 입힌 소리는 같은 클립에 새 버전으로 들어가고, [효과 되돌리기]로 원래 소리로 돌아갈 수 있습니다.

## 설정

| 설정 | 고르는 것 | 뜻 |
|---|---|---|
| 모드 | 공간 울림 · 잡음 줄이기 | 공간 울림은 고른 공간에서 녹음한 것처럼 울림을 입힙니다. 잡음 줄이기는 말소리 뒤의 '쉬—' 하는 잡음을 줄입니다 |
| 공간 | 욕실 · 작은 방 · 거실 · 강당 · 성당 · 터널 | 공간 울림일 때만 씁니다. 욕실은 짧고 또렷하게, 성당 · 터널은 길게 울립니다 |
| 거리 | 가까이 · 보통 · 멀리 | 공간 울림일 때만 씁니다. 멀수록 울림이 커지고 소리가 멀게 들립니다 |
| 잡음 줄이기 세기 | 약하게 · 보통 · 강하게 | 잡음 줄이기일 때만 씁니다. 강할수록 잡음이 더 줄지만 말소리가 뭉개질 수 있습니다 |

## 어떻게 동작하나

- **공간 울림**: pyroomacoustics 의 상자 모양 방 시뮬레이션(`ShoeBox`)으로 방 울림(임펄스 응답)을 계산해 소리에 입힙니다. 이른 반사는 거울상 음원법, 늦은 울림은 광선 추적으로 계산합니다. 벽이 소리를 먹는 정도는 공간마다 정한 잔향 시간(RT60)에서 거꾸로 계산합니다(`pra.inverse_sabine`). 귀 사이 거리만큼 떨어진 마이크 두 개로 받아 결과는 스테레오입니다. 소리가 듣는 사람까지 가는 시간만큼은 앞에서 잘라 원래 소리와 박자가 맞고, 끝에 울림 꼬리(최대 3초)가 붙습니다. 크기는 원래 소리와 비슷하게 맞춥니다.
- **잡음 줄이기**: pyroomacoustics 의 스펙트럼 빼기(`denoise.SpectralSub`)를 채널마다 돌립니다. 0.6초 안에서 가장 작은 소리를 잡음으로 보고 뺍니다. 말소리에 맞춘 방식이라 길게 끄는 음악은 소리가 뭉개질 수 있습니다.
- 읽는 형식: wav · mp3 · flac · ogg(m4a · aac · webm 은 못 읽습니다). 결과는 WAV 입니다. 한 번에 10분까지 처리합니다(렌더 탭은 클립 300초까지).
- 인터넷을 쓰지 않습니다. 소리는 이 PC 밖으로 나가지 않습니다.

## 파일

```
manifest.json                 플러그인 정보 · 노드 정의
icon.png
nodes/main.py                 노드 코드
nodes/requirements.in         직접 쓰는 패키지
nodes/requirements-*.txt      운영체제별 해시 잠금 파일(uv pip compile --generate-hashes, Python 3.12)
```

## 함께 쓰는 오픈소스

| 패키지 | 라이선스 |
|---|---|
| [pyroomacoustics](https://github.com/LCAV/pyroomacoustics) 0.10.1 | MIT |
| numpy · scipy | BSD-3-Clause |
| [soundfile](https://github.com/bastibe/python-soundfile) 0.14.0 (libsndfile 포함) | BSD-3-Clause (libsndfile: LGPL-2.1) |
| Cython · cffi · pycparser · typing-extensions | Apache-2.0 · MIT · BSD-3-Clause · PSF |

패키지는 실행 준비 때 PyPI 에서 받습니다. 이 저장소에는 들어 있지 않습니다.

---

## English

**Room Reverb · Noise Reduction** is a PromBoard community plugin. It adds the reverb of a real space (bathroom, living room, cathedral, …) to a sound, or reduces the background noise behind speech. It uses the room simulation and denoising features of the open-source [pyroomacoustics](https://github.com/LCAV/pyroomacoustics) (MIT). No AI model is downloaded, and it runs on the CPU of this PC in a few seconds.

- Plugin id: `promboard.room-acoustics`
- Requires PromBoard 1.0.2 or later
- License: MIT

### Install

1. In PromBoard Home, open **Plugins** → **Community plugins** and install "공간 울림 · 잡음 줄이기".
2. It is a community plugin, so turn off restricted mode and turn the plugin on.
3. Press **Prepare** once. Python and the packages are downloaded into the local AI model folder (about 100 MB to download, about 250 MB on disk; Python and uv already fetched for another plugin are reused).

### Use

**Canvas node**: add the node, connect an audio node and press ▷.

**Render tab**: right-click an audio clip → **Audio effects ›** → pick the effect → choose the settings → **Apply effect**. The processed sound goes into the same clip as a new version, and **Undo effect** brings back the original sound.

### Settings

| Setting | Options | Meaning |
|---|---|---|
| Mode | Room reverb · Noise reduction | Room reverb makes the sound feel recorded in the chosen space. Noise reduction lowers the hiss behind speech |
| Space | Bathroom · Small room · Living room · Hall · Cathedral · Tunnel | Room reverb only. Bathrooms ring short and bright, cathedrals and tunnels ring long |
| Distance | Near · Medium · Far | Room reverb only. Farther means more reverb and a more distant sound |
| Noise reduction strength | Light · Normal · Strong | Noise reduction only. Stronger removes more noise but can smear speech |

The setting labels inside the app are in Korean for now (the plugin format takes one language).

### How it works

- **Room reverb**: computes a room impulse response with pyroomacoustics' shoebox room simulation (image source method for early reflections, ray tracing for the late tail) and convolves the sound with it. Wall absorption is derived from each space's reverberation time (RT60) with `pra.inverse_sabine`. Two microphones spaced like human ears give a stereo result. The travel time to the listener is trimmed so the result stays in sync with the original, and a reverb tail (up to 3 s) is added at the end. The loudness is matched to the original.
- **Noise reduction**: runs pyroomacoustics' spectral subtraction (`denoise.SpectralSub`) on each channel, using the minimum level within 0.6 s as the noise estimate. It is tuned for speech; long sustained music notes may get smeared.
- Reads wav · mp3 · flac · ogg (not m4a · aac · webm). Writes WAV. Up to 10 minutes at a time (the render tab sends clips of up to 300 s).
- No internet access. The sound never leaves this PC.

### Third-party open source

pyroomacoustics 0.10.1 (MIT), numpy · scipy (BSD-3-Clause), soundfile 0.14.0 (BSD-3-Clause, bundles libsndfile under LGPL-2.1), Cython (Apache-2.0), cffi (MIT), pycparser (BSD-3-Clause), typing-extensions (PSF). The packages are downloaded from PyPI during **Prepare** and are not included in this repository.
