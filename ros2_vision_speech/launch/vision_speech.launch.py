from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([

        Node(
            package='ros2_vision_speech',
            executable='camera_node',
            name='camera_node',
            output='screen'
        ),

        Node(
            package='ros2_vision_speech',
            executable='pose_detection_node',
            name='pose_detection_node',
            output='screen'
        ),

        Node(
            package='ros2_vision_speech',
            executable='state_tracker_node',
            name='state_tracker_node',
            output='screen'
        ),

        # 注意：analysis_node 目前订阅的是旧的 /detections 话题，
        # pose_detection_node/state_tracker_node 上线后需要把它改成订阅
        # /anomaly_events 才能收到摔倒/区域报警事件（这是第4步要做的事）。
        Node(
            package='ros2_vision_speech',
            executable='analysis_node',
            name='analysis_node',
            output='screen'
        ),

        Node(
            package='ros2_vision_speech',
            executable='tts_node',
            name='tts_node',
            output='screen'
        ),
        Node(
            package='ros2_vision_speech',
            executable='display_node',
            name='display_node',
            output='screen'
        ),

    ])