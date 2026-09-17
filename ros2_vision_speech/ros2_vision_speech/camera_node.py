import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')
        self.publisher_ = self.create_publisher(Image, '/image_raw', 10)#创建一个发布者，发布消息类型Image，发布到话题/image_raw，队列大小10,最多缓存十条消息
        self.timer = self.create_timer(0.1, self.timer_callback)  # 定时器，每0.1秒触发一次timer_callback
        self.bridge = CvBridge()#opencv与ros之间的桥接器，将opencv的图像转成ros的消息
        self.cap = cv2.VideoCapture(0)#打开摄像头
        self.get_logger().info('摄像头节点已启动')

    def timer_callback(self):
        ret, frame = self.cap.read()#ret是否成功读取到图像，frame读取到的图像数据
        if ret:#如果读取到图像，将opencv格式的图像转成ros的image消息格式
            msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
            self.publisher_.publish(msg)#将转换后的消息发布到/image_raw话题下，订阅了该话题的所有节点都会收到这张图片

    def destroy_node(self):
        self.cap.release()#销毁时要释放摄像头
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()