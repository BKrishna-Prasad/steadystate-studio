"""Synthetic harmonic signals with channel variation and background noise."""

import numpy as np
from scipy import signal


def band_limited_noise(N, fs, low=1.0, high=40.0, rng=None):
    rng = rng or np.random.default_rng(0)
    x = rng.standard_normal(N)
    sos = signal.butter(4, [low, high], btype="bandpass", fs=fs, output="sos")
    y = signal.sosfiltfilt(sos, x)
    y = y / (np.std(y) + 1e-9)
    return y


def make_segment(
    fs: int,
    duration_s: float,
    n_ch: int,
    ssvep_freq: float | None,
    ssvep_amp: float,
    harmonics: int,
    noise_amp: float,
    line_amp: float,
    drift_amp: float,
    rng: np.random.Generator,
) -> np.ndarray:
    N = int(duration_s * fs)
    t = np.arange(N) / fs

    X = np.zeros((N, n_ch), dtype=np.float64)

    # EEG-like band-limited noise
    for ch in range(n_ch):
        X[:, ch] = noise_amp * band_limited_noise(N, fs, 1.0, 40.0, rng=rng)

    # 50 Hz line noise
    if line_amp > 0:
        phases = rng.uniform(0, 2 * np.pi, size=n_ch)
        X += line_amp * np.sin(2 * np.pi * 50.0 * t)[:, None] * np.cos(phases)[None, :]

    # slow drift
    if drift_amp > 0:
        drift = drift_amp * signal.sawtooth(2 * np.pi * 0.03 * t)  # very slow
        X += drift[:, None]

    # SSVEP component (same freq across channels, different amp/phase)
    if ssvep_freq is not None:
        amps = ssvep_amp * (0.6 + 0.8 * rng.random(n_ch))
        phs = rng.uniform(0, 2 * np.pi, size=n_ch)
        for h in range(1, harmonics + 1):
            X += (amps / h) * np.sin(
                2 * np.pi * (h * ssvep_freq) * t[:, None] + phs[None, :]
            )

    return X
