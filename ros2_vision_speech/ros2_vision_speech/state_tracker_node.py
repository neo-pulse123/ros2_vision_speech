import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from collections import deque
import json, time

# ========== 场景配置：按你实际的房间布局和摄像头分辨率修改 ==========
# 坐标为像素坐标 (x1, y1, x2, y2)，对应 /image_raw 的分辨率
# type='immediate'  -> 进入即报警（比如灶台、楼梯口这类瞬时危险区）
# type='duration'   -> 停留超过 threshold_sec 才报警（比如卫生间久留）
ROI_ZONES = {
    'kitchen': {'box': (0, 0, 200, 200), 'type': 'immediate', 'threshold_sec': 0},
    'bathroom': {'box': (400, 0, 640, 240), 'type': 'duration', 'threshold_sec': 300},
}

FALL_CONFIRM_WINDOW_SEC = 3.0   # 姿态持续"lying"超过该时长才确认摔倒，避免单帧误判
FALL_MIN_SAMPLES = 3            # 窗口内至少要有几帧支持才算数
HISTORY_WINDOW_SEC = 10.0       # 滑动窗口保留的历史时长


class StateTrackerNode(Node):
    def __init__(self):
        super().__init__('state_tracker_node')
        self.subscription = self.create_subscription(
            String, '/pose_detections', self.detection_callback, 10)
        self.publisher_ = self.create_publisher(String, '/anomaly_events', 10)

        self.history = deque()          # (timestamp, posture)
        self.zone_enter_time = {}       # zone_name -> 首次进入该区域的时间
        self.fall_alerted = False       # 边沿触发：确认摔倒后不重复报警，直到姿态恢复正常
        self.zone_alerted = set()       # 已经报过警的 zone，避免持续刷屏

        self.get_logger().info('状态追踪节点已启动')

    def detection_callback(self, msg):
        try:
            payload = json.loads(msg.data)
            persons = payload['persons']
            img_b64 = payload['image_b64']
        except Exception as e:
            self.get_logger().error(f'解析失败: {e}')
            return

        if not persons:
            self._reset_zone_state()
            return

        # 演示场景假设画面中主要看护对象是面积最大的人体框；
        # 多人同框场景需要换成带ID的多目标追踪，先不在这版范围内
        main_person = max(
            persons, key=lambda p: (p['bbox'][2] - p['bbox'][0]) * (p['bbox'][3] - p['bbox'][1])
        )

        now = time.time()
        self.history.append((now, main_person['posture']))
        self._trim_history(now)

        self._check_fall(now, main_person, img_b64)
        self._check_zones(now, main_person, img_b64)

    def _trim_history(self, now):
        while self.history and now - self.history[0][0] > HISTORY_WINDOW_SEC:
            self.history.popleft()

    def _check_fall(self, now, person, img_b64):
        recent = [(t, p) for t, p in self.history if now - t <= FALL_CONFIRM_WINDOW_SEC]
        lying_count = sum(1 for _, p in recent if p == 'lying')

        if len(recent) >= FALL_MIN_SAMPLES and lying_count == len(recent):
            if not self.fall_alerted:
                self.fall_alerted = True
                self._publish_event('fall', 'high', None, person, img_b64,
                                     f'检测到持续 {FALL_CONFIRM_WINDOW_SEC}s 以上的躺倒姿态，疑似摔倒')
        else:
            if person['posture'] != 'lying':
                self.fall_alerted = False  # 姿态恢复正常，重新允许下一次报警

    def _check_zones(self, now, person, img_b64):
        cx, cy = person['center']

        for zone_name, cfg in ROI_ZONES.items():
            x1, y1, x2, y2 = cfg['box']
            inside = x1 <= cx <= x2 and y1 <= cy <= y2

            if inside:
                if zone_name not in self.zone_enter_time:
                    self.zone_enter_time[zone_name] = now

                duration = now - self.zone_enter_time[zone_name]

                if cfg['type'] == 'immediate' and zone_name not in self.zone_alerted:
                    self.zone_alerted.add(zone_name)
                    self._publish_event('zone_enter', 'medium', zone_name, person, img_b64,
                                         f'进入危险区域「{zone_name}」')
                elif cfg['type'] == 'duration' and duration > cfg['threshold_sec'] \
                        and zone_name not in self.zone_alerted:
                    self.zone_alerted.add(zone_name)
                    self._publish_event('zone_stay', 'medium', zone_name, person, img_b64,
                                         f'在「{zone_name}」停留超过 {cfg["threshold_sec"]}s')
            else:
                self.zone_enter_time.pop(zone_name, None)
                self.zone_alerted.discard(zone_name)

    def _reset_zone_state(self):
        # 画面中暂时没检测到人，清空区域状态；fall_alerted 不清，避免人短暂出画面导致重复报警
        self.zone_enter_time.clear()
        self.zone_alerted.clear()

    def _publish_event(self, event, risk_level, zone, person, img_b64, description):
        payload = json.dumps({
            'event': event,
            'risk_level': risk_level,
            'zone': zone,
            'posture': person['posture'],
            'bbox': person['bbox'],
            'image_b64': img_b64,
            'description': description,
            'timestamp': time.time(),
        })
        self.publisher_.publish(String(data=payload))
        self.get_logger().warn(f'[异常事件] {description}')


def main(args=None):
    rclpy.init(args=args)
    node = StateTrackerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
