#!/usr/bin/env python3
"""Simple helper to dump raw *Present_Position* of all SO-101 follower servos.

Usage
-----
ros2 run so101_hw_interface so101_read_steps [--port /dev/ttyACM0]

The script prints a YAML dictionary mapping joint names to their current raw
encoder counts (0-4095).  This is useful when calibrating or debugging the
URDF → servo mapping.
"""
from __future__ import annotations

import argparse
import sys
import yaml

from so101_hw_interface.motors.feetech.feetech import FeetechMotorsBus
from so101_hw_interface.motors import Motor, MotorNormMode

# -----------------------------------------------------------------------------
# Joint → (ID, model) map – keep in sync with the rest of the package
# -----------------------------------------------------------------------------
JOINTS: dict[str, dict[str, int | str]] = {
    "shoulder_pan": {"id": 1, "model": "sts3215"},
    "shoulder_lift": {"id": 2, "model": "sts3215"},
    "elbow_flex": {"id": 3, "model": "sts3215"},
    "wrist_flex": {"id": 4, "model": "sts3215"},
    "wrist_roll": {"id": 5, "model": "sts3215"},
    "gripper": {"id": 6, "model": "sts3215"},
}


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> None:  # noqa: D401
    """Entry-point for *so101_read_steps*."""
    parser = argparse.ArgumentParser(
        prog="so101_read_steps",
        description="Read raw Present_Position of all SO-101 follower servos and print as YAML.",
    )
    parser.add_argument(
        "--port",
        default="/dev/ttyACM0",
        help="Serial port to which the Feetech bus is connected (default: /dev/ttyACM0)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Read once and exit (default). If omitted the script keeps printing every second.",
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=1.0,
        help="Polling rate in Hz when running continuously (default: 1.0)",
    )
    args = parser.parse_args()

    motors = {
        name: Motor(cfg["id"], cfg["model"], MotorNormMode.DEGREES) for name, cfg in JOINTS.items()
    }

    try:
        bus = FeetechMotorsBus(args.port, motors)
        bus.connect()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: could not connect to bus on {args.port}: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        import time

        def _read_and_print() -> None:
            pos_raw = bus.sync_read("Present_Position", normalize=False)
            print(yaml.safe_dump(pos_raw, sort_keys=False))

        if args.once:
            _read_and_print()
        else:
            period = 1.0 / max(args.rate, 0.01)
            while True:
                start = time.time()
                _read_and_print()
                elapsed = time.time() - start
                time.sleep(max(0.0, period - elapsed))
    finally:
        bus.disconnect()


if __name__ == "__main__":
    main() 