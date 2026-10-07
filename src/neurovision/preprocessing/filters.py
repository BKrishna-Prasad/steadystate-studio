"""Windowed notch filtering, common average referencing and filter banks."""

from typing import List

import numpy as np
from scipy import signal

from ..config import DecoderConfig


class Preprocessor:
    def __init__(self, cfg: DecoderConfig):
        self.cfg = cfg

        # Notch (fs-aware)
        self.b_notch, self.a_notch = signal.iirnotch(
            w0=cfg.notch_hz, Q=cfg.notch_q, fs=cfg.fs
        )

        # Plot bandpass
        self.sos_plot = signal.butter(
            N=4,
            Wn=[cfg.plot_bp_low, cfg.plot_bp_high],
            btype="bandpass",
            fs=cfg.fs,
            output="sos",
        )

        # Filter-bank SOS filters
        self.fb_sos = []
        for lo, hi in cfg.fb_bands:
            sos = signal.butter(
                N=4, Wn=[lo, hi], btype="bandpass", fs=cfg.fs, output="sos"
            )
            self.fb_sos.append(sos)

    @staticmethod
    def car(x: np.ndarray) -> np.ndarray:
        return x - np.mean(x, axis=1, keepdims=True)

    @staticmethod
    def detrend(x: np.ndarray) -> np.ndarray:
        return signal.detrend(x, axis=0, type="linear")

    def preprocess_for_plot(self, x: np.ndarray) -> np.ndarray:
        y = signal.filtfilt(self.b_notch, self.a_notch, x, axis=0)
        y = signal.sosfiltfilt(self.sos_plot, y, axis=0)
        y = self.car(y)
        y = self.detrend(y)
        return y

    def preprocess_for_decode_fb(self, x: np.ndarray) -> List[np.ndarray]:
        y = signal.filtfilt(self.b_notch, self.a_notch, x, axis=0)
        y = self.car(y)
        y = self.detrend(y)

        out = []
        for sos in self.fb_sos:
            out.append(signal.sosfiltfilt(sos, y, axis=0))
        return out
