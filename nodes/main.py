"""공간 울림 · 잡음 줄이기 — pyroomacoustics(MIT) 로 소리에 실제 공간의 울림을 입히거나 잡음을 줄인다.

PromBoard 노드 코드 약속(앱 저장소 docs/Scrum4/02_스키마-v0.md §6)을 따른다.
  - NODES = {노드 id: 함수}. 노드 id 는 manifest.json 의 nodes[].id 와 같다.
  - 함수(ctx, inputs, settings) -> {출력 포트 id: 값}. 소리 입력은 읽기 전용 파일 경로, 결과는 ctx.out_path() 에 쓴 WAV 경로.
  - 렌더 탭 [오디오 효과 ›] 로 돌 때도 같은 함수다(manifest renderEffect: "audio").

공간 울림
  pyroomacoustics 의 방 시뮬레이션(ShoeBox — 상자 모양 방)으로 방 울림(임펄스 응답)을 계산해 소리에 입힌다. 이른 반사는 거울상
  음원법(max_order 3), 늦은 울림은 광선 추적으로 계산한다(하이브리드 — 큰 공간도 몇 초 안에 끝난다). 늦은 울림이 중간에 끊기지
  않게 두 가지를 맞춘다.
    - 광선 수: 듣는 자리 공(반지름 0.5m)에 시간 칸마다 광선이 평균 10번은 닿게 고른다. 모자라면 칸이 비어 꼬리가 끊긴다(강당 ·
      성당 · 터널). 작은 방은 광선 1만 개로 이미 넉넉해 그대로다. 광선이 10만 개를 넘을 만큼 큰 방은 시간 칸을 넓힌다(성당).
    - 꼬리 재료 시각: 라이브러리 0.10.1 의 poisson_sequence 는 시간이 갈수록 빨라지는 포아송 과정을 구간 시작의 빠르기로만
      뽑는다. 큰 방에서 듣는 자리가 가까우면 시작 빠르기가 초당 한 번 남짓이라 첫 간격이 1초 가까이 벌어지고, 그동안 꼬리가
      통째로 빈다(귀마다 따로 뽑아 한쪽만 비기도 한다). 같은 빠르기 식을 누적해서 바르게 뽑는 함수로 바꿔 끼운다.
  벽 흡음률은 공간마다 정한
  잔향 시간(RT60)에서 역산한다(pra.inverse_sabine). 마이크 둘(귀 사이 18cm)이라 결과는 스테레오다. 입력이 스테레오면 하나로
  섞어 소리를 낸다. 소리가 마이크까지 가는 시간만큼은 앞에서 잘라 원래 소리와 박자가 맞는다. 울림 꼬리(최대 3초)가 뒤에 붙는다.
  크기는 원래 소리와 비슷하게(RMS) 맞추고 넘치지 않게 줄인다.

잡음 줄이기
  pyroomacoustics 의 스펙트럼 빼기(denoise.SpectralSub) 를 채널마다 돌린다. 라이브러리 한 번에 돌리기(apply_spectral_sub)와 같은
  흐름이지만, 긴 소리에서 취소 · 진행률을 받으려고 같은 클래스(STFT · SpectralSub)로 반복을 직접 돈다. 라이브러리 출력은 반 프레임
  늦어서 그만큼 당겨 원래 소리와 박자를 맞춘다. 잡음 추정은 0.6초 안의 가장 작은 값이다 — 말소리용이라 길게 끄는 음악은 소리가
  뭉개질 수 있다. 라이브러리는 잡음 추정 칸을 0 으로 시작해 처음 0.6초는 잡음을 0 으로 보고 줄이지 않는다. 그래서 앞 0.6초를
  한 번 미리 흘려 추정 칸만 채우고(결과는 버린다) 처음부터 다시 돈다. 그 뒤 칸이 실제 소리로 다 바뀌면 결과는 예전과 같다.
"""

import math

