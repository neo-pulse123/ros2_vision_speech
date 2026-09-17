import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import pyttsx3
import threading

class TtsNode(Node):
    def __init__(self):
        super().__init__('tts_node')
        self.subscription = self.create_subscription(
            String, '/speech_text', self.speech_callback, 10)
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 160)   # 语速
        self.engine.setProperty('volume', 0.9) # 音量
        # 尝试设置中文声音（若系统有的话）
        voices = self.engine.getProperty('voices')
        for v in voices:
            if 'zh' in v.id.lower() or 'chinese' in v.name.lower():
                self.engine.setProperty('voice', v.id)
                break
        self.lock = threading.Lock()
        self.get_logger().info('语音节点已启动')

    def speech_callback(self, msg):
        text = msg.data
        self.get_logger().info(f'播报: {text}')
        # 单独线程播报，避免阻塞ROS2回调
        threading.Thread(target=self._speak, args=(text,), daemon=True).start()#每次播报都是一个独立的线程

    def _speak(self, text):#播报函数
        with self.lock:#线程锁
            self.engine.say(text)
            self.engine.runAndWait()#阻塞等待

def main(args=None):
    rclpy.init(args=args)
    node = TtsNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()