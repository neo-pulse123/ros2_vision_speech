# ros2_vision_speech/display_node.py

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import cv2

class DisplayNode(Node):
    def __init__(self):
        super().__init__('display_node')
        self.bridge = CvBridge()
        self.latest_text = ''

        self.create_subscription(Image, '/image_raw', self.image_callback, 10)
        self.create_subscription(String, '/speech_text', self.text_callback, 10)
        self.get_logger().info('显示节点已启动')

    def text_callback(self, msg):
        self.latest_text = msg.data#保存最新的文字内容

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')#ros转opencv

        # 底部加一条半透明黑色背景条
        if self.latest_text:
            overlay = frame.copy()#复制原始图像
            h, w = frame.shape[:2]
            cv2.rectangle(overlay, (0, h - 60), (w, h), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

            cv2.putText(#字幕
                frame,
                self.latest_text,
                (12, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 180),
                2,
                cv2.LINE_AA
            )

        cv2.imshow('ROS2 视觉识别', frame)#窗口名称
        cv2.waitKey(1)#等1ms，让窗口更新显示，处理键盘事件避免阻塞

    def destroy_node(self):
        cv2.destroyAllWindows()#opencv窗口是独立资源，不受python垃圾回收控制，要手动删除
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = DisplayNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()