#: 공간 — (가로 · 세로 · 높이 m, 잔향 시간 RT60 초, 거리 가까이 · 보통 · 멀리 m)
SPACES = {
    "bathroom": ((2.4, 1.8, 2.4), 0.9, (0.5, 1.0, 1.5)),
    "small-room": ((3.5, 3.0, 2.5), 0.35, (0.6, 1.4, 2.4)),
    "living-room": ((6.0, 4.5, 2.6), 0.55, (0.8, 2.2, 4.2)),
    "hall": ((24.0, 16.0, 9.0), 1.6, (1.0, 5.0, 14.0)),
    "cathedral": ((60.0, 26.0, 24.0), 4.5, (1.5, 8.0, 30.0)),
    "tunnel": ((120.0, 7.0, 5.0), 2.8, (1.5, 10.0, 40.0)),
}
DISTANCES = ("near", "mid", "far")
#: 잡음 줄이기 세기 — (최대로 줄일 dB, 잡음 추정 키우기 배수 beta). 라이브러리 잡음 추정(최솟값)이 실제보다 작게 나와 beta 를 크게 둔다.
STRENGTHS = {"light": (12, 100), "normal": (20, 250), "strong": (28, 500)}
#: 한 번에 처리할 최대 길이(초) — 메모리를 지키려고. 렌더 탭은 300초까지 보낸다.
MAX_SECONDS = 600
#: 울림 꼬리 최대 길이(초)
MAX_TAIL_SECONDS = 3.0
#: 두 마이크 사이(m) — 사람 귀 사이 정도
EAR_SPACING = 0.18
#: 소리를 마이크 정면에서 옆으로 비킨 거리(m)
SOURCE_OFFSET = 0.25
#: 아주 작은 흔들림(약 -140dB) — 완전한 무음에서 라이브러리 이득 계산이 0 으로 나누지 않게
DITHER = 1e-7
#: 광선 추적 — 듣는 자리 공 반지름(m) · 시간 칸마다 공에 닿을 광선 수 목표 · 광선 수 최소 · 최대 · 시간 칸(초) 기본 · 최대.
#: 라이브러리 기본 규칙(Vorländer 2008 식 11.12)은 목표 20 이라 성당에서 광선 70만 개가 넘는다 — 목표를 10 으로 두고 칸을 넓혀 맞춘다.
RT_RADIUS = 0.5
RT_HITS = 10
RT_RAYS = (10000, 100000)
RT_BIN = (0.004, 0.016)


def _read_audio(path):
    import numpy as np
    import soundfile as sf

    try:
        data, fs = sf.read(path, dtype="float32", always_2d=True)
    except Exception as e:  # libsndfile 이 못 읽는 형식(m4a · aac · webm 등)
        raise ValueError(
            "이 소리 파일 형식은 읽을 수 없어요. wav · mp3 · flac · ogg 로 바꿔서 넣어 주세요."
            f" ({type(e).__name__})"
        ) from None
    if data.shape[0] == 0:
        raise ValueError("소리가 비어 있어요.")
    if data.shape[0] > MAX_SECONDS * fs:
        raise ValueError(f"한 번에 {MAX_SECONDS // 60}분까지 처리할 수 있어요. 소리를 나눠서 넣어 주세요.")
    return np.asarray(data, dtype=np.float64), int(fs)


def _write_wav(ctx, data, fs, name):
    import numpy as np
    import soundfile as sf

    out = ctx.out_path(name)
    sf.write(out, np.clip(np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0), -1.0, 1.0), fs, subtype="PCM_16")
    return out


def _ray_tracing(volume, c):
    """광선 수 · 시간 칸(초). 듣는 자리 공에 칸마다 닿는 광선이 평균 RT_HITS 번이 되게 고른다(라이브러리 기본 규칙과 같은 식).
    광선이 RT_RAYS[1] 을 넘게 필요하면 칸을 RT_BIN[1] 까지 넓혀 줄인다."""

    def needed(b):  # 칸(b 초)마다 공에 평균 RT_HITS 번 닿게 하는 데 드는 광선 수
        return RT_HITS * volume / (math.pi * RT_RADIUS**2 * c * b)

    b = RT_BIN[0]
    if needed(b) > RT_RAYS[1]:
        b = min(RT_BIN[1], b * needed(b) / RT_RAYS[1])
    return min(RT_RAYS[1], max(RT_RAYS[0], math.ceil(needed(b)))), b


