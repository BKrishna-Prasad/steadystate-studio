# Synthetic replay example

`ssvep_example.csv` contains eight channels of generated signals at 250 Hz. Its six 15-second blocks are 15, 8, 10, off, 12 and off Hz. The values match the generator's seed-42 settings with three harmonics, SSVEP amplitude 80, noise amplitude 2, and no line noise or drift, in arbitrary units.

```sh
python -m neurovision replay data/synthetic/ssvep_example.csv --config configs/csv.example.json
```

We decode only the eight `EEG` columns. `Sample`, `TRIG`, `LABEL` and `TARGET_FREQ` are metadata; frequency labels are used separately to check the decoded output. The CSV does not embed its sample rate, so replay uses the accompanying config.

This file is synthetic demonstration data, not participant EEG. Successful recovery checks the software under these controlled conditions and does not establish live-EEG accuracy.
