import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
from ultralytics import YOLO
import json, cv2, base64

class DetectionNode(Node):
    def __init__(self):
        super().__init__('detection_node')
        self.subscription = self.create_subscription(
            Image, '/image_raw', self.image_callback, 10)
        self.publisher_ = self.create_publisher(String, '/detections', 10)
        self.bridge = CvBridge()
        self.model = YOLO('yolov8n.pt')  # 自动下载，CPU可运行
        self.frame_count = 0
        self.get_logger().info('识别节点已启动')

    def image_callback(self, msg):
        # 每5帧识别一次，减少CPU压力
        self.frame_count += 1
        if self.frame_count % 5 != 0:
            return

        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')#把image消息转换为opencv可以处理的格式
        results = self.model(frame, verbose=False)#调用yolo模型对图像进行推理

        detections = []
        for result in results:
            for box in result.boxes:
                label = self.model.names[int(box.cls)]#类别转换，把类别id转成类别名称
                confidence = float(box.conf)#box.conf置信度，
                if confidence > 0.5:
                    detections.append({
                        'label': label,
                        'confidence': round(confidence, 2)
                    })

        if detections:
            # 同时把图像编码为base64供analysis_node使用
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])#图像压缩为jpeg
            img_b64 = base64.b64encode(buffer).decode('utf-8')#二进制转base64编码

            payload = json.dumps({
                'detections': detections,
                'image_b64': img_b64
            })#json格式
            self.publisher_.publish(String(data=payload))
            self.get_logger().info(f'检测到: {[d["label"] for d in detections]}')

def main(args=None):
    rclpy.init(args=args)
    node = DetectionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()