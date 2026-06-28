from __future__ import annotations

import hashlib
import sys
import wave
from pathlib import Path


def read_wav(path: Path):
    with wave.open(str(path), "rb") as wav:
        params = wav.getparams()
        frames = wav.readframes(params.nframes)
    return params, frames


def repeat_to_frames(signal: bytes, signal_frames: int, frame_size: int, frames: int) -> bytes:
    if signal_frames <= 0:
        raise ValueError("ID 121 signal is empty")
    repeats, remainder = divmod(frames, signal_frames)
    return signal * repeats + signal[: remainder * frame_size]


def write_wav(path: Path, params, frames: bytes) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setparams(params)
        wav.writeframes(frames)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as src:
        for block in iter(lambda: src.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main(folder: Path) -> None:
    id121_path = folder / "1111001.wav"
    rgb_path = folder / "timeline_penlight_rgb_r-g-b_00m00s-00m29s.wav"
    breath_path = folder / "timeline_penlight_rgb_breath_timed_once_00m00s-00m24p60s.wav"

    signal_params, signal = read_wav(id121_path)
    rgb_params, rgb = read_wav(rgb_path)
    breath_params, breath = read_wav(breath_path)

    signal_format = (
        signal_params.nchannels,
        signal_params.sampwidth,
        signal_params.framerate,
        signal_params.comptype,
    )
    for name, params in (("RGB", rgb_params), ("breath", breath_params)):
        file_format = (params.nchannels, params.sampwidth, params.framerate, params.comptype)
        if file_format != signal_format:
            raise ValueError(f"{name} WAV format does not match ID 121")

    frame_size = signal_params.nchannels * signal_params.sampwidth
    rate = signal_params.framerate

    # Append ID 121 continuously for exactly three seconds.
    append_frames = 3 * rate
    rgb_out_frames = rgb + repeat_to_frames(
        signal, signal_params.nframes, frame_size, append_frames
    )
    rgb_out = folder / "timeline_penlight_rgb_r-g-b_plus_ID121_00m00s-00m32s.wav"
    write_wav(rgb_out, rgb_params, rgb_out_frames)

    # Every cue is one second long. Fill only the gaps between cue end and next cue.
    cue_starts = (0.0, 2.0, 4.0, 6.0, 9.0, 12.0, 15.0, 18.0, 21.5, 23.6)
    gaps = [(start + 1.0, next_start) for start, next_start in zip(cue_starts, cue_starts[1:])]
    breath_out_frames = bytearray(breath)
    for gap_start, gap_end in gaps:
        start_frame = round(gap_start * rate)
        end_frame = round(gap_end * rate)
        replacement = repeat_to_frames(
            signal, signal_params.nframes, frame_size, end_frame - start_frame
        )
        breath_out_frames[start_frame * frame_size : end_frame * frame_size] = replacement

    breath_out = (
        folder
        / "timeline_penlight_rgb_breath_timed_once_ID121_fill_00m00s-00m24p60s.wav"
    )
    write_wav(breath_out, breath_params, bytes(breath_out_frames))

    # Validate exact durations and that all non-gap regions in the breath file stayed untouched.
    expected_rgb_frames = rgb_params.nframes + append_frames
    if len(rgb_out_frames) // frame_size != expected_rgb_frames:
        raise AssertionError("RGB output duration mismatch")
    if len(breath_out_frames) != len(breath):
        raise AssertionError("Breath output duration changed")
    cursor = 0
    for gap_start, gap_end in gaps:
        start = round(gap_start * rate) * frame_size
        end = round(gap_end * rate) * frame_size
        if breath_out_frames[cursor:start] != breath[cursor:start]:
            raise AssertionError("Existing breath cue data was altered")
        cursor = end
    if breath_out_frames[cursor:] != breath[cursor:]:
        raise AssertionError("Existing breath cue data was altered")

    print(f"{rgb_out.name}\t{expected_rgb_frames / rate:.3f}s\t{sha256(rgb_out)}")
    print(f"{breath_out.name}\t{breath_params.nframes / rate:.3f}s\t{sha256(breath_out)}")
    print("filled gaps:", ", ".join(f"{a:.2f}-{b:.2f}s" for a, b in gaps))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
