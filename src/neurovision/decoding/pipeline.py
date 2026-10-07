"""Sample-indexed window scheduling and decoder state changes."""

from dataclasses import asdict, dataclass

import numpy as np

from ..preprocessing.filters import Preprocessor
from .decision import DecisionSmoother
from .fbcca import FBCCA


@dataclass
class WindowResult:
    end_sample: int
    end_time_sec: float
    scores: list[float]
    action: str
    state_idx: int | None
    frequency_hz: float
    changed: bool
    best_idx: int
    best_score: float
    margin: float

    def to_dict(self):
        return asdict(self)

    def command(self):
        if not self.changed:
            return None
        if self.state_idx is None:
            return f"SSVEP_NONE;FREQ=0;BEST={self.best_idx};S={self.best_score:.3f};M={self.margin:.3f}"
        return f"SSVEP_IDX={self.state_idx};FREQ={self.frequency_hz};S={self.best_score:.3f};M={self.margin:.3f}"


class Pipeline:
    def __init__(self, settings):
        self.settings = settings.validate()
        self.cfg = settings.decoder
        self.window_samples = round(self.cfg.fs * self.cfg.window_sec)
        self.step_samples = round(self.cfg.fs * self.cfg.step_sec)
        self.preprocessor = Preprocessor(self.cfg)
        self.decoder = FBCCA(self.cfg)
        self.reset()

    def reset(self):
        self.pending = np.empty(
            (0, self.settings.lsl.expected_channels), dtype=np.float32
        )
        self.smoother = DecisionSmoother(self.cfg)
        self.state = None
        self.consumed = 0

    def feed(self, chunk):
        """Decode every complete scheduled window, independent of input chunk size."""
        chunk = np.asarray(chunk, dtype=np.float32)
        if chunk.ndim != 2 or chunk.shape[1] != self.settings.lsl.expected_channels:
            raise ValueError("EEG chunk does not match configured channel count")
        if not np.isfinite(chunk).all():
            raise ValueError("EEG contains non-finite samples; decoding stopped")
        self.pending = np.concatenate((self.pending, chunk))
        results = []
        while len(self.pending) >= self.window_samples:
            window = self.pending[: self.window_samples]
            scores = self.decoder.score_window(
                self.preprocessor.preprocess_for_decode_fb(window)
            )
            info = self.smoother.step(scores)
            previous = self.state
            if info.action == "SET_IDX":
                self.state = info.idx
            elif info.action == "SET_NONE":
                self.state = None
            end = self.consumed + self.window_samples
            results.append(
                WindowResult(
                    end,
                    end / self.cfg.fs,
                    scores.tolist(),
                    info.action,
                    self.state,
                    0.0 if self.state is None else self.cfg.freqs[self.state],
                    previous != self.state,
                    info.best_idx,
                    info.best_score,
                    info.margin,
                )
            )
            self.pending = self.pending[self.step_samples :]
            self.consumed += self.step_samples
        return results
