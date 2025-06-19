# LeRobot ROS2 - SO101 Follower Arm

A ROS2 implementation for the SO101 follower robotic arm, providing complete integration with LeRobot framework including hardware interface, MoveIt motion planning, and topic-based control.

## 🤖 Overview

This repository contains ROS2 packages for controlling the SO101 follower arm robot. It includes:

- **Robot Description**: URDF/XACRO models with 3D meshes
- **MoveIt Integration**: Motion planning and execution
- **Hardware Interface**: Direct motor control via Feetech servos
- **Topic-based Control**: Flexible control interface

## 📦 Packages

### `so101_follower_description`
Robot description package containing:
- URDF/XACRO robot model
- 3D mesh files (.stl/.part)
- RViz visualization configuration
- Launch files for robot display

### `so101_follower_moveit`
MoveIt configuration package with:
- Kinematic configuration
- Motion planning setup
- Controller configuration
- Collision detection setup

### `so101_hw_interface`
Hardware interface package providing:
- Motor control via Feetech protocol
- Calibration utilities
- Hardware abstraction layer
- LeRobot integration utilities

### `topic_based_ros2_control`
Generic topic-based control interface for:
- Flexible control architectures
- Custom control strategies
- Integration with external systems

## 🚀 Quick Start

### Prerequisites
- ROS2 Humble or later
- MoveIt2
- Python 3.8+

### Installation

1. Clone the repository:
```bash
git clone git@github.com:forgetwhatuwant/Lerobot_ros2.git
cd Lerobot_ros2
```

2. Install dependencies:
```bash
rosdep install --from-paths src --ignore-src -r -y
```

3. Build the workspace:
```bash
colcon build
source install/setup.bash
```

### Usage

#### Visualize the robot:
```bash
ros2 launch so101_follower_description display.launch.py
```

#### Launch MoveIt demo:
```bash
ros2 launch so101_follower_moveit demo.launch.py
```

#### Start hardware interface:
```bash
ros2 launch so101_hw_interface so101_hw.launch.py
```

#### Calibrate the arm:
```bash
ros2 run so101_hw_interface so101_calibrate
```

## 🔧 Configuration

### Hardware Setup
- Connect Feetech servos via serial/USB interface
- Update motor IDs in `config/so101_calibration.yaml`
- Verify communication with `so101_motor_bridge`

### Calibration
1. Run calibration script: `so101_calibrate`
2. Follow on-screen instructions to move joints
3. Calibration data saved automatically

## 📚 Documentation

- [Hardware Setup Guide](docs/hardware_setup.md)
- [Calibration Process](docs/calibration.md)
- [MoveIt Integration](docs/moveit_integration.md)
- [API Reference](docs/api_reference.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

For questions and support:
- Open an issue on GitHub
- Check the documentation
- Join our community discussions

## 🔗 Related Projects

- [LeRobot](https://github.com/huggingface/lerobot) - Main LeRobot framework
- [SO101 Hardware](https://github.com/TheRobotStudio/SO-ARM101) - Original hardware design

---

**Made with ❤️ for the robotics community** 