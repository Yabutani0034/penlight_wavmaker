import argparse
import json
import wave
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT = "combined.wav"
DEFAULT_CONFIG = Path(__file__).with_name("concat_10_commands.json")


def load_config(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as file:
        config = json.load(file)

    if not isinstance(config, dict):
        raise ValueError("JSON root must be an object")

    return config


def get_wav_paths(config: dict[str, Any], base_dir: Path) -> list[Path]:
    files = config.get("files")

    if files is None:
        files = config.get("wav_files")

    if not isinstance(files, list) or not files:
        raise ValueError("JSON must contain a non-empty 'files' array")

    wav_paths = []
    for index, item in enumerate(files, start=1):
        if isinstance(item, str):
            path_text = item
        elif isinstance(item, dict) and isinstance(item.get("path"), str):
            path_text = item["path"]
        else:
            raise ValueError(f"files[{index}] must be a string or an object with a 'path' string")

        wav_path = Path(path_text)
        if not wav_path.is_absolute():
            wav_path = base_dir / wav_path

        wav_paths.append(wav_path)

    return wav_paths


def get_output_path(config: dict[str, Any], base_dir: Path) -> Path:
    output = config.get("output", DEFAULT_OUTPUT)

    if not isinstance(output, str) or not output:
        raise ValueError("'output' must be a non-empty string")

    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = base_dir / output_path

    return output_path


def read_wav_params(wav_path: Path) -> wave._wave_params:
    if not wav_path.exists():
        raise FileNotFoundError(f"WAV file not found: {wav_path}")

    with wave.open(str(wav_path), "rb") as wav_file:
        return wav_file.getparams()


def validate_wav_files(wav_paths: list[Path]) -> wave._wave_params:
    base_params = read_wav_params(wav_paths[0])
    base_format = base_params[:4]

    for wav_path in wav_paths[1:]:
        params = read_wav_params(wav_path)
        if params[:4] != base_format:
            raise ValueError(
                "WAV format mismatch: "
                f"{wav_path} has channels={params.nchannels}, "
                f"sample_width={params.sampwidth}, "
                f"framerate={params.framerate}, "
                f"compression={params.comptype}; "
                f"expected channels={base_params.nchannels}, "
                f"sample_width={base_params.sampwidth}, "
                f"framerate={base_params.framerate}, "
                f"compression={base_params.comptype}"
            )

    return base_params


def concat_wavs(wav_paths: list[Path], output_path: Path) -> None:
    params = validate_wav_files(wav_paths)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(output_path), "wb") as output_file:
        output_file.setparams(params)

        for wav_path in wav_paths:
            with wave.open(str(wav_path), "rb") as input_file:
                output_file.writeframes(input_file.readframes(input_file.getnframes()))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Concatenate WAV files listed in a JSON file into one WAV file."
    )
    parser.add_argument(
        "json",
        nargs="?",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"Path to the JSON config file, default: {DEFAULT_CONFIG.name}",
    )
    args = parser.parse_args()

    config_path = args.json.resolve()
    config = load_config(config_path)
    base_dir = config_path.parent

    wav_paths = get_wav_paths(config, base_dir)
    output_path = get_output_path(config, base_dir)

    concat_wavs(wav_paths, output_path)

    print(f"concatenated {len(wav_paths)} wav files: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
