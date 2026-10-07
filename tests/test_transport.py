import uuid

import numpy as np
import pytest
from neurovision.acquisition.lsl import select_channels, timed_blocks
from neurovision.config import Settings


class Info:
    def __init__(self, n=8, fs=250):
        self.n, self.fs = n, fs

    def type(self):
        return "EEG"

    def channel_count(self):
        return self.n

    def nominal_srate(self):
        return self.fs


def test_explicit_channels_and_rate():
    settings = Settings()
    assert select_channels(Info(), settings) == tuple(range(8))
    with pytest.raises(ValueError):
        select_channels(Info(9), settings)
    settings.lsl.eeg_channels = tuple(range(1, 9))
    assert select_channels(Info(9), settings) == tuple(range(1, 9))
    with pytest.raises(ValueError):
        select_channels(Info(9, 500), settings)


def test_timestamp_gaps_split_windows():
    samples = np.zeros((4, 8))
    blocks = timed_blocks(samples, [1, 1.004, 2, 2.004], None, 0.1)
    assert [(len(x), reset) for x, reset in blocks] == [(2, False), (2, True)]
    assert timed_blocks(samples[:1], [0.5], 1, 0.1)[0][1]


@pytest.mark.integration
def test_lsl_eeg_and_command_round_trip():
    lsl = pytest.importorskip("pylsl")
    from neurovision.acquisition.lsl import resolve_named
    from neurovision.communication.transports import CommandOutlet

    settings = Settings()
    settings.decoder.cmd_stream_name = "test_cmd_" + uuid.uuid4().hex
    command = CommandOutlet(settings)
    info = resolve_named(
        settings.decoder.cmd_stream_name, 5, settings.decoder.cmd_source_id
    )
    inlet = lsl.StreamInlet(info)
    inlet.open_stream(timeout=3)
    assert command.outlet.wait_for_consumers(3)
    message = "SSVEP_IDX=2;FREQ=12.0;S=0.8;M=0.5"
    command.send(message)
    sample, timestamp = inlet.pull_sample(timeout=3)
    assert sample == [message] and timestamp > 0
    inlet.close_stream()
    name = "test_eeg_" + uuid.uuid4().hex
    outlet = lsl.StreamOutlet(lsl.StreamInfo(name, "EEG", 8, 250, "float32", name))
    inlet = lsl.StreamInlet(resolve_named(name, 5))
    inlet.open_stream(timeout=3)
    assert outlet.wait_for_consumers(3)
    x = np.arange(80, dtype=np.float32).reshape(10, 8)
    stamps = (lsl.local_clock() + np.arange(10) / 250).tolist()
    outlet.push_chunk(x.tolist(), stamps)
    received, times = inlet.pull_chunk(timeout=3, max_samples=10)
    np.testing.assert_array_equal(received, x)
    np.testing.assert_allclose(times, stamps, rtol=0, atol=1e-6)
    inlet.close_stream()


@pytest.mark.integration
def test_real_udp_osc_packet_without_sonic_pi():
    pytest.importorskip("pythonosc")
    import socket

    from neurovision.communication.transports import osc_client
    from pythonosc.osc_packet import OscPacket

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
        receiver.bind(("127.0.0.1", 0))
        receiver.settimeout(3)
        settings = Settings()
        settings.music.osc_port = receiver.getsockname()[1]
        osc_client(settings, True).send_message(settings.music.osc_address, 110)
        packet = OscPacket(receiver.recvfrom(4096)[0])
        message = packet.messages[0].message
        assert message.address == "/loop/only" and list(message.params) == [110]
