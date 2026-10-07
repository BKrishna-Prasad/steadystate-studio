"""Generate, replay and check labelled synthetic demonstration signals."""

import json
import threading
from pathlib import Path

from ..decoding.pipeline import Pipeline
from .signals import check_recovery


def run(recording, output_dir, use_lsl=False):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    recording.save(output / "synthetic.npz")
    results = []
    if use_lsl:
        import uuid

        from ..acquisition.lsl import publish_recording, resolve_named, synthetic_outlet
        from ..acquisition.runtime import decode_lsl

        outlet = synthetic_outlet(recording, f"NeuroVision_Demo_{uuid.uuid4().hex}")
        stop = threading.Event()
        errors = []

        def publish():
            try:
                publish_recording(outlet, recording, stop=stop)
            except Exception as error:
                errors.append(error)

        thread = threading.Thread(target=publish, daemon=True)
        thread.start()
        try:
            descriptor = outlet.get_info()
            info = resolve_named(
                descriptor.name(),
                recording.settings.lsl.connect_timeout_sec,
                descriptor.source_id(),
            )
            decode_lsl(
                recording.settings,
                results.append,
                sample_limit=len(recording.samples),
                info=info,
            )
        finally:
            stop.set()
            thread.join(timeout=2)
        if errors:
            raise errors[0]
    else:
        pipeline = Pipeline(recording.settings)
        for start in range(0, len(recording.samples), 137):
            results.extend(pipeline.feed(recording.samples[start : start + 137]))
    with (output / "decoder.jsonl").open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result.to_dict(), allow_nan=False) + "\n")
    report = check_recovery(recording, results)
    report["transport"] = "lsl_local_replay" if use_lsl else "offline"
    report["settings"] = recording.settings.to_dict()
    (output / "report.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return report, results
