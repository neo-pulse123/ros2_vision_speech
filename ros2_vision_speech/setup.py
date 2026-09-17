import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'ros2_vision_speech'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
    (
        'share/ament_index/resource_index/packages',
        ['resource/ros2_vision_speech']
    ),
    (
        'share/ros2_vision_speech',
        ['package.xml']
    ),
    (
        os.path.join('share', 'ros2_vision_speech', 'launch'),
        glob('launch/*.launch.py')
    ),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ubuntu',
    maintainer_email='ubuntu@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'camera_node = ros2_vision_speech.camera_node:main',
            'pose_detection_node = ros2_vision_speech.pose_detection_node:main',
            'state_tracker_node = ros2_vision_speech.state_tracker_node:main',
            'analysis_node = ros2_vision_speech.analysis_node:main',
            'tts_node = ros2_vision_speech.tts_node:main',
            'display_node = ros2_vision_speech.display_node:main',
        ],
    },
)