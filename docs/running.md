# Configuration and troubleshooting

We install from the repository with `python -m pip install .`. `python -m neurovision --help` lists the commands. Each command accepts `--config` after its name.

## Configuration

Shared decoder defaults are in `src/neurovision/decoding/parameters.py`; other settings are in `src/neurovision/config.py`. JSON files override only the values needed for a setup.

```sh
python -m neurovision config --out configs/local.json
python -m neurovision demo --config configs/local.json
```

The sections are `decoder`, `lsl`, `music`, `stimulus` and `synthetic`. Unknown keys, invalid bands and inconsistent channel selections are rejected. The sample rate must keep the notch, filter edges and reference harmonics below Nyquist. The decoder can use a different frequency set, while the music screen requires exactly four targets. The instrument order is Drums/Piano/Bass/Extra.

The synthetic generator uses 1–40 Hz background noise and a 50 Hz line-noise component. Changing the decoder notch does not change the injected line frequency. Line noise is off in the default demo.

For an outlet with a leading counter followed by eight EEG channels, a config would include:

```json
{
  "lsl": {
    "eeg_name": "YOUR_EEG_STREAM",
    "expected_channels": 8,
    "eeg_channels": [1, 2, 3, 4, 5, 6, 7, 8]
  }
}
```

Verify the channel layout in the acquisition software. CAR uses only the selected EEG channels. The outlet must advertise its actual nominal sample rate and stream type EEG. Pairing, calibration, electrode contact and unit conversion are handled outside the decoder.

## LSL connections

```sh
python -m pip install ".[lsl]"
python -m neurovision inspect-streams
```

See the [pylsl documentation](https://github.com/labstreaminglayer/pylsl#installation) for native `liblsl` installation and discovery. `PYLSL_LIB` can identify the library path. If discovery fails, check that the outlet is running, the stream name matches exactly, and local firewall/network settings permit discovery. Close duplicate outlets or set `lsl.eeg_source_id`.

The streamer waits up to `connect_timeout_sec` for a consumer. Start the decoder within that interval or increase the timeout. The decoder stops after `data_timeout_sec` without samples. For a bounded run use `--duration`; for continued replay use `stream --repeat`. Replays pause briefly between passes, resetting window and decision history. `demo --lsl` manages the recording length automatically.

Per-window JSON contains scores, best index, margin, state, change flag and relative sample/time offsets. LSL timestamps detect discontinuities. The tool does not align trials from stimulus markers or measure stimulus-to-audio latency. Connect `listen` before a transition to capture it.

## PsychoPy

Follow [PsychoPy's installation guidance](https://psychopy.org/download), then install this repository in the same interpreter. In a compatible environment:

```sh
python -m pip install ".[stimuli]"
python -m neurovision stimuli --keyboard-only
```

PsychoPy's graphics and audio dependencies have their own Python/platform requirements. It is optional for the core decoder and synthetic demo.

For BCI control, start the decoder before the interface. Command discovery runs in a background thread; keyboard controls remain available without a command stream. If the decoder disconnects, restart the interface after restarting the decoder. Queued commands expire so old selections are not applied after re-enabling flicker.

Check physical stimulus timing on the actual monitor. A measured refresh rate and dropped-frame diagnostic do not establish correct luminance timing.

## Sonic Pi

Open and run `sonic_pi/neurovision_killswitch.rb`, then enable incoming OSC. The [Sonic Pi OSC tutorial](https://sonic-pi.net/tutorial-12.html) covers the local port and settings for messages from other computers.

```sh
python -m pip install ".[osc]"
python -m neurovision music-demo --indices 0,1,0 --send-osc
```

Set `music.osc_host`, `music.osc_port` and `music.osc_address` for a different endpoint. Without `--send-osc`, the tool prints the messages for inspection. UDP delivery has no acknowledgement. See [music controls](music.md) for loop aliases and controller behavior.
