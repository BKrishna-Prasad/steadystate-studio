"""Score, margin and temporal gates for target and no-control decisions."""

from dataclasses import dataclass
from typing import Literal, Optional

import numpy as np

from ..config import DecoderConfig

DecisionAction = Literal["HOLD", "SET_IDX", "SET_NONE"]


@dataclass
class DecisionInfo:
    action: DecisionAction
    idx: Optional[int]  # valid if action == SET_IDX
    best_idx: int
    best_score: float
    second_score: float
    margin: float


class DecisionSmoother:
    """
    Proper state machine:
    - HOLD: keep previous state (do not output NONE just because we are "pending")
    - SET_IDX: when stable winner confirmed
    - SET_NONE: only when we've seen sustained FAIL windows
    """

    def __init__(self, cfg: DecoderConfig):
        self.cfg = cfg
        self._winner_idx: Optional[int] = None
        self._win_streak: int = 0
        self._fail_streak: int = 0

    def step(self, scores: np.ndarray) -> DecisionInfo:
        scores = np.asarray(scores, dtype=float)
        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])
        s_sorted = np.sort(scores)
        second_score = float(s_sorted[-2]) if scores.size >= 2 else float("-inf")
        margin = best_score - second_score

        passes = (best_score >= self.cfg.min_score) and (margin >= self.cfg.min_margin)

        if not passes:
            # fail window
            self._fail_streak += 1
            self._winner_idx = None
            self._win_streak = 0

            if self._fail_streak >= self.cfg.no_control_wins:
                # commit NONE once
                self._fail_streak = 0
                return DecisionInfo(
                    "SET_NONE", None, best_idx, best_score, second_score, margin
                )

            return DecisionInfo(
                "HOLD", None, best_idx, best_score, second_score, margin
            )

        # pass window
        self._fail_streak = 0

        if self._winner_idx == best_idx:
            self._win_streak += 1
        else:
            self._winner_idx = best_idx
            self._win_streak = 1

        if self._win_streak >= self.cfg.consecutive_wins:
            # commit IDX once
            self._win_streak = 0
            return DecisionInfo(
                "SET_IDX", best_idx, best_idx, best_score, second_score, margin
            )

        return DecisionInfo("HOLD", None, best_idx, best_score, second_score, margin)
