import rclpy
from rclpy.node import Node
import hardware_interface
from hardware_interface import SystemInterface
import hardware_interface.msg as hardware_interface_msg

from so101_hw_interface.motors.feetech import FeetechMotorsBus
from so101_hw_interface.motors import Motor, MotorNormMode


class SO101SystemInterface(SystemInterface):

    def on_init(self, info):
        self.info_ = info
        self.port = self.info_.hardware_parameters['port']
        
        self.joints = {}
        for joint in self.info_.joints:
            self.joints[joint.name] = {
                "id": int(joint.parameters["id"]),
                "model": joint.parameters["model"],
                "position": 0.0,
                "velocity": 0.0,
                "effort": 0.0,
                "command": 0.0,
            }

        motors = {
            name: Motor(params["id"], params["model"], MotorNormMode.DEGREES)
            for name, params in self.joints.items()
        }
        self.bus_ = FeetechMotorsBus(self.port, motors)

        return hardware_interface_msg.CallbackReturn.SUCCESS

    def export_state_interfaces(self):
        state_interfaces = []
        for joint_name in self.joints:
            state_interfaces.append(
                hardware_interface.StateInterface(
                    name=joint_name, interface_name="position", value=self.joints[joint_name]["position"]
                )
            )
            state_interfaces.append(
                hardware_interface.StateInterface(
                    name=joint_name, interface_name="velocity", value=self.joints[joint_name]["velocity"]
                )
            )
            state_interfaces.append(
                hardware_interface.StateInterface(
                    name=joint_name, interface_name="effort", value=self.joints[joint_name]["effort"]
                )
            )
        return state_interfaces

    def export_command_interfaces(self):
        command_interfaces = []
        for joint_name in self.joints:
            command_interfaces.append(
                hardware_interface.CommandInterface(
                    name=joint_name, interface_name="position"
                )
            )
        return command_interfaces

    def on_configure(self, state):
        self.bus_.configure_motors()
        for motor in self.bus_.motors:
            self.bus_.write("Operating_Mode", motor, 3) # 3 for position mode
            self.bus_.write("P_Coefficient", motor, 16)
            self.bus_.write("I_Coefficient", motor, 0)
            self.bus_.write("D_Coefficient", motor, 32)
        return hardware_interface_msg.CallbackReturn.SUCCESS

    def on_activate(self, state):
        self.bus_.connect()

        # Attempt to move each joint to the middle of its calibrated range
        try:
            # If calibration parameters are available on the ROS param server,
            # load them. Otherwise, fall back to the YAML used by MotorBridge.
            import pathlib, yaml

            calib_path = pathlib.Path.home() / ".so101_follower_calibration.yaml"
            if calib_path.is_file():
                with calib_path.open("r", encoding="utf-8") as fp:
                    calib = yaml.safe_load(fp)

                goal_pos = {}
                for joint_name, params in self.joints.items():
                    if joint_name not in calib:
                        continue
                    rng_min = calib[joint_name]["range_min"]
                    rng_max = calib[joint_name]["range_max"]
                    mid_raw = int((rng_min + rng_max) / 2)
                    goal_pos[joint_name] = mid_raw  # absolute raw value

                if goal_pos:
                    self.bus_.sync_write("Goal_Position", goal_pos)
        except Exception:  # noqa: BLE001
            # If anything goes wrong, proceed without blocking activation.
            pass

        return hardware_interface_msg.CallbackReturn.SUCCESS

    def on_deactivate(self, state):
        self.bus_.disconnect(disable_torque=True)
        return hardware_interface_msg.CallbackReturn.SUCCESS

    def read(self, time, period):
        obs = self.bus_.sync_read("Present_Position")
        for joint_name, pos in obs.items():
            self.joints[joint_name]["position"] = pos
        return hardware_interface_msg.CallbackReturn.SUCCESS

    def write(self, time, period):
        goal_pos = {}
        for joint_name in self.joints:
            goal_pos[joint_name] = self.joints[joint_name]["command"]
        self.bus_.sync_write("Goal_Position", goal_pos)
        return hardware_interface_msg.CallbackReturn.SUCCESS 