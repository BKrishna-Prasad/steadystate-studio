"""Real-time decoding with timestamp-gap and shutdown handling."""

import time

import numpy as np

from ..decoding.pipeline import Pipeline
from .lsl import connect_eeg, timed_blocks


def decode_lsl(
    settings,
    on_result,
    command_out=None,
    duration=None,
    sample_limit=None,
    info=None,
    on_gap=None,
):
    inlet, indices = connect_eeg(settings, info)
    pipeline = Pipeline(settings)
    started = last_data = time.monotonic()
    last_timestamp = None
    received = 0
    try:
        while duration is None or time.monotonic() - started < duration:
            chunk, timestamps = inlet.pull_chunk(timeout=0.1, max_samples=256)
            if not chunk:
                if time.monotonic() - last_data > settings.lsl.data_timeout_sec:
                    raise RuntimeError("EEG data timed out; decoder stopped")
                continue
            last_data = time.monotonic()
            samples = np.asarray(chunk, dtype=np.float32)[:, indices]
            if sample_limit is not None:
                count = min(len(samples), sample_limit - received)
                samples, timestamps = samples[:count], timestamps[:count]
            for block, reset in timed_blocks(
                samples, timestamps, last_timestamp, settings.lsl.gap_tolerance_sec
            ):
                if reset:
                    pipeline.reset()
                    if command_out:
                        command_out.send("SSVEP_NONE;FREQ=0;REASON=DATA_GAP")
                    if on_gap:
                        on_gap()
                for result in pipeline.feed(block):
                    on_result(result)
                    message = result.command()
                    if message and command_out:
                        command_out.send(message)
            received += len(samples)
            if len(timestamps):
                last_timestamp = timestamps[-1]
            if sample_limit is not None and received >= sample_limit:
                break
    finally:
        if command_out:
            command_out.send("SSVEP_NONE;FREQ=0;REASON=SHUTDOWN")
        inlet.close_stream()
    return received
