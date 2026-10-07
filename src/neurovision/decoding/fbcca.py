"""Filter Bank Canonical Correlation Analysis with harmonic references."""

from typing import List

import numpy as np

from ..config import DecoderConfig


class FBCCA:
    def __init__(self, cfg: DecoderConfig):
        self.cfg = cfg

        # Precompute filter-bank weights and their sum (for normalization to 0..1)
        self.weights = np.array(
            [
                (k + 1) ** (-cfg.fb_weight_a) + cfg.fb_weight_b
                for k in range(len(cfg.fb_bands))
            ],
            dtype=np.float64,
        )
        self.wsum = float(np.sum(self.weights))

    def _reference_signals(self, f: float, n: int) -> np.ndarray:
        t = np.arange(n) / self.cfg.fs
        refs = []
        for h in range(1, self.cfg.harmonics + 1):
            refs.append(np.sin(2 * np.pi * (h * f) * t))
            refs.append(np.cos(2 * np.pi * (h * f) * t))
        return np.stack(refs, axis=1).astype(np.float64)

    @staticmethod
    def _cca_maxcorr(X: np.ndarray, Y: np.ndarray, ridge: float = 1e-6) -> float:
        X = X.astype(np.float64)
        Y = Y.astype(np.float64)

        X -= X.mean(axis=0, keepdims=True)
        Y -= Y.mean(axis=0, keepdims=True)

        Cxx = (X.T @ X) / (X.shape[0] - 1) + ridge * np.eye(X.shape[1])
        Cyy = (Y.T @ Y) / (Y.shape[0] - 1) + ridge * np.eye(Y.shape[1])
        Cxy = (X.T @ Y) / (X.shape[0] - 1)

        Lx = np.linalg.cholesky(Cxx)
        Ly = np.linalg.cholesky(Cyy)

        Wx = np.linalg.solve(Lx, Cxy)
        W = np.linalg.solve(Ly, Wx.T).T

        svals = np.linalg.svd(W, compute_uv=False)
        return float(np.clip(svals[0], 0.0, 1.0))

    def score_window(self, fb_windows: List[np.ndarray]) -> np.ndarray:
        """
        Returns normalized FBCCA scores in [0..1] (approximately):
          score = sum_k w_k * r_k^2 / sum_k w_k
        """
        n_freqs = len(self.cfg.freqs)
        scores = np.zeros(n_freqs, dtype=np.float64)

        for fi, f in enumerate(self.cfg.freqs):
            acc = 0.0
            for k, Xk in enumerate(fb_windows):
                Y = self._reference_signals(f, Xk.shape[0])
                r = self._cca_maxcorr(Xk, Y)
                acc += self.weights[k] * (r**2)
            scores[fi] = acc / self.wsum  # normalize
        return scores