def _patch_poisson_sequence():
    """pyroomacoustics 0.10.1 의 늦은 울림 재료 시각(simulation.rt.poisson_sequence)을 바르게 뽑는 것으로 바꿔 끼운다.

    빠르기 식은 라이브러리와 같다: mu(t) = min(4π c³ / V · (t0 + t)², max_rate). 라이브러리는 다음 간격을 지금 빠르기 하나로만
    뽑아(dt = -ln z / mu) 시작 빠르기가 아주 작으면 간격이 크게 튄다. 여기서는 빠르기를 누적한 값이 지수 분포만큼 늘어나는
    시각을 바로 푼다(역누적 비율법) — 빠르기가 max_rate 에 닿기 전에는 (t0 + t)³ 이 3E / fpcv 만큼 늘고, 닿은 뒤에는 E / max_rate.
    """
    import numpy as np
    import pyroomacoustics as pra
    from pyroomacoustics import random as pra_random
    from pyroomacoustics.simulation import rt

    # 잠금 파일이 고정한 0.10.1 의 함수 모양(인자 · 돌려주는 값)에 맞춘 것이다 — 다른 판이면 건드리지 않는다.
    if pra.__version__ != "0.10.1" or getattr(rt.poisson_sequence, "_promboard", False):
        return

    def poisson_sequence(volume, duration, c, max_rate=10000, t0=None):
        rng = pra_random.get_rng()
        fpcv = 4 * np.pi * c**3 / volume
        if t0 is None:
            t0 = ((2 * np.log(2)) / fpcv) ** (1.0 / 3.0)
        t_cap = math.sqrt(max_rate / fpcv) - t0  # 이 시각부터 빠르기가 max_rate 로 고정
        times = [t0]
        while times[-1] < t0 + duration:
            t = times[-1]
            e = -math.log1p(-rng.uniform())  # 지수 분포(평균 1), 0 을 뽑아도 log(0) 이 나지 않게
            if t < t_cap:
                grow = 3 * e / fpcv
                if (t0 + t_cap) ** 3 - (t0 + t) ** 3 >= grow:
                    times.append((((t0 + t) ** 3 + grow) ** (1.0 / 3.0)) - t0)
                    continue
                e -= fpcv / 3 * ((t0 + t_cap) ** 3 - (t0 + t) ** 3)
                t = t_cap
            times.append(t + e / max_rate)
        return t0, np.array(times)

    poisson_sequence._promboard = True
    rt.poisson_sequence = poisson_sequence


def _room_impulse(space, distance, fs):
    """공간 · 거리의 방 울림 두 채널(마이크 왼쪽 · 오른쪽)과 잔향 시간."""
    import numpy as np
    import pyroomacoustics as pra

    dim, rt60, dists = SPACES[space]
    dist = dists[DISTANCES.index(distance)]
    e_absorption, _ = pra.inverse_sabine(rt60, dim)
    room = pra.ShoeBox(dim, fs=fs, materials=pra.Material(e_absorption), max_order=3, air_absorption=True)
    rays, hist_bin = _ray_tracing(dim[0] * dim[1] * dim[2], room.c)
    room.set_ray_tracing(receiver_radius=RT_RADIUS, n_rays=rays, energy_thres=1e-5, hist_bin_size=hist_bin)
    _patch_poisson_sequence()
    height = min(1.6, dim[2] - 0.5)
    src_x = 0.5 if dim[0] < 10 else dim[0] * 0.1
    # 소리를 가운데서 조금(SOURCE_OFFSET) 비켜 두어 두 마이크의 울림이 달라진다(가운데면 좌우가 거울처럼 같다).
    src = np.array([src_x, dim[1] * 0.5 - SOURCE_OFFSET, height])
    mic = np.array([src_x + dist, dim[1] * 0.5, height])
    room.add_source(src)
    room.add_microphone_array(np.c_[mic + [0.0, -EAR_SPACING / 2, 0.0], mic + [0.0, EAR_SPACING / 2, 0.0]])
    room.compute_rir()
    rirs = [np.asarray(room.rir[m][0], dtype=np.float64) for m in range(2)]
    length = min(len(r) for r in rirs)
    # 소리가 가까운 마이크까지 가는 시간(라이브러리 분수 지연 필터의 반 포함)을 2ms 남기고 잘라 원래 소리와 박자를 맞춘다.
    nearest = float(np.linalg.norm(src - (mic + [0.0, -EAR_SPACING / 2, 0.0])))
    direct = int(fs * nearest / room.c) + pra.constants.get("frac_delay_length") // 2
    start = max(0, min(length - 1, direct - int(0.002 * fs)))
    end = min(length, start + int(fs * (rt60 * 1.5 + 0.1)))
    return np.stack([r[start:end] for r in rirs]), rt60


