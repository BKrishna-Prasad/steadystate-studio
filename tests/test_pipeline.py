from pathlib import Path

import numpy as np
import pytest
from neurovision.config import Settings, settings_from_dict
from neurovision.decoding.decision import DecisionSmoother
from neurovision.decoding.pipeline import Pipeline
from neurovision.synthetic.signals import (
    check_recovery,
    generate,
    load_csv,
    load_recording,
)


def feed(recording, chunk_size):
    pipeline = Pipeline(recording.settings)
    return [
        result
        for start in range(0, len(recording.samples), chunk_size)
        for result in pipeline.feed(recording.samples[start : start + chunk_size])
    ]


def test_known_frequency_and_rest_recovery(tmp_path):
    recording = generate(Settings())
    results = feed(recording, 137)
    assert check_recovery(recording, results)["passed"]
    path = tmp_path / "synthetic.npz"
    recording.save(path)
    loaded = load_recording(path)
    np.testing.assert_array_equal(recording.samples, loaded.samples)
    assert [r.to_dict() for r in results] == [r.to_dict() for r in feed(loaded, 501)]
    assert [r.frequency_hz for r in results if r.changed] == [8, 0, 10, 0, 12, 0, 15, 0]


def test_example_csv_matches_seeded_generation():
    root = Path(__file__).resolve().parents[1]
    recording = load_csv(
        root / "data/synthetic/ssvep_example.csv", Settings()
    )
    reconstructed = generate(
        Settings(), schedule="15:15,8:15,10:15,off:15,12:15,off:15"
    )
    np.testing.assert_allclose(
        recording.samples, reconstructed.samples, rtol=1e-12, atol=1e-12
    )
    np.testing.assert_array_equal(recording.injected_hz, reconstructed.injected_hz)


def test_margin_and_temporal_gates():
    cfg = Settings().decoder
    smoother = DecisionSmoother(cfg)
    for _ in range(cfg.consecutive_wins - 1):
        assert smoother.step(np.array([0.9, 0.1, 0.1, 0.1])).action == "HOLD"
    assert smoother.step(np.array([0.9, 0.1, 0.1, 0.1])).action == "SET_IDX"
    # High absolute scores with an insufficient margin still fail the gate.
    for _ in range(cfg.no_control_wins - 1):
        assert smoother.step(np.array([0.9, 0.88, 0.1, 0.1])).action == "HOLD"
    assert smoother.step(np.array([0.9, 0.88, 0.1, 0.1])).action == "SET_NONE"


@pytest.mark.parametrize(
    "bad",
    [
        {"decoder": {"fs": 80}},
        {"decoder": {"harmonics": 9}},
        {"decoder": {"consecutive_wins": 0}},
        {"decoder": {"min_score": 1.1}},
        {"lsl": {"expected_channels": 1}},
        {"lsl": {"eeg_channels": [0, 0, 1, 2, 3, 4, 5, 6]}},
        {"decoder": {"invented_accuracy": 1}},
        {"synthetic": {"seed": -1}},
    ],
)
def test_invalid_settings_are_rejected(bad):
    with pytest.raises(ValueError):
        settings_from_dict(bad)


def test_nonfinite_eeg_is_rejected():
    pipeline = Pipeline(Settings())
    with pytest.raises(ValueError):
        pipeline.feed(np.full((400, 8), np.nan))
