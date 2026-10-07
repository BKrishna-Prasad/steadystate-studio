"""Shared settings and validation for acquisition, decoding and interfaces."""

import json
import math
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from .decoding.parameters import DecoderConfig


@dataclass
class LSLConfig:
    eeg_name: str = "NeuroVision_Synthetic_EEG"
    eeg_source_id: str = ""
    expected_channels: int = 8
    eeg_channels: tuple[int, ...] = ()
    marker_name: str = "NeuroVision_Paradigm"
    connect_timeout_sec: float = 15.0
    data_timeout_sec: float = 5.0
    gap_tolerance_sec: float = 0.1


@dataclass
class MusicConfig:
    instrument_labels: tuple[str, ...] = ("Drums", "Piano", "Bass", "Extra")
    instrument_codes: tuple[str, ...] = ("D", "P", "B", "E")
    osc_host: str = "127.0.0.1"
    osc_port: int = 4560
    osc_address: str = "/loop/only"


@dataclass
class StimulusConfig:
    screen: int = 0
    fullscreen: bool = False
    selection_cooldown_sec: float = 1.0
    command_max_age_sec: float = 2.0


@dataclass
class SyntheticConfig:
    seed: int = 42
    ssvep_amp: float = 80.0
    noise_amp: float = 2.0
    line_amp: float = 0.0
    drift_amp: float = 0.0


@dataclass
class Settings:
    decoder: DecoderConfig = field(default_factory=DecoderConfig)
    lsl: LSLConfig = field(default_factory=LSLConfig)
    music: MusicConfig = field(default_factory=MusicConfig)
    stimulus: StimulusConfig = field(default_factory=StimulusConfig)
    synthetic: SyntheticConfig = field(default_factory=SyntheticConfig)

    def to_dict(self):
        return asdict(self)

    def validate(self):
        d, stream, m, s = self.decoder, self.lsl, self.music, self.stimulus
        if any(
            isinstance(f, bool)
            or not isinstance(f, (int, float))
            or not math.isfinite(f)
            for f in d.freqs
        ):
            raise ValueError("Target frequencies must be finite numbers")
        if any(
            not isinstance(band, (tuple, list))
            or len(band) != 2
            or any(
                isinstance(edge, bool)
                or not isinstance(edge, (int, float))
                or not math.isfinite(edge)
                for edge in band
            )
            for band in d.fb_bands
        ):
            raise ValueError("Filter bands must contain two finite numeric edges")
        if any(
            isinstance(idx, bool) or not isinstance(idx, int)
            for idx in stream.eeg_channels
        ):
            raise ValueError("EEG indices must be integers")
        if any(
            not isinstance(label, str) or not label.strip()
            for label in m.instrument_labels
        ):
            raise ValueError("Instrument labels must be nonempty strings")
        for obj in (d, stream, m, s, self.synthetic):
            for item in fields(obj):
                value = getattr(obj, item.name)
                if isinstance(value, float) and not math.isfinite(value):
                    raise ValueError(f"{item.name} must be finite")
        if d.fs <= 0 or d.window_sec <= 0 or d.step_sec <= 0:
            raise ValueError("Sample rate, window and step must be positive")
        if round(d.window_sec * d.fs) < 64 or round(d.step_sec * d.fs) < 1:
            raise ValueError(
                "Window must contain at least 64 samples; step at least one"
            )
        if d.step_sec > d.window_sec:
            raise ValueError("Step must not exceed the window")
        if len(d.freqs) < 2 or len(set(d.freqs)) != len(d.freqs):
            raise ValueError("Use at least two distinct target frequencies")
        if d.harmonics < 1 or any(
            f <= 0 or f * d.harmonics >= d.fs / 2 for f in d.freqs
        ):
            raise ValueError("All reference harmonics must be below Nyquist")
        if not 0 < d.notch_hz < d.fs / 2 or d.notch_q <= 0:
            raise ValueError("Notch frequency must be below Nyquist and Q positive")
        bands = (*d.fb_bands, (d.plot_bp_low, d.plot_bp_high))
        if not d.fb_bands or any(not 0 < lo < hi < d.fs / 2 for lo, hi in bands):
            raise ValueError("Filter bands must satisfy 0 < low < high < Nyquist")
        if not 0 <= d.min_score <= 1 or not 0 <= d.min_margin <= 1:
            raise ValueError("Score and margin thresholds must be in [0,1]")
        if d.consecutive_wins < 1 or d.no_control_wins < 1:
            raise ValueError("Decision streak lengths must be positive")
        if d.fb_weight_a < 0 or d.fb_weight_b < 0:
            raise ValueError("Filter-bank weights must be nonnegative")
        if stream.expected_channels < 2:
            raise ValueError("CAR requires at least two EEG channels")
        if stream.eeg_channels and (
            len(stream.eeg_channels) != stream.expected_channels
            or len(set(stream.eeg_channels)) != len(stream.eeg_channels)
            or min(stream.eeg_channels) < 0
        ):
            raise ValueError(
                "eeg_channels must contain one distinct nonnegative index per expected channel"
            )
        if any(
            v <= 0
            for v in (
                stream.connect_timeout_sec,
                stream.data_timeout_sec,
                stream.gap_tolerance_sec,
            )
        ):
            raise ValueError("LSL timeouts and gap tolerance must be positive")
        if len(m.instrument_labels) != 4 or m.instrument_codes != ("D", "P", "B", "E"):
            raise ValueError(
                "The music mapping requires D/P/B/E in that order"
            )
        if (
            not m.osc_host.strip()
            or not 1 <= m.osc_port <= 65535
            or not m.osc_address.startswith("/")
        ):
            raise ValueError("Invalid OSC port or address")
        if s.screen < 0 or s.selection_cooldown_sec < 0 or s.command_max_age_sec <= 0:
            raise ValueError("Invalid stimulus screen, cooldown or command age")
        for name in (
            stream.eeg_name,
            stream.marker_name,
            d.cmd_stream_name,
            d.cmd_stream_type,
            d.cmd_source_id,
        ):
            if not name.strip():
                raise ValueError("Stream names, type and source ID must be nonempty")
        if self.synthetic.seed < 0 or any(
            v < 0
            for v in (
                self.synthetic.ssvep_amp,
                self.synthetic.noise_amp,
                self.synthetic.line_amp,
                self.synthetic.drift_amp,
            )
        ):
            raise ValueError("Synthetic seed and amplitudes must be nonnegative")
        return self


