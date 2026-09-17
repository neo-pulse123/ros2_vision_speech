import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
from ultralytics import YOLO
import json, cv2, base64, math

# COCO 17 关键点索引（YOLOv8-Pose 输出顺序）
KP_LEFT_SHOULDER, KP_RIGHT_SHOULDER = 5, 6
KP_LEFT_HIP, KP_RIGHT_HIP = 11, 12

# 判定阈值——先用这组默认值跑通，再根据你摄像头的实际安装角度和高度微调
ANGLE_LYING_THRESHOLD = 55.0        # 躯干与竖直方向夹角(度)，超过视为"躺/倒地"倾向
ASPECT_RATIO_LYING_THRESHOLD = 1.3  # 人体框 宽/高，超过视为"躺/倒地"倾向（关键点不可靠时的兜底）
KEYPOINT_CONF_THRESHOLD = 0.5


class PoseDetectionNode(Node):
    def __init__(self):
        super().__init__('pose_detection_node')
        self.subscription = self.create_subscription(
            Image, '/image_raw', self.image_callback, 10)
        self.publisher_ = self.create_publisher(String, '/pose_detections', 10)
        self.bridge = CvBridge()
        self.model = YOLO('yolov8n-pose.pt')  # 自动下载，CPU可运行
        self.frame_count = 0
        self.get_logger().info('姿态检测节点已启动')

    def image_callback(self, msg):
        # 每5帧检测一次，减少CPU压力
        self.frame_count += 1
        if self.frame_count % 5 != 0:
            return

        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        results = self.model(frame, verbose=False)

        persons = []
        for result in results:
            if result.keypoints is None or result.boxes is None:
                continue
            boxes = result.boxes
            kpts_all = result.keypoints.data  # (N, 17, 3) -> x, y, conf

            for i in range(len(boxes)):
                cls_id = int(boxes.cls[i])
                if self.model.names[cls_id] != 'person':
                    continue
                conf = float(boxes.conf[i])
                if conf < 0.5:
                    continue

                x1, y1, x2, y2 = boxes.xyxy[i].tolist()
                w, h = x2 - x1, y2 - y1
                aspect_ratio = w / h if h > 0 else 0

                kpts = kpts_all[i]
                posture, angle = self._classify_posture(kpts, aspect_ratio)

                persons.append({
                    'bbox': [round(x1), round(y1), round(x2), round(y2)],
                    'center': [round((x1 + x2) / 2), round((y1 + y2) / 2)],
                    'aspect_ratio': round(aspect_ratio, 2),
                    'torso_angle': round(angle, 1) if angle is not None else None,
                    'posture': posture,
                    'confidence': round(conf, 2),
                })

        if persons:
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            img_b64 = base64.b64encode(buffer).decode('utf-8')

            payload = json.dumps({
                'persons': persons,
                'image_b64': img_b64,
            })
            self.publisher_.publish(String(data=payload))
            postures = [p['posture'] for p in persons]
            self.get_logger().info(f'检测到 {len(persons)} 人，姿态: {postures}')

    def _classify_posture(self, kpts, aspect_ratio):
        """基于肩-髋连线与竖直方向的夹角 + 人体框宽高比 判断姿态"""
        ls, rs = kpts[KP_LEFT_SHOULDER], kpts[KP_RIGHT_SHOULDER]
        lh, rh = kpts[KP_LEFT_HIP], kpts[KP_RIGHT_HIP]

        valid = all(p[2] > KEYPOINT_CONF_THRESHOLD for p in (ls, rs, lh, rh))
        if not valid:
            # 关键点置信度不足（比如侧躺被遮挡），退化为只用宽高比判断
            if aspect_ratio > ASPECT_RATIO_LYING_THRESHOLD:
                return 'lying', None
            return 'unknown', None

        shoulder_mid = ((ls[0] + rs[0]) / 2, (ls[1] + rs[1]) / 2)
        hip_mid = ((lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2)

        dx = hip_mid[0] - shoulder_mid[0]
        dy = hip_mid[1] - shoulder_mid[1]
        # 竖直向下为基准方向；夹角越接近90度说明身体越接近水平
        angle = math.degrees(math.atan2(abs(dx), abs(dy) + 1e-6))

        if angle > ANGLE_LYING_THRESHOLD or aspect_ratio > ASPECT_RATIO_LYING_THRESHOLD:
            return 'lying', angle
        elif angle < 25:
            return 'standing', angle
        else:
            return 'sitting', angle


def main(args=None):
    rclpy.init(args=args)
    node = PoseDetectionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
