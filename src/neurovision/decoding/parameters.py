"""Default signal-processing and decision parameters."""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class DecoderConfig:
    fs: float = 250.0
    freqs: Tuple[float, ...] = (8.0, 10.0, 12.0, 15.0)
    harmonics: int = 3

    # Real-time windowing
    window_sec: float = 1.5
    step_sec: float = 0.25

    # Preprocessing
    notch_hz: float = 50.0
    notch_q: float = 30.0

    # For plotting
    plot_bp_low: float = 1.0
    plot_bp_high: float = 40.0

    # Filter-bank CCA bands
    fb_bands: Tuple[Tuple[float, float], ...] = (
        (6.0, 15.0),
        (15.0, 25.0),
        (25.0, 40.0),
    )
    fb_weight_a: float = 1.25
    fb_weight_b: float = 0.25

    # Decision logic (scores are normalized to 0..1)
    min_score: float = 0.45
    min_margin: float = 0.06
    consecutive_wins: int = 4  # require same winner N times to switch to a target
    no_control_wins: int = 6  # require N consecutive FAIL windows to switch to NONE

    # Output stream
    cmd_stream_name: str = "unicorn_cmd"
    cmd_stream_type: str = "Markers"
    cmd_source_id: str = "ssvep_decoder"
