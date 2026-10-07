"""Optional command and OSC transports; dry runs need no audio software."""

import json
import math
import re

from ..acquisition.lsl import require_lsl


class CommandOutlet:
    def __init__(self, settings):
        lsl = require_lsl()
        cfg = settings.decoder
        self.outlet = lsl.StreamOutlet(
            lsl.StreamInfo(
                cfg.cmd_stream_name,
                cfg.cmd_stream_type,
                1,
                0,
                "string",
                cfg.cmd_source_id,
            )
        )

    def send(self, message):
        self.outlet.push_sample([message])


class MarkerOutlet:
    def __init__(self, settings):
        lsl = require_lsl()
        self.outlet = lsl.StreamOutlet(
            lsl.StreamInfo(
                settings.lsl.marker_name, "Markers", 1, 0, "string", "nv_controller"
            )
        )

    def push_sample(self, sample):
        self.outlet.push_sample(sample)


class DryRunOSC:
    def __init__(self, write=print):
        self.write = write

    def send_message(self, address, value):
        self.write(
            json.dumps({"kind": "osc_dry_run", "address": address, "value": value})
        )


def osc_client(settings, enabled=False):
    if not enabled:
        return DryRunOSC()
    try:
        from pythonosc.udp_client import SimpleUDPClient
    except ImportError as error:
        raise RuntimeError(
            "Install OSC support: python -m pip install '.[osc]'"
        ) from error
    return SimpleUDPClient(settings.music.osc_host, settings.music.osc_port)


def parse_command(message, frequencies):
    """Parse decoder commands; reject inconsistent index/frequency pairs."""
    if isinstance(message, bytes):
        message = message.decode("utf-8")
    parts = str(message).strip().split(";")
    if len(parts) < 2:
        raise ValueError("Malformed decoder command")
    fields = dict(part.split("=", 1) for part in parts[1:])
    frequency = float(fields["FREQ"])
    if parts[0] == "SSVEP_NONE" and frequency == 0:
        return None
    match = re.fullmatch(r"SSVEP_IDX=(\d+)", parts[0])
    if not match:
        raise ValueError("Unknown decoder command")
    idx = int(match.group(1))
    if (
        not math.isfinite(frequency)
        or not 0 <= idx < len(frequencies)
        or not math.isclose(frequency, frequencies[idx], abs_tol=1e-6)
    ):
        raise ValueError("Decoder command index/frequency disagrees with config")
    return idx
