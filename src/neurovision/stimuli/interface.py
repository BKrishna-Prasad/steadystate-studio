"""Four-target PsychoPy stimulus and music selection interface."""

import logging
import threading
import time

import numpy as np

from ..acquisition.lsl import require_lsl, resolve_named
from ..communication.controller import BCIController
from ..communication.transports import MarkerOutlet, osc_client, parse_command


class CommandListener:
    """Resolve away from the drawing loop and drain to the newest fresh command."""

    def __init__(self, settings):
        self.settings = settings
        self.inlet = None
        self.error = None
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._connect, daemon=True)
        self.thread.start()

    def _connect(self):
        lsl = require_lsl()
        while not self.stop.is_set() and self.inlet is None:
            try:
                info = resolve_named(
                    self.settings.decoder.cmd_stream_name,
                    1,
                    self.settings.decoder.cmd_source_id,
                )
                if (
                    info.channel_count() != 1
                    or info.nominal_srate() != 0
                    or info.channel_format() != lsl.cf_string
                ):
                    raise ValueError(
                        "Decoder command stream must be one irregular string channel"
                    )
                inlet = lsl.StreamInlet(info, processing_flags=lsl.proc_clocksync)
                inlet.open_stream(timeout=1)
                if self.stop.is_set():
                    inlet.close_stream()
                    return
                self.inlet = inlet
            except (RuntimeError, ValueError) as error:
                self.error = str(error)
                self.stop.wait(1)

    def poll(self):
        if self.inlet is None:
            return None
        lsl = require_lsl()
        latest = None
        try:
            for _ in range(32):
                sample, stamp = self.inlet.pull_sample(timeout=0)
                if sample is None:
                    break
                age = lsl.local_clock() - stamp
                if age < -0.5 or age > self.settings.stimulus.command_max_age_sec:
                    continue
                try:
                    latest = parse_command(sample[0], self.settings.decoder.freqs)
                except (ValueError, KeyError, UnicodeError) as error:
                    logging.warning("Rejected decoder command: %s", error)
        except lsl.LostError:
            logging.warning(
                "Decoder command stream lost; restart the interface after restarting the decoder"
            )
            self.inlet.close_stream()
            self.inlet = None
        return latest

    def close(self):
        self.stop.set()
        self.thread.join(timeout=3)
        if self.inlet:
            self.inlet.close_stream()


def run_interface(settings, send_osc=False, keyboard_only=False):
    try:
        from psychopy import core, event, visual
    except ImportError as error:
        raise RuntimeError(
            "PsychoPy is optional. See docs/running.md for installation in a compatible Python environment."
        ) from error
    if len(settings.decoder.freqs) != 4:
        raise ValueError("The music interface requires four targets")
    markers = MarkerOutlet(settings)
    controller = BCIController(markers, settings, osc_client(settings, send_osc))
    listener = None if keyboard_only else CommandListener(settings)
    win = None
    try:
        win = visual.Window(
            size=[1200, 800],
            screen=settings.stimulus.screen,
            fullscr=settings.stimulus.fullscreen,
            monitor="testMonitor",
            units="height",
            color=[-1, -1, -1],
            waitBlanking=True,
            useFBO=True,
            checkTiming=True,
        )
        win.recordFrameIntervals = True
        rate = win.getActualFrameRate()
        logging.info(
            "Measured display refresh: %s Hz; monitor timing still needs verification",
            rate,
        )
        ratio = win.size[0] / win.size[1]
        x, y = ratio / 2 - 0.15, 0.35
        positions = [(-x, y), (x, y), (-x, -y), (x, -y)]
        squares = [
            visual.Rect(
                win, width=0.2, height=0.2, pos=p, fillColor="white", lineColor=None
            )
            for p in positions
        ]
        colors = ["#00FFFF", "#00FF00", "#FF00FF", "#FFFF00"]
        labels = [
            visual.TextStim(
                win,
                height=0.03,
                color=colors[i],
                pos=(p[0], p[1] + (-0.2 if p[1] > 0 else 0.2)),
            )
            for i, p in enumerate(positions)
        ]
        fixation = visual.TextStim(win, text="+", height=0.1)
        instructions = visual.TextStim(
            win,
            text="Q/W/A/S: select | Backspace: back\nSpace: start/stop flicker | Esc: exit",
            height=0.025,
            pos=(0, -0.13),
        )
        status = visual.TextStim(win, height=0.022, pos=(0, 0.12))
        clock = core.Clock()
        flashing, start, cooldown = False, 0.0, 0.0
        while True:
            keys = event.getKeys()
            if "escape" in keys:
                break
            if "space" in keys:
                flashing = not flashing
                start = clock.getTime()
                markers.push_sample(["start_flash" if flashing else "stop_flash"])
            if "backspace" in keys:
                controller.go_back()
            candidates = [
                (i, "KEY") for i, k in enumerate(("q", "w", "a", "s")) if k in keys
            ]
            bci = listener.poll() if listener else None
            if flashing and bci is not None:
                candidates.append((bci, "BCI"))
            if candidates and time.monotonic() >= cooldown:
                idx, source = candidates[0]
                controller.handle_selection(idx, source=source)
                cooldown = time.monotonic() + settings.stimulus.selection_cooldown_sec
            current_labels = controller.get_current_labels()
            for i, label in enumerate(labels):
                label.text = f"{current_labels[i]}\n({settings.decoder.freqs[i]:g} Hz)"
                label.draw()
            if flashing:
                t = clock.getTime() - start
                for frequency, square in zip(settings.decoder.freqs, squares):
                    square.opacity = 0.5 * (1 + np.sin(2 * np.pi * frequency * t))
                    square.draw()
            else:
                instructions.draw()
            status.text = (
                "Keyboard"
                if keyboard_only
                else "BCI connected"
                if listener.inlet
                else "Waiting for decoder"
            ) + (" | OSC enabled" if send_osc else " | audio dry run")
            status.draw()
            fixation.draw()
            win.flip()
        markers.push_sample(["stop_flash"])
    finally:
        if listener:
            listener.close()
        if win:
            logging.info(
                "PsychoPy reported %s dropped frames; this is a display diagnostic",
                win.nDroppedFrames,
            )
            win.close()
