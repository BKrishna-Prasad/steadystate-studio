import pytest
from neurovision.communication.controller import BCIController
from neurovision.communication.transports import parse_command
from neurovision.config import Settings


class Capture:
    def __init__(self):
        self.messages = []

    def push_sample(self, sample):
        self.messages.append(sample[0])

    def send_message(self, address, code):
        self.messages.append((address, code))


def test_preview_add_remove_restart_and_back():
    markers, osc = Capture(), Capture()
    controller = BCIController(markers, Settings(), osc)
    for idx in (0, 1, 0):
        controller.handle_selection(idx)
    assert ("D", "2") in controller.active_tracks
    assert osc.messages == [("/loop/only", 2)]
    for idx in (0, 1, 1):
        controller.handle_selection(idx)
    assert not controller.active_tracks
    assert osc.messages[-1] == ("/loop/only", 22)
    for idx in (1, 2, 2):
        controller.handle_selection(idx)
    assert osc.messages[-2:] == [("/loop/only", 110), ("/loop/only", 6969)]
    controller.handle_selection(0)
    controller.handle_selection(0)
    controller.go_back()
    assert controller.state == 1
    assert osc.messages[-1] == ("/loop/only", 11)
    assert "action_KILL_P3" in markers.messages


def test_piano_slot_four_osc_codes():
    controller = BCIController(Capture(), Settings(), Capture())
    assert controller.osc_map[("P", "4")] == 12
    assert controller.osc_off_map[("P", "4")] == 1212


def test_wire_format_and_no_control():
    frequencies = Settings().decoder.freqs
    assert parse_command("SSVEP_IDX=1;FREQ=10.0;S=0.9;M=0.5", frequencies) == 1
    assert parse_command("SSVEP_NONE;FREQ=0;REASON=SHUTDOWN", frequencies) is None
    for msg in (
        "SSVEP_IDX=1;FREQ=12",
        "SSVEP_IDX=7;FREQ=8",
        "SSVEP_IDX=0;FREQ=nan",
        "bad",
    ):
        with pytest.raises((ValueError, KeyError)):
            parse_command(msg, frequencies)
