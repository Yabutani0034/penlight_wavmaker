import sys
import wave
from pathlib import Path


def read_wav(path: Path):
    with wave.open(str(path), "rb") as wav:
        params = wav.getparams()
        return params, wav.readframes(params.nframes)


folder = Path(sys.argv[1])
source_path = folder / "timeline_penlight_intro_r-g-b_ID121_fill_00m00s-00m29s.wav"
id121_path = folder / "1111001.wav"
output_path = folder / "timeline_penlight_intro_r-g-b_ID121_fill_plus_ID121_00m00s-00m32s.wav"

source_params, source_data = read_wav(source_path)
id121_params, id121_data = read_wav(id121_path)

source_format = (
    source_params.nchannels,
    source_params.sampwidth,
    source_params.framerate,
    source_params.comptype,
)
id121_format = (
    id121_params.nchannels,
    id121_params.sampwidth,
    id121_params.framerate,
    id121_params.comptype,
)
if source_format != id121_format:
    raise ValueError("WAV formats do not match")

frame_size = source_params.nchannels * source_params.sampwidth
append_frames = 3 * source_params.framerate
repeats, remainder = divmod(append_frames, id121_params.nframes)
appended_data = id121_data * repeats + id121_data[: remainder * frame_size]

with wave.open(str(output_path), "wb") as wav:
    wav.setparams(source_params)
    wav.writeframes(source_data + appended_data)

check_params, check_data = read_wav(output_path)
expected_frames = source_params.nframes + append_frames
if check_params.nframes != expected_frames or check_data != source_data + appended_data:
    raise AssertionError("Output verification failed")

print(f"{output_path.name}\t{check_params.nframes / check_params.framerate:.3f}s")
