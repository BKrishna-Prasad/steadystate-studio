"""A local synthetic EEG -> LSL decoder -> menu -> UDP command check."""

import socket
import threading
import time
import uuid

import pytest
from neurovision.config import Settings


@pytest.mark.integration
def test_synthetic_decisions_drive_music_controller_over_udp():
    lsl = pytest.importorskip("pylsl")
    pytest.importorskip("pythonosc")
    from neurovision.acquisition.lsl import (
        publish_recording,
        resolve_named,
        synthetic_outlet,
    )
    from neurovision.acquisition.runtime import decode_lsl
    from neurovision.communication.controller import BCIController
    from neurovision.communication.transports import (
        CommandOutlet,
        osc_client,
        parse_command,
    )
    from neurovision.synthetic.signals import generate
    from pythonosc.osc_packet import OscPacket

    settings = Settings()
    settings.decoder.cmd_stream_name = "e2e_command_" + uuid.uuid4().hex
    recording = generate(settings, schedule="off:2,8:4,10:4,12:4,off:4")
    outlet = synthetic_outlet(recording, "e2e_eeg_" + uuid.uuid4().hex)
    descriptor = outlet.get_info()
    eeg_info = resolve_named(descriptor.name(), 5, descriptor.source_id())
    command = CommandOutlet(settings)
    inlet = lsl.StreamInlet(
        resolve_named(
            settings.decoder.cmd_stream_name, 5, settings.decoder.cmd_source_id
        )
    )
    inlet.open_stream(timeout=3)
    assert command.outlet.wait_for_consumers(3)
    errors = []
    stop = threading.Event()

    def publisher():
        try:
            publish_recording(outlet, recording, stop=stop)
        except Exception as error:
            errors.append(error)

    def decoder():
        try:
            decode_lsl(
                settings,
                lambda _: None,
                command,
                sample_limit=len(recording.samples),
                info=eeg_info,
            )
        except Exception as error:
            errors.append(error)

    class Markers:
        def push_sample(self, sample):
            pass

    threads = [
        threading.Thread(target=publisher, daemon=True),
        threading.Thread(target=decoder, daemon=True),
    ]
    selections = []
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
        receiver.bind(("127.0.0.1", 0))
        receiver.settimeout(3)
        settings.music.osc_port = receiver.getsockname()[1]
        controller = BCIController(Markers(), settings, osc_client(settings, True))
        for thread in threads:
            thread.start()
        deadline = time.monotonic() + 25
        try:
            while time.monotonic() < deadline and any(t.is_alive() for t in threads):
                sample, _ = inlet.pull_sample(timeout=0.1)
                if sample:
                    idx = parse_command(sample[0], settings.decoder.freqs)
                    if idx is not None:
                        selections.append(idx)
                        controller.handle_selection(idx)
            assert not errors
            assert selections == [0, 1, 2]
            messages = [
                OscPacket(receiver.recvfrom(4096)[0]).messages[0].message
                for _ in range(2)
            ]
            assert [(m.address, list(m.params)) for m in messages] == [
                ("/loop/only", [2]),
                ("/loop/only", [6969]),
            ]
        finally:
            stop.set()
            for thread in threads:
                thread.join(timeout=6)
            inlet.close_stream()
