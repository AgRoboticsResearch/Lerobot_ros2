from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution
from ament_index_python.packages import get_package_share_directory
from launch_ros.substitutions import FindPackageShare
import os

def generate_launch_description():
    pkg_share = get_package_share_directory('so101_hw_interface')
    
    # Get URDF via xacro
    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution(
                [
                    FindPackageShare("so101_follower_description"),
                    "urdf",
                    "so101_follower.urdf.xacro",
                ]
            ),
        ]
    )
    robot_description = {"robot_description": robot_description_content}

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[robot_description]
    )

    controller_manager = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[
            robot_description,
            os.path.join(pkg_share, "config", "so101_controllers.yaml"),
        ],
        output="screen",
    )

    return LaunchDescription([
        robot_state_publisher,
        controller_manager,
    ]) 