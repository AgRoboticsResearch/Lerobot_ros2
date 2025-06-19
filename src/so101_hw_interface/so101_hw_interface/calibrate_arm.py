#!/usr/bin/env python3
"""Interactive calibration helper for the SO-101 follower arm.

What it does
------------
1. Connects to the Feetech bus.
2. Reads the *current* raw encoder value of every joint and stores it as the
   home (zero) offset.
3. Optionally lets you move to the positive / negative mechanical stops and
   records those as `range_max` / `range_min`.
4. Writes the data to a YAML file (default: `~/.so101_follower_calibration.yaml`).

Run:
    ros2 run so101_hw_interface so101_calibrate   # --ros-args -p port:=/dev/ttyACM0
"""
from __future__ import annotations

import getpass
import os
import pathlib
import sys
from datetime import datetime
import time
import select

import rclpy
from rclpy.node import Node
import yaml

from so101_hw_interface.motors.feetech.feetech import FeetechMotorsBus
from so101_hw_interface.motors import Motor, MotorNormMode

JOINTS = {
    "shoulder_pan": {"id": 1, "model": "sts3215"},
    "shoulder_lift": {"id": 2, "model": "sts3215"},
    "elbow_flex": {"id": 3, "model": "sts3215"},
    "wrist_flex": {"id": 4, "model": "sts3215"},
    "wrist_roll": {"id": 5, "model": "sts3215"},
    "gripper": {"id": 6, "model": "sts3215"},
}

DEFAULT_PATH = pathlib.Path.home() / ".so101_follower_calibration.yaml"

class Calibrator(Node):
    def __init__(self):
        super().__init__("so101_calibrator")
        self.declare_parameter("port", "/dev/ttyACM0")
        self.declare_parameter("outfile", str(DEFAULT_PATH))

        port = self.get_parameter("port").get_parameter_value().string_value
        outfile = pathlib.Path(
            self.get_parameter("outfile").get_parameter_value().string_value
        ).expanduser()
        self.outfile = outfile

        motors = {
            name: Motor(cfg["id"], cfg["model"], MotorNormMode.DEGREES)
            for name, cfg in JOINTS.items()
        }
        self.bus = FeetechMotorsBus(port, motors)
        self.get_logger().info(f"Connecting to bus on {port} …")
        self.bus.connect()

        self.calib: dict[str, dict[str, int]] = {}

    # ------------------------------------------------------------
    def run(self):
        print("We'll record mechanical limits joint-by-joint.\n"
              "For each joint:\n"
              "  1. Rotate to the NEGATIVE mechanical stop and press <Enter>.\n"
              "  2. Rotate to the POSITIVE mechanical stop and press <Enter>.\n")

        for joint in JOINTS:
            input(f"Move {joint} to its NEGATIVE stop then press Enter…")
            neg = self.bus.read("Present_Position", joint, normalize=False)
            input(f"Now move {joint} to its POSITIVE stop then press Enter…")
            pos = self.bus.read("Present_Position", joint, normalize=False)

            # ensure correct ordering
            range_min = int(min(neg, pos))
            range_max = int(max(neg, pos))
            home = int((range_min + range_max) // 2)

            self.calib[joint] = {
                "range_min": range_min,
                "range_max": range_max,
                "homing_offset": home,
            }

        print("\nCalibration captured.  Mid-point between min/max will be treated as zero.")

        # Save YAML
        self.outfile.parent.mkdir(parents=True, exist_ok=True)
        with open(self.outfile, "w", encoding="utf-8") as fp:
            yaml.safe_dump({"generated": datetime.now().isoformat(), **self.calib}, fp, sort_keys=False)
        self.get_logger().info(f"Calibration written to {self.outfile}")

        self.bus.disconnect()


def main():  # noqa: D401
    rclpy.init()
    cal = Calibrator()
    try:
        cal.run()
    finally:
        rclpy.shutdown()

if __name__ == "__main__":
    main() 