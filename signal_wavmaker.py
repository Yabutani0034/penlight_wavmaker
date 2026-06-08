import os
import wave
import numpy as np


# =========================
# 設定
# =========================

FS = 48_000
SYMBOL_SEC = 0.125
BIT_LENGTH = 7
OUTPUT_DIR = os.path.join("signal", "7bit_19k-20k")

AMPLITUDE = 0.5
FADE_MS = 3

# 値 → 周波数
VALUE_TO_FREQ = {
    0: 19_000,
    1: 19_250,
    2: 19_500,
    3: 19_750,
    4: 20_000,
}

# 偶数列: 0bit / 1bit をどの値にするか
# 0bit -> 1
# 1bit -> 3
EVEN_COLUMN_VALUE = {
    "0": 1,
    "1": 3,
}

# 奇数列: 0bit / 1bit をどの値にするか
# 0bit -> 2
# 1bit -> 4
ODD_COLUMN_VALUE = {
    "0": 2,
    "1": 4,
}

TEST_TONES = {
    "test_19000.wav": 19_000,
    "test_19250.wav": 19_250,
    "test_19500.wav": 19_500,
    "test_19750.wav": 19_750,
    "test_20000.wav": 20_000,
}


# =========================
# 基本関数
# =========================

def sine_wave(freq: float, duration_sec: float, fs: int) -> np.ndarray:
    sample_count = int(duration_sec * fs)
    t = np.arange(sample_count) / fs
    return np.sin(2 * np.pi * freq * t)


def apply_fade(signal: np.ndarray, fs: int, fade_ms: float) -> np.ndarray:
    fade_samples = int(fs * fade_ms / 1000)

    if fade_samples <= 0:
        return signal

    if len(signal) < fade_samples * 2:
        return signal

    faded = signal.copy()

    fade_in = np.linspace(0.0, 1.0, fade_samples)
    fade_out = np.linspace(1.0, 0.0, fade_samples)

    faded[:fade_samples] *= fade_in
    faded[-fade_samples:] *= fade_out

    return faded


def normalize_to_int16(signal: np.ndarray, amplitude: float) -> np.ndarray:
    signal = np.clip(signal, -1.0, 1.0)
    signal = signal * amplitude
    return (signal * 32767).astype(np.int16)


def write_wav(path: str, signal: np.ndarray, fs: int):
    pcm = normalize_to_int16(signal, AMPLITUDE)

    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(fs)
        wf.writeframes(pcm.tobytes())


# =========================
# 符号音生成
# =========================

def bit_to_value(bit: str, column_index: int) -> int:
    """
    bitと列番号から、0〜4の値を決める。

    column_indexは1始まり。

    1列目: 必ず0
    偶数列: 1 or 3
    奇数列: 2 or 4
    """
    if column_index == 1:
        return 0

    if column_index % 2 == 0:
        return EVEN_COLUMN_VALUE[bit]
    else:
        return ODD_COLUMN_VALUE[bit]


def bit_to_freq(bit: str, column_index: int) -> int:
    value = bit_to_value(bit, column_index)
    return VALUE_TO_FREQ[value]


def generate_command_signal(bits: str) -> np.ndarray:
    """
    7bitコマンド音を生成する。

    構造:
      [START][b6][b5][b4][b3][b2][b1][b0]

    全体:
      8 symbols × 0.125 sec = 1.0 sec
    """
    if len(bits) != BIT_LENGTH:
        raise ValueError(f"bits must be {BIT_LENGTH} characters: {bits}")

    if any(b not in ("0", "1") for b in bits):
        raise ValueError(f"bits must contain only 0 or 1: {bits}")

    symbols = []

    # 1列目: START = 0 = 19.00kHz
    start_freq = VALUE_TO_FREQ[0]
    start_symbol = sine_wave(start_freq, SYMBOL_SEC, FS)
    start_symbol = apply_fade(start_symbol, FS, FADE_MS)
    symbols.append(start_symbol)

    # 2〜8列目: 7bitデータ
    for i, bit in enumerate(bits):
        column_index = i + 2
        freq = bit_to_freq(bit, column_index)

        symbol = sine_wave(freq, SYMBOL_SEC, FS)
        symbol = apply_fade(symbol, FS, FADE_MS)
        symbols.append(symbol)

    return np.concatenate(symbols)


def generate_all_command_wavs():
    """
    0000000.wav 〜 1111111.wav を生成する。
    7bitなので128個。
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for value in range(2 ** BIT_LENGTH):
        bits = format(value, f"0{BIT_LENGTH}b")
        signal = generate_command_signal(bits)

        path = os.path.join(OUTPUT_DIR, f"{bits}.wav")
        write_wav(path, signal, FS)

    print(f"Generated {2 ** BIT_LENGTH} command WAV files in '{OUTPUT_DIR}/'")


# =========================
# テストトーン生成
# =========================

def generate_test_tones(duration_sec: float = 1.0):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for filename, freq in TEST_TONES.items():
        signal = sine_wave(freq, duration_sec, FS)
        signal = apply_fade(signal, FS, FADE_MS)

        path = os.path.join(OUTPUT_DIR, filename)
        write_wav(path, signal, FS)

    print(f"Generated test tones in '{OUTPUT_DIR}/'")


# =========================
# 実行
# =========================

if __name__ == "__main__":
    generate_all_command_wavs()
    generate_test_tones()
    print("Done.")