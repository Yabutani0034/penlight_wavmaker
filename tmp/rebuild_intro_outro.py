from __future__ import annotations

import hashlib
import sys
import wave
from pathlib import Path


def signal_name(signal_id: int) -> str:
    return f"{signal_id:07b}.wav"


def read_wav(path: Path):
    with wave.open(str(path), "rb") as wav:
        params = wav.getparams()
        frames = wav.readframes(params.nframes)
    return params, frames


def repeat_to_frames(data: bytes, source_frames: int, frame_size: int, frames: int) -> bytes:
    repeats, remainder = divmod(frames, source_frames)
    return data * repeats + data[: remainder * frame_size]


def build_timeline(
    folder: Path,
    cues: list[tuple[float, int]],
    end_time: float,
    output_name: str,
) -> Path:
    filler_id = 121
    required_ids = {signal_id for _, signal_id in cues} | {filler_id}
    sources = {signal_id: read_wav(folder / signal_name(signal_id)) for signal_id in required_ids}

    base_params = sources[filler_id][0]
    base_format = (
        base_params.nchannels,
        base_params.sampwidth,
        base_params.framerate,
        base_params.comptype,
    )
    for signal_id, (params, _) in sources.items():
        current_format = (
            params.nchannels,
            params.sampwidth,
            params.framerate,
            params.comptype,
        )
        if current_format != base_format:
            raise ValueError(f"ID {signal_id} has a mismatched WAV format")

    rate = base_params.framerate
    frame_size = base_params.nchannels * base_params.sampwidth
    total_frames = round(end_time * rate)
    filler_params, filler_data = sources[filler_id]
    output = bytearray(
        repeat_to_frames(filler_data, filler_params.nframes, frame_size, total_frames)
    )

    # The requested signal is copied once at each cue start. ID 121 remains in every gap.
    for start_time, signal_id in cues:
        params, data = sources[signal_id]
        start_frame = round(start_time * rate)
        copy_frames = min(params.nframes, total_frames - start_frame)
        start_byte = start_frame * frame_size
        end_byte = (start_frame + copy_frames) * frame_size
        output[start_byte:end_byte] = data[: copy_frames * frame_size]

    output_path = folder / output_name
    with wave.open(str(output_path), "wb") as wav:
        wav.setparams(base_params)
        wav.writeframes(output)

    # Read back and validate duration.
    check_params, check_data = read_wav(output_path)
    if check_params.nframes != total_frames or check_data != bytes(output):
        raise AssertionError(f"Validation failed: {output_path.name}")
    return output_path


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as src:
        for block in iter(lambda: src.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def main(folder: Path) -> None:
    intro_cues = [
        (0.0, 1),
        (8.0, 8),
        (9.0, 11),
        (10.0, 13),
        (11.0, 8),
        (12.0, 11),
        (13.0, 13),
        (14.0, 8),
        (15.0, 11),
        (16.0, 13),
        (17.0, 8),
        (18.0, 11),
        (19.0, 17),
        (21.0, 52),
        (22.0, 58),
        (23.0, 56),
        (24.0, 50),
        (25.0, 58),
        (26.0, 56),
        (27.0, 52),
        (28.0, 125),
    ]
    outro_cues = [
        (0.0, 8),
        (2.0, 11),
        (4.0, 13),
        (6.0, 17),
        (9.0, 57),
        (12.0, 43),
        (15.0, 37),
        (18.0, 17),
        (21.0, 33),
        (23.0, 125),
    ]

    intro = build_timeline(
        folder,
        intro_cues,
        29.0,
        "timeline_penlight_intro_r-g-b_ID121_fill_00m00s-00m29s.wav",
    )
    outro = build_timeline(
        folder,
        outro_cues,
        24.0,
        "timeline_penlight_outro_r-g-b_breath_ID121_fill_00m00s-00m24s.wav",
    )

    for path, duration in ((intro, 29.0), (outro, 24.0)):
        print(f"{path.name}\t{duration:.3f}s\t{digest(path)}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
