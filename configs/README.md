# Configuration examples

We keep shared defaults in the Python configuration and use partial JSON overrides for each setup. Write a full editable config with `python -m neurovision config --out configs/local.json`.

- `unicorn.example.json`: an eight-channel EEG input; verify the stream name and EEG indices before use.
- `csv.example.json`: the 250 Hz sample rate for the included synthetic CSV.
- `noisy_synthetic.example.json`: higher background and line-noise amplitudes for exploring the decoder. This example may fail the demo's recovery check; it is not a physiological model or a benchmark.

Local stream identifiers and device settings belong in `configs/local*.json`, which Git ignores. See [configuration guidance](../docs/running.md).
