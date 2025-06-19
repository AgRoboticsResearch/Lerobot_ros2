#!/usr/bin/env python3
"""ROS 2 node that bridges Feetech servos <-> topic_based_ros2_control.

It:
* subscribes to `/so101_follower/joint_commands` (sensor_msgs/JointState)
  and writes Goal_Position to the servos.
* publishes `/so101_follower/joint_states` every 20 ms using Present_Position.

Make sure the USB-to-UART adapter of the servo bus is accessible
(e.g. `/dev/ttyUSB0`) and you have permission to open it.
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
import sys
import math
import yaml, pathlib

# -----------------------------------------------------------------------------
# Provide lightweight stubs for optional third-party dependencies that the
# Feetech SDK imports but are not strictly required to operate the motors.
# -----------------------------------------------------------------------------
try:
    import deepdiff  # type: ignore
except ImportError:  # create stub
    import types
    deepdiff_stub = types.ModuleType("deepdiff")
    class _DD(dict):
        pass
    deepdiff_stub.DeepDiff = _DD  # type: ignore
    sys.modules["deepdiff"] = deepdiff_stub

try:
    import tqdm  # type: ignore
except ImportError:  # create stub
    import types
    tqdm_stub = types.ModuleType("tqdm")
    def _tqdm(iterable=None, **kwargs):
        return iterable if iterable is not None else []
    tqdm_stub.tqdm = _tqdm  # type: ignore
    sys.modules["tqdm"] = tqdm_stub

# -----------------------------------------------------------------------------

from so101_hw_interface.motors.feetech.feetech import FeetechMotorsBus
from so101_hw_interface.motors import Motor, MotorNormMode

PORT_DEFAULT = "/dev/ttyACM0"

JOINTS = {
    "shoulder_pan": {"id": 1, "model": "sts3215"},
    "shoulder_lift": {"id": 2, "model": "sts3215"},
    "elbow_flex": {"id": 3, "model": "sts3215"},
    "wrist_flex": {"id": 4, "model": "sts3215"},
    "wrist_roll": {"id": 5, "model": "sts3215"},
    "gripper": {"id": 6, "model": "sts3215"},
}

# default calibration path
CALIB_FILE = pathlib.Path.home() / ".so101_follower_calibration.yaml"

class MotorBridge(Node):
    def __init__(self):
        super().__init__("so101_motor_bridge")
        # Declare parameters so they can be overridden from launch/CLI
        self.declare_parameter("port", PORT_DEFAULT)
        self.declare_parameter("calib_file", str(CALIB_FILE))

        port = self.get_parameter("port").get_parameter_value().string_value
        if not port:
            port = PORT_DEFAULT

        # Build motor objects
        motors = {
            name: Motor(cfg["id"], cfg["model"], MotorNormMode.DEGREES)
            for name, cfg in JOINTS.items()
        }
        self.bus = FeetechMotorsBus(port, motors)

        self.get_logger().info(f"Connecting to Feetech bus on {port} …")
        try:
            self.bus.connect()
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f"Could not open motor bus: {exc}")
            raise
        self.bus.configure_motors()
        self.bus.enable_torque()
        self.get_logger().info("Motor bus connected and configured.")

        # Publishers / Subscribers
        self.joint_states_pub = self.create_publisher(JointState, "so101_follower/joint_states", 10)
        self.joint_commands_sub = self.create_subscription(
            JointState,
            "so101_follower/joint_commands",
            self._command_cb,
            10,
        )

        # Command cache (rad)
        self.current_commands: dict[str, float] = {name: 0.0 for name in JOINTS}

        # Feetech STS3215 resolution: 4096 steps per 2π rad
        self._steps_per_rad = 4096.0 / (2 * math.pi)

        # Load calibration (if file exists) else fall back to first-read capture
        calib_path = pathlib.Path(self.get_parameter("calib_file").get_parameter_value().string_value).expanduser()
        self._home_offsets: dict[str, int] | None = None
        self._limits: dict[str, tuple[int, int]] | None = None
        if calib_path.is_file():
            with open(calib_path, "r", encoding="utf-8") as fp:
                calib = yaml.safe_load(fp)
            self._home_offsets = {j: calib[j]["homing_offset"] for j in JOINTS if j in calib}
            self._limits = {j: (calib[j]["range_min"], calib[j]["range_max"]) for j in JOINTS if j in calib}
            self.get_logger().info(f"Loaded calibration from {calib_path}")
        else:
            self.get_logger().warn(f"Calibration file {calib_path} not found – will capture offsets on first read.")

        # Timer for periodic read/write (50 Hz)
        self.timer = self.create_timer(0.02, self._timer_cb)

        # Flag to ensure we only command the initial middle position once
        self._initial_move_done = False

    # ---------------------------------------------------------------------
    # Callbacks
    # ---------------------------------------------------------------------
    def _command_cb(self, msg: JointState):
        """Store desired joint positions from topic (rad)."""
        for name, pos in zip(msg.name, msg.position):
            if name in self.current_commands:
                self.current_commands[name] = pos

    def _timer_cb(self):
        # --- Read present positions
        try:
            raw_positions = self.bus.sync_read("Present_Position", normalize=False)

            # Establish home offsets once (first successful read)
            if self._home_offsets is None:
                self._home_offsets = raw_positions
                self.get_logger().info("Captured home offsets: %s" % self._home_offsets)

            # convert to radians relative to home
            positions = {
                n: (raw - self._home_offsets.get(n, 0)) * (2 * math.pi) / 4096.0 if self._home_offsets else 0.0
                for n, raw in raw_positions.items()
            }
        except Exception as exc:  # noqa: BLE001
            self.get_logger().warn(f"sync_read failed: {exc}")
            return

        # Publish joint states
        js = JointState()
        js.header.stamp = self.get_clock().now().to_msg()
        js.name = list(JOINTS.keys())
        js.position = [positions[n] for n in js.name]
        js.velocity = []
        js.effort = []
        self.joint_states_pub.publish(js)

        # -----------------------------------------------------------------
        # After the first successful read AND once we have both limits and
        # home offsets, send a single command to drive each joint to the
        # middle of its calibrated range. This provides a well-defined pose
        # on startup without relying on external controllers.
        # -----------------------------------------------------------------
        if (
            not self._initial_move_done
            and self._home_offsets is not None
            and self._limits is not None
        ):
            for name in JOINTS:
                if name in self._limits and name in self._home_offsets:
                    low, high = self._limits[name]
                    mid_raw = int((low + high) / 2)
                    # Convert to radians relative to home
                    self.current_commands[name] = (mid_raw - self._home_offsets[name]) * (2 * math.pi) / 4096.0
            self._initial_move_done = True
            self.get_logger().info("Issued initial command to move joints to mid-range position.")

        # --- Write goal positions
        try:
            # convert desired rad to raw steps relative to home
            raw_goals = {}
            for n, rad in self.current_commands.items():
                home = self._home_offsets.get(n, 0) if self._home_offsets else 0
                raw = int(home + rad * self._steps_per_rad)
                # clamp to limits if available
                if self._limits and n in self._limits:
                    low, high = self._limits[n]
                    raw = max(low, min(high, raw))
                raw_goals[n] = raw
            self.bus.sync_write("Goal_Position", raw_goals, normalize=False)
        except Exception as exc:  # noqa: BLE001
            self.get_logger().warn(f"sync_write failed: {exc}")


# -------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------

def main():  # noqa: D401
    """Entry-point."""
    rclpy.init()
    node = MotorBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.bus.disconnect()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main() 