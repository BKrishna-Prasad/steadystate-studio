"""Synthetic schedules, saved recordings and frequency recovery checks."""

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..config import settings_from_dict
from .generator import make_segment


@dataclass
class Recording:
    samples: np.ndarray
    injected_hz: np.ndarray
    settings: object
    segments: list[dict]
    seed: int

    def save(self, path):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        metadata = {
            "kind": "synthetic_demonstration",
            "generator": "neurovision.synthetic.generator.make_segment",
            "seed": self.seed,
            "settings": self.settings.to_dict(),
            "segments": self.segments,
            "units": "arbitrary; not a calibrated physiological model",
        }
        with target.open("wb") as handle:
            np.savez_compressed(
                handle,
                samples=self.samples,
                injected_hz=self.injected_hz,
                metadata=json.dumps(metadata),
            )


def generate(settings, seed=None, target_sec=6.0, rest_sec=4.0, schedule=None):
    """Generate synthetic signals with an explicit, labelled block schedule."""
    settings.validate()
    if target_sec <= 0 or rest_sec <= 0:
        raise ValueError("Target and rest durations must be positive")
    cfg = settings.decoder
    n_ch = settings.lsl.expected_channels
    seed = settings.synthetic.seed if seed is None else seed
    rng = np.random.default_rng(seed)
    samples, labels, segments = [], [], []
    offset = 0
    if schedule is None:
        sequence = [(0.0, rest_sec)]
        for freq in cfg.freqs:
            sequence.extend([(freq, target_sec), (0.0, rest_sec)])
    else:
        sequence = []
        for item in schedule.split(","):
            label, duration = item.strip().split(":", 1)
            freq = 0.0 if label.lower() in ("off", "none", "0") else float(label)
            duration = float(duration)
            if freq != 0 and freq not in cfg.freqs:
                raise ValueError(
                    "Schedule frequency must be a configured decoder target"
                )
            if not np.isfinite(duration) or duration <= 0:
                raise ValueError("Schedule duration must be positive and finite")
            sequence.append((freq, duration))
    for freq, duration in sequence:
        n = int(duration * cfg.fs)
        if n < 64:
            raise ValueError(
                "Generator blocks must contain at least 64 samples for filtering"
            )
        synth = settings.synthetic
        x = make_segment(
            cfg.fs,
            duration,
            n_ch,
            freq or None,
            synth.ssvep_amp,
            cfg.harmonics,
            synth.noise_amp,
            synth.line_amp,
            synth.drift_amp,
            rng,
        )
        samples.append(x)
        labels.append(np.full(n, freq, dtype=np.float32))
        segments.append(
            {"start_sample": offset, "end_sample": offset + n, "injected_hz": freq}
        )
        offset += n
    return Recording(
        np.concatenate(samples), np.concatenate(labels), settings, segments, seed
    )


def load_csv(path, settings):
    """Read labelled synthetic CSV data; keep labels out of EEG channels."""
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        names = [f"EEG {i + 1}" for i in range(settings.lsl.expected_channels)]
        if not reader.fieldnames or not set([*names, "TARGET_FREQ", "Sample"]).issubset(
            reader.fieldnames
        ):
            raise ValueError(
                "CSV requires EEG columns, Sample and TARGET_FREQ; use only known synthetic data"
            )
        rows = list(reader)
    samples = np.asarray(
        [[float(row[n]) for n in names] for row in rows], dtype=np.float64
    )
    labels = np.asarray([float(row["TARGET_FREQ"]) for row in rows], dtype=np.float32)
    indices = [int(row["Sample"]) for row in rows]
    if (
        not rows
        or indices != list(range(len(rows)))
        or not np.isfinite(samples).all()
        or not np.isfinite(labels).all()
        or any(f != 0 and f not in settings.decoder.freqs for f in np.unique(labels))
    ):
        raise ValueError("Invalid labelled synthetic CSV")
    boundaries = [0, *(np.flatnonzero(np.diff(labels)) + 1).tolist(), len(labels)]
    segments = [
        {"start_sample": a, "end_sample": b, "injected_hz": float(labels[a])}
        for a, b in zip(boundaries[:-1], boundaries[1:])
    ]
    return Recording(samples, labels, settings, segments, None)


def load_recording(path):
    """Load our synthetic NPZ format without pickle or executable metadata."""
    with np.load(path, allow_pickle=False) as archive:
        samples = np.asarray(archive["samples"], dtype=np.float64)
        labels = np.asarray(archive["injected_hz"], dtype=np.float32)
        metadata = json.loads(str(archive["metadata"].item()))
    if metadata.get("kind") != "synthetic_demonstration":
        raise ValueError("This replay format is reserved for labelled synthetic data")
    settings = settings_from_dict(metadata["settings"])
    if (
        samples.ndim != 2
        or samples.shape[1] != settings.lsl.expected_channels
        or labels.shape != (len(samples),)
        or not np.isfinite(samples).all()
        or not np.isfinite(labels).all()
    ):
        raise ValueError("Invalid synthetic recording dimensions or samples")
    segments = metadata["segments"]
    cursor = 0
    for segment in segments:
        start, end, freq = (
            segment["start_sample"],
            segment["end_sample"],
            segment["injected_hz"],
        )
        if (
            start != cursor
            or not start < end <= len(samples)
            or (freq != 0 and freq not in settings.decoder.freqs)
            or not np.all(labels[start:end] == freq)
        ):
            raise ValueError("Synthetic segment metadata does not match sample labels")
        cursor = end
    if cursor != len(samples):
        raise ValueError("Synthetic segments must cover all samples")
    return Recording(samples, labels, settings, segments, metadata["seed"])


def check_recovery(recording, results):
    """Require the known state at the end of every injected/rest segment."""
    checks = []
    for segment in recording.segments:
        inside = [
            r
            for r in results
            if segment["start_sample"]
            + round(
                recording.settings.decoder.fs * recording.settings.decoder.window_sec
            )
            <= r.end_sample
            <= segment["end_sample"]
        ]
        expected = segment["injected_hz"]
        recovered = bool(inside and inside[-1].frequency_hz == expected)
        checks.append(
            {
                **segment,
                "recovered_at_end": recovered,
                "decoded_hz_at_end": inside[-1].frequency_hz if inside else None,
            }
        )
    return {
        "kind": "synthetic_software_check",
        "seed": recording.seed,
        "passed": all(c["recovered_at_end"] for c in checks),
        "checks": checks,
        "interpretation": "Controlled synthetic software check; not live-EEG accuracy or a benchmark.",
    }
