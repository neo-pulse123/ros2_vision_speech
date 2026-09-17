import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import openai, json, base64, time, os


class AnalysisNode(Node):
    def __init__(self):
        super().__init__('analysis_node')
        self.subscription = self.create_subscription(
            String, '/detections', self.detection_callback, 10)
        self.publisher_ = self.create_publisher(String, '/speech_text', 10)

        api_key = os.environ.get('SILICONFLOW_API_KEY', '')
        if not api_key:
            self.get_logger().error('未找到 SILICONFLOW_API_KEY 环境变量！')

        self.client = openai.OpenAI(
            api_key=api_key,
            base_url='https://api.siliconflow.cn/v1'
        )
        self.model = 'Qwen/Qwen3-235B-A22B'  # 可按需换成 Qwen/Qwen3-7B 等
        self.last_call_time = 0
        self.cooldown = 5.0  # 两次API调用最少间隔5秒
        self.get_logger().info(f'分析节点已启动，模型：{self.model}')

    def detection_callback(self, msg):
        now = time.time()
        if now - self.last_call_time < self.cooldown:
            return
        self.last_call_time = now

        try:
            payload = json.loads(msg.data)
            detections = payload['detections']
            img_b64 = payload['image_b64']
        except Exception as e:
            self.get_logger().error(f'解析失败: {e}')
            return

        labels = [d['label'] for d in detections]
        self.get_logger().info(f'调用模型分析: {labels}')

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=200,
                extra_body={'thinking': {'type': 'disabled'}},  # 关闭thinking，直接输出结果
                messages=[
                    {
                        'role': 'system',
                        'content': (
                            '你是一个智能家居助手，输出格式严格为：'
                            '检测到[目标]，状态[状态描述]，建议[行动建议]。'
                            '只输出这一句话，不要任何其他内容，不要思考过程。'
                        )
                    },
                    {
                        'role': 'user',
                        'content': [
                            {
                                'type': 'image_url',
                                'image_url': {
                                    'url': f'data:image/jpeg;base64,{img_b64}'
                                }
                            },
                            {
                                'type': 'text',
                                'text': (
                                    f'YOLOv8识别到了：{labels}。\n'
                                    '请观察图像描述目标的当前状态并给出建议。\n'
                                    '例如：检测到人，状态玩手机，建议不要打扰。'
                                )
                            }
                        ]
                    }
                ]
            )
            speech_text = response.choices[0].message.content.strip()
            self.get_logger().info(f'模型输出: {speech_text}')
            self.publisher_.publish(String(data=speech_text))

        except Exception as e:
            self.get_logger().error(f'API调用错误: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = AnalysisNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()