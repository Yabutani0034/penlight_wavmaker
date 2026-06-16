from datetime import datetime
from pathlib import Path
import argparse
import re
import sys

import serial
from serial import SerialException
from serial.tools import list_ports


PORT = "COM6"
BAUDRATE = 115200
OUTPUT_DIR = Path(
    r"C:\Users\0108411501\OneDrive - Sony\code\laboratory\AAI\balloon\penlight_wavmaker\received_command"
)

COMMAND_LINE_PATTERN = re.compile(r"^received command=(\d+)$")


def available_ports() -> list[str]:
    return [port.device for port in list_ports.comports()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Log received command values from a serial port.")
    parser.add_argument("--port", default=PORT, help=f"serial port to open (default: {PORT})")
    parser.add_argument("--baudrate", type=int, default=BAUDRATE, help=f"baudrate (default: {BAUDRATE})")
    parser.add_argument("--list-ports", action="store_true", help="show available serial ports and exit")
    return parser.parse_args()


def save_commands(commands: list[int]) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output_file = OUTPUT_DIR / f"commands_{timestamp}.txt"
    output_file.write_text(
        "\n".join(str(command) for command in commands) + "\n",
        encoding="utf-8",
    )

    return output_file


def handle_line(line: str, commands: list[int]) -> None:
    match = COMMAND_LINE_PATTERN.search(line)
    if match is None:
        return

    command = int(match.group(1))
    commands.append(command)
    print(f"received command={command}")


def main() -> int:
    args = parse_args()

    if args.list_ports:
        ports = available_ports()
        print("available ports: " + (", ".join(ports) if ports else "none"))
        return 0

    commands: list[int] = []

    try:
        with serial.Serial(args.port, args.baudrate, timeout=1) as serial_port:
            print(f"listening on {args.port} at {args.baudrate} baud")
            print(f"output directory: {OUTPUT_DIR}")

            while True:
                line = serial_port.readline().decode("utf-8", errors="ignore").strip()
                if line:
                    handle_line(line, commands)

    except KeyboardInterrupt:
        print("stopped")

        if commands:
            output_file = save_commands(commands)
            print(f"saved {len(commands)} commands: {output_file}")
        else:
            print("no commands received")

        return 0

    except SerialException as error:
        print(f"serial error: {error}", file=sys.stderr)
        ports = available_ports()
        print("available ports: " + (", ".join(ports) if ports else "none"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())