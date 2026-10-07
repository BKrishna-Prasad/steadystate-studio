"""Optional LSL transport with explicit stream and channel checks."""

import time
import uuid

import numpy as np


def require_lsl():
    try:
        import pylsl
    except (ImportError, RuntimeError, OSError) as error:
        raise RuntimeError(
            "LSL unavailable. Install with: python -m pip install '.[lsl]'. If liblsl is missing, see docs/running.md."
        ) from error
    return pylsl


def resolve_named(name, timeout, source_id=""):
    lsl = require_lsl()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        matches = [
            s
            for s in lsl.resolve_streams(
                wait_time=min(1.0, max(0.01, deadline - time.monotonic()))
            )
            if s.name() == name and (not source_id or s.source_id() == source_id)
        ]
        if len(matches) > 1:
            raise RuntimeError(
                f"Multiple LSL streams named {name!r}; close duplicates or set eeg_source_id"
            )
        if matches:
            return matches[0]
    raise RuntimeError(f"LSL stream {name!r} not found within {timeout:g}s")


def select_channels(info, settings):
    cfg = settings.lsl
    if info.type().upper() != "EEG":
        raise ValueError(f"Expected EEG stream, got type {info.type()!r}")
    if not np.isclose(info.nominal_srate(), settings.decoder.fs, rtol=0, atol=1e-6):
        raise ValueError(
            f"Stream sample rate {info.nominal_srate()} differs from config {settings.decoder.fs}; set fs explicitly"
        )
    count = info.channel_count()
    if cfg.eeg_channels:
        indices = cfg.eeg_channels
        if max(indices) >= count:
            raise ValueError("Configured EEG indices exceed incoming stream channels")
    elif count == cfg.expected_channels:
        indices = tuple(range(count))
    else:
        raise ValueError(
            f"Stream has {count} channels. Configure eeg_channels explicitly to select {cfg.expected_channels} EEG channels"
        )
    return indices


def connect_eeg(settings, info=None):
    lsl = require_lsl()
    info = info or resolve_named(
        settings.lsl.eeg_name,
        settings.lsl.connect_timeout_sec,
        settings.lsl.eeg_source_id,
    )
    indices = select_channels(info, settings)
    inlet = lsl.StreamInlet(info, max_buflen=30, processing_flags=lsl.proc_clocksync)
    inlet.open_stream(timeout=settings.lsl.connect_timeout_sec)
    return inlet, indices


def synthetic_outlet(recording, name=None):
    lsl = require_lsl()
    info = lsl.StreamInfo(
        name or recording.settings.lsl.eeg_name,
        "EEG",
        recording.samples.shape[1],
        recording.settings.decoder.fs,
        "float32",
        f"neurovision_synthetic_{uuid.uuid4().hex}",
    )
    info.desc().append_child_value("data_kind", "synthetic_demonstration")
    info.desc().append_child_value("generator", "neurovision.synthetic.generator.make_segment")
    channels = info.desc().append_child("channels")
    for i in range(recording.samples.shape[1]):
        channel = channels.append_child("channel")
        channel.append_child_value("label", f"EEG {i + 1}")
        channel.append_child_value("unit", "arbitrary")
    return lsl.StreamOutlet(info)


def publish_recording(outlet, recording, wait_timeout=15.0, stop=None):
    """Replay once at nominal sample rate with per-sample LSL timestamps."""
    lsl = require_lsl()
    if not outlet.wait_for_consumers(wait_timeout):
        raise RuntimeError(
            "No EEG consumer connected before replay timeout; start the decoder"
        )
    fs = recording.settings.decoder.fs
    chunk_size = max(1, round(0.02 * fs))
    base_lsl, base_wall = lsl.local_clock(), time.monotonic()
    for start in range(0, len(recording.samples), chunk_size):
        if stop is not None and stop.is_set():
            return
        end = min(start + chunk_size, len(recording.samples))
        deadline = base_wall + (end - 1) / fs
        remaining = deadline - time.monotonic()
        if remaining > 0:
            if stop is not None:
                if stop.wait(remaining):
                    return
            else:
                time.sleep(remaining)
        timestamps = (base_lsl + np.arange(start, end) / fs).tolist()
        outlet.push_chunk(
            recording.samples[start:end].astype(np.float32).tolist(), timestamps
        )
    # Keep the outlet alive briefly so the last queued packet can reach inlets.
    if stop is not None:
        stop.wait(0.3)
    else:
        time.sleep(0.3)


def timed_blocks(samples, timestamps, last_timestamp, gap_tolerance):
    """Split at discontinuities; the consumer can reset before each new block."""
    timestamps = np.asarray(timestamps, dtype=float)
    if timestamps.shape != (len(samples),) or not np.isfinite(timestamps).all():
        raise ValueError("Invalid EEG timestamps")
    if not len(samples):
        return []
    previous = np.r_[
        timestamps[0] if last_timestamp is None else last_timestamp, timestamps[:-1]
    ]
    delta = timestamps - previous
    discontinuity = (delta <= 0) | (delta > gap_tolerance)
    if last_timestamp is None:
        discontinuity[0] = False
    boundaries = sorted(set([0, *np.flatnonzero(discontinuity).tolist(), len(samples)]))
    return [
        (samples[a:b], bool(discontinuity[a]))
        for a, b in zip(boundaries[:-1], boundaries[1:])
    ]