def _reverb(ctx, data, fs, settings):
    import numpy as np
    from scipy.signal import oaconvolve

    space = settings["space"]
    distance = settings["distance"]
    if space not in SPACES or distance not in DISTANCES:
        raise ValueError("공간 또는 거리 설정을 알 수 없어요.")
    ctx.progress(0.15, "room")
    impulse, rt60 = _room_impulse(space, distance, fs)
    ctx.check_cancel()
    mono = data.mean(axis=1)
    n = len(mono)
    tail = min(impulse.shape[1] - 1, int(fs * min(rt60, MAX_TAIL_SECONDS)))
    ctx.progress(0.6, "convolve")
    out = np.stack([oaconvolve(mono, impulse[c])[: n + tail] for c in range(2)], axis=1)
    if tail > 0:
        fade = min(tail, int(0.05 * fs))
        out[-fade:] *= np.linspace(1.0, 0.0, fade)[:, None]
    ctx.check_cancel()
    rms_in = math.sqrt(float(np.mean(mono**2)))
    rms_out = math.sqrt(float(np.mean(out[:n] ** 2)))
    gain = rms_in / rms_out if rms_out > 1e-12 else 1.0
    peak = float(np.max(np.abs(out))) * gain
    if peak > 0.98:
        gain *= 0.98 / peak
    return out * gain


def _denoise(ctx, data, fs, settings):
    import numpy as np
    import pyroomacoustics as pra
    from pyroomacoustics.denoise.spectral_subtraction import SpectralSub
    from pyroomacoustics.transform import STFT

    strength = settings["strength"]
    if strength not in STRENGTHS:
        raise ValueError("잡음 줄이기 세기 설정을 알 수 없어요.")
    db_reduc, beta = STRENGTHS[strength]
    nfft = 1024 if fs > 32000 else 512  # 프레임 약 21ms
    hop = nfft // 2
    lookback = max(1, int(0.6 * fs / hop))
    window = pra.hann(nfft, flag="asymmetric", length="full")
    n, channels = data.shape
    rng = np.random.default_rng(0)
    out = np.zeros_like(data)
    frames = (n + hop) // hop
    total = frames * channels
    done = 0
    for c in range(channels):
        x = np.concatenate([data[:, c] + DITHER * rng.standard_normal(n), np.zeros(hop)])
        scnr = SpectralSub(nfft, db_reduc, lookback, beta, 1)
        # 잡음 추정 칸(lookback + 1)을 앞 0.6초로 미리 채운다 — 라이브러리는 칸을 0 으로 시작해 처음 0.6초를 줄이지 않는다.
        # 첫 프레임은 앞 절반이 0 이라 칸에 넣지 않고 STFT 만 채운다. 이 결과는 버린다.
        warm = STFT(nfft, hop=hop, analysis_window=window, streaming=True)
        warm.analysis(x[:hop])
        for k in range(1, min(lookback + 2, len(x) // hop)):
            warm.analysis(x[k * hop : (k + 1) * hop])
            scnr.compute_gain_filter(warm.X)
        stft = STFT(nfft, hop=hop, analysis_window=window, streaming=True)
        y = np.zeros(len(x))
        pos = 0
        while len(x) - pos >= hop:
            stft.analysis(x[pos : pos + hop])
            gain = np.nan_to_num(np.asarray(scnr.compute_gain_filter(stft.X)), nan=1.0)
            y[pos : pos + hop] = stft.synthesis(gain * stft.X)
            pos += hop
            done += 1
            if done % 200 == 0:
                ctx.check_cancel()
                ctx.progress(0.1 + 0.8 * done / total, "denoise")
        # 라이브러리 출력은 반 프레임(hop) 늦다 — 당겨서 원래 소리와 맞춘다.
        out[:, c] = y[hop : hop + n]
    return out


def room_acoustics(ctx, inputs, settings):
    ctx.progress(0.02, "load")
    data, fs = _read_audio(inputs["audio"])
    ctx.check_cancel()
    if settings["mode"] == "reverb":
        out = _reverb(ctx, data, fs, settings)
        name = "room.wav"
    elif settings["mode"] == "denoise":
        out = _denoise(ctx, data, fs, settings)
        name = "denoised.wav"
    else:
        raise ValueError("모드 설정을 알 수 없어요.")
    ctx.progress(0.95, "save")
    path = _write_wav(ctx, out, fs, name)
    ctx.progress(1.0, "done")
    return {"audio": path}


NODES = {"room-acoustics": room_acoustics}
