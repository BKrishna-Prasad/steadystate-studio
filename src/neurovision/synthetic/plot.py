"""Optional inspection plot for explicitly labelled synthetic data."""

import numpy as np
from scipy import signal


def plot_recording(recording, results, output):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise RuntimeError(
            "Install plotting support: python -m pip install '.[plot]'"
        ) from error
    from ..preprocessing.filters import Preprocessor

    fs = recording.settings.decoder.fs
    cleaned = Preprocessor(recording.settings.decoder).preprocess_for_plot(
        recording.samples
    )
    f, t, power = signal.spectrogram(
        cleaned[:, -1], fs=fs, nperseg=round(fs * 2), noverlap=round(fs * 1.5)
    )
    fig, axes = plt.subplots(3, 1, figsize=(11, 8))
    fig.subplots_adjust(left=0.08, right=0.77, top=0.92, bottom=0.07, hspace=0.38)
    time_axis = np.arange(len(recording.samples)) / fs
    axes[0].plot(
        time_axis, recording.injected_hz, label="Known injection", color="#203b62"
    )
    axes[0].step(
        [r.end_time_sec for r in results],
        [r.frequency_hz for r in results],
        where="post",
        label="Committed decoder state",
        color="#d97520",
    )
    axes[0].set_ylabel("Frequency (Hz)")
    axes[0].set_ylim(-0.8, max(recording.settings.decoder.freqs) + 3.5)
    axes[0].legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=9)
    keep = f <= 45
    image = axes[1].pcolormesh(
        t, f[keep], 10 * np.log10(power[keep] + 1e-18), shading="auto", cmap="magma"
    )
    axes[1].set_ylabel("Frequency (Hz)")
    axes[1].set_title("Last synthetic channel: notch, display band-pass, CAR, detrend")
    position = axes[1].get_position()
    colorbar_axis = fig.add_axes(
        [position.x1 + 0.03, position.y0, 0.012, position.height]
    )
    fig.colorbar(image, cax=colorbar_axis, label="PSD (dB, arbitrary units)")
    for i, freq in enumerate(recording.settings.decoder.freqs):
        axes[2].plot(
            [r.end_time_sec for r in results],
            [r.scores[i] for r in results],
            label=f"{freq:g} Hz",
        )
    axes[2].axhline(recording.settings.decoder.min_score, color="gray", ls="--")
    axes[2].set_ylabel("FBCCA score")
    axes[2].set_xlabel("Time (seconds)")
    axes[2].legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=9)
    fig.suptitle("Controlled synthetic software demo - not live EEG validation")
    fig.savefig(output, dpi=160)
    plt.close(fig)
