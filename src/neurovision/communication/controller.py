"""Instrument, loop and action menus with OSC music commands."""

import logging
from typing import Optional, Set, Tuple


class BCIController:
    def __init__(self, outlet, settings, osc):
        self.settings = settings
        self.menu_instruments = {
            "labels": settings.music.instrument_labels,
            "codes": settings.music.instrument_codes,
        }
        self.menu_loops = {
            "labels": [f"Loop {i}" for i in range(1, 5)],
            "codes": [str(i) for i in range(1, 5)],
        }
        self.menu_actions = {
            "labels": ["Add", "Remove", "Restart", "BACK"],
            "codes": ["ADD", "REM", "KILL", "BACK"],
        }
        self.state = 0  # 0=Instruments, 1=Loops, 2=Actions
        self.outlet = outlet

        self.selected_instrument: Optional[str] = None
        self.selected_instrument_name: str = ""
        self.selected_loop: Optional[str] = None

        # Track management:
        # - active_tracks: confirmed layers currently “kept”
        # - pending_track: the preview started on entering the action menu
        self.active_tracks: Set[Tuple[str, str]] = set()
        self.pending_track: Optional[Tuple[str, str]] = None
        self.pending_was_active: bool = False

        # OSC → Sonic Pi
        self.osc = osc

        self.osc_map = {
            ("D", "1"): 1,
            ("D", "2"): 2,
            ("D", "3"): 3,
            ("D", "4"): 4,
            ("B", "1"): 5,
            ("B", "2"): 6,
            ("B", "3"): 7,
            ("B", "4"): 8,
            ("P", "1"): 9,
            ("P", "2"): 10,
            ("P", "3"): 110,
            ("P", "4"): 12,
            ("E", "1"): 13,
            ("E", "2"): 14,
            ("E", "3"): 15,
            ("E", "4"): 16,
        }

        self.osc_off_map = {
            ("D", "1"): 11,
            ("D", "2"): 22,
            ("D", "3"): 33,
            ("D", "4"): 44,
            ("B", "1"): 55,
            ("B", "2"): 66,
            ("B", "3"): 77,
            ("B", "4"): 88,
            ("P", "1"): 99,
            ("P", "2"): 1010,
            ("P", "3"): 1111,
            ("P", "4"): 1212,
            ("E", "1"): 1313,
            ("E", "2"): 1414,
            ("E", "3"): 1515,
            ("E", "4"): 1616,
        }

    def get_current_labels(self):
        if self.state == 0:
            return self.menu_instruments["labels"]
        elif self.state == 1:
            base = self.menu_loops["labels"]
            return [f"{self.selected_instrument_name}\n{label}" for label in base]
        elif self.state == 2:
            return self.menu_actions["labels"]

    def _send_marker(self, marker: str):
        try:
            self.outlet.push_sample([marker])
        except Exception as error:
            logging.warning("Marker delivery failed: %s", error)

    def _send_osc_loop_only(self, code: int):
        self.osc.send_message(self.settings.music.osc_address, int(code))

    def _start_pending_track(self, key: Tuple[str, str]):
        """Start a loop preview; Add confirms it as an active layer."""
        self.pending_track = key
        self.pending_was_active = key in self.active_tracks

        osc_on = self.osc_map.get(key)
        if osc_on is None:
            logging.warning(f"No OSC mapping for {key} — add it to self.osc_map")
            return
        self._send_osc_loop_only(osc_on)

    def _cancel_pending_track_if_needed(self):
        """Stop an unconfirmed preview when navigating back."""
        if self.pending_track is None:
            return

        if not self.pending_was_active:
            osc_off = self.osc_off_map.get(self.pending_track)
            if osc_off is None:
                logging.warning(
                    f"No OSC OFF mapping for {self.pending_track} — add to self.osc_off_map"
                )
            else:
                self._send_osc_loop_only(osc_off)

        # Clear pending either way
        self.pending_track = None
        self.pending_was_active = False
        self.selected_loop = None

    def _commit_pending_track(self):
        """Keep the pending layer active after Add."""
        if self.pending_track is not None:
            self.active_tracks.add(self.pending_track)
        self.pending_track = None
        self.pending_was_active = False

    def _remove_current_track(self):
        """Stop the selected track and clear its local state."""
        if self.selected_instrument is None or self.selected_loop is None:
            return
        key = (self.selected_instrument, self.selected_loop)

        osc_off = self.osc_off_map.get(key)
        if osc_off is None:
            logging.warning(
                f"No OSC OFF mapping for {key} — add it to self.osc_off_map"
            )
        else:
            self._send_osc_loop_only(osc_off)

        self.active_tracks.discard(key)
        self.pending_track = None
        self.pending_was_active = False
        self.selected_loop = None

    def _kill_all(self):
        """Send a global audio reset and clear the controller state."""
        self._send_osc_loop_only(6969)
        self.active_tracks.clear()
        self.pending_track = None
        self.pending_was_active = False
        self.selected_instrument = None
        self.selected_instrument_name = ""
        self.selected_loop = None

    def go_back(self):
        """Cancel an unconfirmed preview or return to instrument selection."""
        if self.state == 2:
            self._cancel_pending_track_if_needed()
            self.state = 1
            logging.info("Navigated Back (2->1)")
            return

        if self.state == 1:
            self.state = 0
            self.selected_instrument = None
            self.selected_instrument_name = ""
            self.selected_loop = None
            self.pending_track = None
            self.pending_was_active = False
            logging.info("Navigated Back (1->0)")
            return

        # state 0: nothing to do

    def handle_selection(self, index: int, source: str = "BCI"):
        if index not in range(4):
            raise ValueError("Music target index must be 0..3")
        # Instrument selection.
        if self.state == 0:
            code = self.menu_instruments["codes"][index]
            self.selected_instrument = code
            self.selected_instrument_name = self.menu_instruments["labels"][index]
            logging.info(
                f"[{source}] Selected instrument: {self.selected_instrument_name}"
            )
            self._send_marker(f"select_inst_{code}")
            self.state = 1
            return

        # Loop selection starts the preview immediately.
        if self.state == 1:
            loop_code = self.menu_loops["codes"][index]
            self.selected_loop = loop_code
            logging.info(f"[{source}] Selected loop: {loop_code}")
            self._send_marker(f"select_loop_{loop_code}")

            if self.selected_instrument is None:
                logging.warning("No instrument selected, ignoring loop selection.")
                return

            key = (self.selected_instrument, loop_code)
            self._start_pending_track(key)

            self.state = 2
            return

        # Confirm or change the selected loop.
        if self.state == 2:
            action_code = self.menu_actions["codes"][index]
            final_id = f"{self.selected_instrument}{self.selected_loop}"
            self._send_marker(f"action_{action_code}_{final_id}")

            if action_code == "BACK":
                # Stop/cancel the currently playing loop, then go back
                self._remove_current_track()
                self.go_back()
                return

            if action_code == "ADD":
                # Confirm the preview track stays active
                print(f"\n>>> CONFIRMED / ADD [{final_id}] <<<\n")
                self._commit_pending_track()
                self.state = 0
                return

            if action_code == "REM":
                print(f"\n>>> REMOVING TRACK [{final_id}] <<<\n")
                self._remove_current_track()
                self.state = 0
                return

            if action_code == "KILL":
                print("\n>>> RESTART / KILL ALL LAYERS <<<\n")
                self._kill_all()
                self.state = 0
                return
