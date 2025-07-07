from setuptools import setup
from setuptools import find_packages
import os
from glob import glob

package_name = 'so101_hw_interface'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(include=[package_name, f"{package_name}.*", 'lerobot', 'lerobot.*']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*')),
        (os.path.join('share', package_name, 'resource'), glob('resource/*.xml')),
        # Install wrapper scripts into lib/<package_name> so ros2 run can locate them
        (os.path.join('lib', package_name), ['scripts/so101_motor_bridge', 'scripts/so101_calibrate', 'scripts/so101_read_steps']),
        ('share/ament_index/resource_index/executables', ['resource/so101_motor_bridge', 'resource/so101_calibrate', 'resource/so101_read_steps']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='hls',
    maintainer_email='hls@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    entry_points={
        'console_scripts': [
            'so101_motor_bridge = so101_hw_interface.motor_bridge:main',
            'so101_calibrate = so101_hw_interface.calibrate_arm:main',
            'so101_read_steps = so101_hw_interface.read_motor_steps:main',
        ],
    },
) 