def settings_from_dict(data):
    """Merge a JSON-compatible partial configuration; reject unknown keys."""
    result = Settings()
    if not isinstance(data, dict):
        raise ValueError("Configuration must be a JSON object")
    for section, values in data.items():
        if section not in {f.name for f in fields(result)} or not isinstance(
            values, dict
        ):
            raise ValueError(f"Unknown or invalid config section: {section}")
        obj = getattr(result, section)
        allowed = {f.name for f in fields(obj)}
        for key, value in values.items():
            if key not in allowed:
                raise ValueError(f"Unknown config key: {section}.{key}")
            default = getattr(obj, key)
            if isinstance(default, tuple):
                if not isinstance(value, (list, tuple)):
                    raise ValueError(f"{section}.{key} must be an array")
                value = tuple(tuple(v) if isinstance(v, list) else v for v in value)
            elif isinstance(default, bool):
                if not isinstance(value, bool):
                    raise ValueError(f"{section}.{key} must be boolean")
            elif isinstance(default, int):
                if isinstance(value, bool) or not isinstance(value, int):
                    raise ValueError(f"{section}.{key} must be an integer")
            elif isinstance(default, float):
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError(f"{section}.{key} must be a number")
                value = float(value)
            elif not isinstance(value, str):
                raise ValueError(f"{section}.{key} must be a string")
            setattr(obj, key, value)
    return result.validate()


def load_settings(path=None):
    if path is None:
        return Settings().validate()
    return settings_from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
