"""Command-line tools for EEG decoding, synthetic replay and music control."""

import argparse
import json
import logging
import math
import sys
from pathlib import Path

from .config import load_settings


def _recording(path, settings, config_path):
    from .synthetic.signals import load_csv, load_recording

    if Path(path).suffix.lower() == ".csv":
        return load_csv(path, settings)
    recording = load_recording(path)
    if config_path:
        if (
            settings.decoder.fs != recording.settings.decoder.fs
            or settings.lsl.expected_channels != recording.samples.shape[1]
        ):
            raise ValueError(
                "Replay config must retain the recording sample rate and channel count"
            )
        if any(
            s["injected_hz"] != 0 and s["injected_hz"] not in settings.decoder.freqs
            for s in recording.segments
        ):
            raise ValueError("Replay config omits an injected frequency")
        recording.settings = settings
    return recording


def make_parser():
    parser = argparse.ArgumentParser(
        prog="neurovision",
        description="SSVEP music interface and controlled synthetic software demos",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in [
        ("demo", "Generate, decode and check a labelled synthetic schedule"),
        ("generate", "Save a labelled synthetic signal schedule"),
        ("replay", "Decode a saved synthetic NPZ or labelled CSV"),
        ("stream", "Replay saved synthetic data through LSL at its sample rate"),
        ("decode", "Decode an external EEG LSL stream"),
        ("listen", "Inspect decoder commands from LSL"),
        ("inspect-streams", "List LSL stream metadata"),
        ("stimuli", "Launch the optional PsychoPy music interface"),
        ("music-demo", "Inspect music menu commands without a display"),
        ("config", "Print or save the full default configuration"),
    ]:
        p = commands.add_parser(name, help=help_text)
        p.add_argument("--config", help="Partial JSON configuration")
        if name in ("demo", "generate"):
            p.add_argument("--seed", type=int)
            p.add_argument(
                "--schedule", help='Explicit schedule, e.g. "off:4,15:6,off:4"'
            )
        if name in ("demo", "replay"):
            p.add_argument("--output", default="demo-output")
            p.add_argument(
                "--lsl",
                action="store_true",
                help="Use real-time local LSL transport; needs [lsl]",
            )
            p.add_argument(
                "--plot",
                action="store_true",
                help="Save a labelled inspection figure; needs [plot]",
            )
        if name == "generate":
            p.add_argument("--out", default="demo-output/synthetic.npz")
        if name in ("replay", "stream"):
            p.add_argument("file")
        if name == "stream":
            p.add_argument("--repeat", action="store_true")
        if name in ("decode", "listen"):
            p.add_argument(
                "--duration",
                type=float,
                help="Stop after this many seconds of connected operation",
            )
        if name == "decode":
            p.add_argument("--eeg-name", help="Override the configured EEG stream name")
            p.add_argument(
                "--no-cmd",
                action="store_true",
                help="Inspect only; do not publish command stream",
            )
            p.add_argument("--output", help="Save JSON lines of scores and decisions")
        if name in ("stimuli", "music-demo"):
            p.add_argument(
                "--send-osc",
                action="store_true",
                help="Send real OSC instead of printing a dry run",
            )
        if name == "stimuli":
            p.add_argument("--keyboard-only", action="store_true")
            p.add_argument("--fullscreen", action="store_true")
        if name == "music-demo":
            p.add_argument(
                "--indices",
                default="0,1,0",
                help="Corner selections; default previews and confirms Drums Loop 2",
            )
        if name == "config":
            p.add_argument("--out")
    return parser


def main(argv=None):
    args = make_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        settings = load_settings(args.config)
        if getattr(args, "duration", None) is not None and (
            args.duration <= 0 or not math.isfinite(args.duration)
        ):
            raise ValueError("duration must be positive and finite")
        if args.command == "config":
            content = json.dumps(settings.to_dict(), indent=2) + "\n"
            if args.out:
                path = Path(args.out)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            else:
                print(content, end="")
        elif args.command in ("demo", "generate", "replay"):
            from .synthetic.signals import generate

            if args.command == "replay":
                recording = _recording(args.file, settings, args.config)
            else:
                recording = generate(settings, seed=args.seed, schedule=args.schedule)
            if args.command == "generate":
                recording.save(args.out)
                print(f"Saved labelled synthetic data: {args.out}")
            else:
                from .synthetic.demo import run

                report, results = run(recording, args.output, args.lsl)
                if args.plot:
                    from .synthetic.plot import plot_recording

                    plot_recording(
                        recording,
                        results,
                        Path(args.output) / "synthetic-inspection.png",
                    )
                for segment in report["checks"]:
                    print(
                        f"Injected {segment['injected_hz']:g} Hz -> end-of-block state {segment['decoded_hz_at_end']} Hz; {'PASS' if segment['recovered_at_end'] else 'FAIL'}"
                    )
                print(
                    f"Synthetic software check: {'PASS' if report['passed'] else 'FAIL'} ({report['transport']}). Files: {args.output}"
                )
                print(report["interpretation"])
                return 0 if report["passed"] else 1
        elif args.command == "stream":
            from .acquisition.lsl import publish_recording, synthetic_outlet

            recording = _recording(args.file, settings, args.config)
            outlet = synthetic_outlet(recording)
            print(
                f"Synthetic EEG outlet {recording.settings.lsl.eeg_name!r}; waiting for decoder",
                flush=True,
            )
            while True:
                publish_recording(
                    outlet, recording, recording.settings.lsl.connect_timeout_sec
                )
                if not args.repeat:
                    break
        elif args.command == "decode":
            from .acquisition.runtime import decode_lsl
            from .communication.transports import CommandOutlet

            if args.eeg_name:
                settings.lsl.eeg_name = args.eeg_name
            settings.validate()
            command_out = None if args.no_cmd else CommandOutlet(settings)
            handle = None
            if args.output:
                path = Path(args.output)
                path.parent.mkdir(parents=True, exist_ok=True)
                handle = path.open("w", encoding="utf-8")

            def write(result):
                line = json.dumps(result.to_dict(), allow_nan=False)
                print(line, flush=True)
                if handle:
                    handle.write(line + "\n")
                    handle.flush()

            def gap():
                print(
                    json.dumps(
                        {
                            "kind": "data_gap",
                            "action": "reset_window_and_decision_state",
                        }
                    ),
                    flush=True,
                )

            try:
                print(f"Connecting to {settings.lsl.eeg_name!r}", file=sys.stderr)
                decode_lsl(
                    settings, write, command_out, duration=args.duration, on_gap=gap
                )
            finally:
                if handle:
                    handle.close()
        elif args.command == "inspect-streams":
            from .acquisition.lsl import require_lsl

            for info in require_lsl().resolve_streams(wait_time=2):
                print(
                    json.dumps(
                        {
                            "name": info.name(),
                            "type": info.type(),
                            "source_id": info.source_id(),
                            "channels": info.channel_count(),
                            "nominal_srate": info.nominal_srate(),
                        }
                    )
                )
        elif args.command == "listen":
            import time

            from .acquisition.lsl import require_lsl, resolve_named

            lsl = require_lsl()
            info = resolve_named(
                settings.decoder.cmd_stream_name,
                settings.lsl.connect_timeout_sec,
                settings.decoder.cmd_source_id,
            )
            inlet = lsl.StreamInlet(info, processing_flags=lsl.proc_clocksync)
            started = time.monotonic()
            try:
                while (
                    args.duration is None or time.monotonic() - started < args.duration
                ):
                    sample, stamp = inlet.pull_sample(timeout=0.2)
                    if sample:
                        print(
                            json.dumps({"lsl_timestamp": stamp, "command": sample[0]}),
                            flush=True,
                        )
            finally:
                inlet.close_stream()
        elif args.command == "stimuli":
            from .stimuli.interface import run_interface

            if args.fullscreen:
                settings.stimulus.fullscreen = True
            run_interface(settings, args.send_osc, args.keyboard_only)
        elif args.command == "music-demo":
            from .communication.controller import BCIController
            from .communication.transports import osc_client

            class ConsoleMarkers:
                def push_sample(self, sample):
                    print(json.dumps({"kind": "menu_marker_demo", "marker": sample[0]}))

            controller = BCIController(
                ConsoleMarkers(), settings, osc_client(settings, args.send_osc)
            )
            for idx in [int(i) for i in args.indices.split(",")]:
                controller.handle_selection(idx, source="DEMO")
            print(
                "Music controller demonstration; selections are scripted, not decoded EEG."
            )
        return 0
    except KeyboardInterrupt:
        print("Stopped.", file=sys.stderr)
        return 130
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
