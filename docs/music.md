# Music controls and OSC mapping

We choose an instrument, then a loop. Entering the action screen starts a pending preview. Add keeps it; Remove sends its off code; Restart sends `6969` and clears the controller's track state.

| Family | Loop 1 on/off | Loop 2 on/off | Loop 3 on/off | Loop 4 on/off |
|---|---|---|---|---|
| Drums | 1 / 11 | 2 / 22 | 3 / 33 | 4 / 44 |
| Bass | 5 / 55 | 6 / 66 | 7 / 77 | 8 / 88 |
| Piano | 9 / 99 | 10 / 1010 | 110 / 1111 | 12 / 1212 |
| Extra | 13 / 1313 | 14 / 1414 | 15 / 1515 | 16 / 1616 |

We send integer OSC messages to `/loop/only`. Piano Loop 3 uses `110`; code `11` already stops Drums Loop 1. The Sonic Pi engine runs at 100 BPM with predefined musical patterns.

## Current behavior to consider when adapting the engine

- Piano Loop 4 shares the `p3` state and playing loop with Piano Loop 3. The controller tracks P3 and P4 separately, so its state can diverge from the audio engine. Use Piano Loop 3 unless you add a separate P4 loop and update the routing.
- The second snare in D3 and the hi-hats in D4 read `d1` for amplitude. Their behavior therefore depends partly on Drums Loop 1.
- The on-screen Back action removes the selected track before returning to loop selection. Backspace cancels a newly previewed track but keeps a previously active one.
- No-control does not stop confirmed music layers. Escape closes the interface without a global audio reset. Use Restart or Sonic Pi's Stop control to silence all layers.
- `active_tracks` stores the controller's intended state. UDP provides no acknowledgement, and restarting Sonic Pi separately can invalidate that state.

These behaviors are part of the current implementation. Changing them requires updating the controller and music engine together.

## Try the mapping

```sh
python -m neurovision music-demo --indices 0,1,0
```

This selects Drums, previews Loop 2 and adds it, printing the OSC messages. For audio, run `sonic_pi/neurovision_killswitch.rb` in Sonic Pi, install the OSC extra and add `--send-osc`.
