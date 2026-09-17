# ros2_vision_speech

一个基于 ROS 2 的视觉识别与语音播报示例项目。项目通过摄像头采集图像，使用 YOLO / YOLOv8-Pose 做目标或人体姿态检测，再结合大模型分析、状态追踪和 TTS 语音播报，实现基础的智能看护与视觉语音交互流程。

## 功能概览

- 摄像头采集：从本机摄像头读取画面并发布到 ROS 2 图像话题。
- 目标识别：使用 YOLOv8 对画面中的目标进行检测。
- 姿态检测：使用 YOLOv8-Pose 识别人、人体框、关键点和站立 / 坐姿 / 躺倒状态。
- 异常追踪：根据姿态持续时间和区域规则判断摔倒、进入危险区域、区域久留等事件。
- 大模型分析：调用 SiliconFlow 兼容 OpenAI SDK 的接口，对检测结果和图像进行自然语言分析。
- 语音播报：使用 `pyttsx3` 将分析结果播报出来。
- 画面显示：使用 OpenCV 显示实时画面，并叠加最新播报文本。

## 项目结构

```text
ros2_vision_speech/
├── launch/
│   └── vision_speech.launch.py        # 一键启动主要节点
├── ros2_vision_speech/
│   ├── camera_node.py                 # 摄像头采集节点
│   ├── detection_node.py              # YOLO 目标检测节点
│   ├── pose_detection_node.py         # YOLOv8-Pose 姿态检测节点
│   ├── state_tracker_node.py          # 异常状态追踪节点
│   ├── analysis_node.py               # 大模型图像分析节点
│   ├── tts_node.py                    # 语音播报节点
│   └── display_node.py                # 画面显示节点
├── package.xml
├── setup.py
└── setup.cfg
```

## 节点与话题

| 节点 | 订阅话题 | 发布话题 | 说明 |
| --- | --- | --- | --- |
| `camera_node` | 无 | `/image_raw` | 读取本机默认摄像头并发布 `sensor_msgs/Image` |
| `detection_node` | `/image_raw` | `/detections` | YOLOv8 普通目标检测，输出检测标签和图像 base64 |
| `pose_detection_node` | `/image_raw` | `/pose_detections` | YOLOv8-Pose 人体姿态检测 |
| `state_tracker_node` | `/pose_detections` | `/anomaly_events` | 根据姿态和 ROI 区域生成异常事件 |
| `analysis_node` | `/detections` | `/speech_text` | 调用大模型生成播报文本 |
| `tts_node` | `/speech_text` | 无 | 将文本转为语音播报 |
| `display_node` | `/image_raw`, `/speech_text` | 无 | 显示摄像头画面并叠加文本 |

> 注意：当前 `launch/vision_speech.launch.py` 启动的是 `pose_detection_node` 和 `state_tracker_node`，但 `analysis_node` 仍订阅旧的 `/detections` 话题。因此使用 launch 文件启动时，`analysis_node` 默认不会收到 `/anomaly_events`。如果要走“异常事件 -> 大模型分析 -> 语音播报”链路，需要将 `analysis_node` 改为订阅 `/anomaly_events`，或额外启动 `detection_node` 产生 `/detections`。

## 环境要求

- ROS 2 Humble 或其他支持 `ament_python` 的 ROS 2 版本
- Python 3.10+
- 可用摄像头设备
- OpenCV / cv_bridge 运行环境
- Python 依赖：
  - `ultralytics`
  - `openai`
  - `pyttsx3`
  - `opencv-python`

ROS 2 依赖在 `package.xml` 中声明：

- `rclpy`
- `std_msgs`
- `sensor_msgs`

## 安装依赖

在 ROS 2 工作空间中安装 Python 依赖：

```bash
pip install ultralytics openai pyttsx3 opencv-python
```

如果系统缺少 `cv_bridge`，请使用 ROS 2 包管理方式安装，例如 Ubuntu / ROS 2 Humble：

```bash
sudo apt install ros-humble-cv-bridge
```

## 配置 API Key

`analysis_node` 使用 SiliconFlow 的 OpenAI 兼容接口，需要设置环境变量：

```bash
export SILICONFLOW_API_KEY="你的 API Key"
```

Windows PowerShell 示例：

```powershell
$env:SILICONFLOW_API_KEY="你的 API Key"
```

如不使用大模型分析功能，可以不启动 `analysis_node`。

## 构建

将本包放在 ROS 2 工作空间的 `src` 目录下，例如：

```text
ros2_ws/
└── src/
    └── ros2_vision_speech/
```

在工作空间根目录执行：

```bash
colcon build --packages-select ros2_vision_speech
source install/setup.bash
```

Windows PowerShell：

```powershell
colcon build --packages-select ros2_vision_speech
.\install\setup.ps1
```

## 运行

### 一键启动

```bash
ros2 launch ros2_vision_speech vision_speech.launch.py
```

该 launch 文件会启动：

- `camera_node`
- `pose_detection_node`
- `state_tracker_node`
- `analysis_node`
- `tts_node`
- `display_node`

### 分别启动节点

摄像头采集：

```bash
ros2 run ros2_vision_speech camera_node
```

普通目标检测：

```bash
ros2 run ros2_vision_speech detection_node
```

姿态检测：

```bash
ros2 run ros2_vision_speech pose_detection_node
```

异常状态追踪：

```bash
ros2 run ros2_vision_speech state_tracker_node
```

大模型分析：

```bash
ros2 run ros2_vision_speech analysis_node
```

语音播报：

```bash
ros2 run ros2_vision_speech tts_node
```

画面显示：

```bash
ros2 run ros2_vision_speech display_node
```

## 典型数据流

### 普通目标识别与播报链路

```text
camera_node
  -> /image_raw
  -> detection_node
  -> /detections
  -> analysis_node
  -> /speech_text
  -> tts_node / display_node
```

### 姿态检测与异常事件链路

```text
camera_node
  -> /image_raw
  -> pose_detection_node
  -> /pose_detections
  -> state_tracker_node
  -> /anomaly_events
```

## 场景配置

异常区域规则在 `ros2_vision_speech/state_tracker_node.py` 的 `ROI_ZONES` 中配置：

```python
ROI_ZONES = {
    'kitchen': {'box': (0, 0, 200, 200), 'type': 'immediate', 'threshold_sec': 0},
    'bathroom': {'box': (400, 0, 640, 240), 'type': 'duration', 'threshold_sec': 300},
}
```

- `box`：区域坐标 `(x1, y1, x2, y2)`，对应图像像素坐标。
- `type='immediate'`：进入区域立即报警。
- `type='duration'`：进入区域并停留超过 `threshold_sec` 后报警。

摔倒判断阈值在 `ros2_vision_speech/pose_detection_node.py` 和 `ros2_vision_speech/state_tracker_node.py` 中配置，可根据摄像头安装角度、画面分辨率和实际场景微调。

## 常见问题

### 摄像头打不开

`camera_node` 默认使用 `cv2.VideoCapture(0)` 打开本机 0 号摄像头。如果有多个摄像头，可以修改 `ros2_vision_speech/camera_node.py` 中的设备编号。

### 首次运行 YOLO 很慢

`ultralytics` 首次加载 `yolov8n.pt` 或 `yolov8n-pose.pt` 时可能会自动下载模型文件。请确认运行环境可以访问模型下载地址，或提前将模型文件放到运行目录。

### 没有语音输出

请检查系统是否安装并配置了可用 TTS 引擎。`tts_node` 会优先尝试选择中文语音，如果系统没有中文 voice，会使用默认 voice。

### 大模型没有输出

请确认已设置 `SILICONFLOW_API_KEY`，并且 `analysis_node` 订阅的话题有数据。当前代码中 `analysis_node` 订阅 `/detections`，需要启动 `detection_node` 才能收到输入。

## 开发提示

- 使用 `ros2 topic list` 查看当前话题。
- 使用 `ros2 topic echo /detections` 查看目标检测输出。
- 使用 `ros2 topic echo /pose_detections` 查看姿态检测输出。
- 使用 `ros2 topic echo /anomaly_events` 查看异常事件输出。
- 使用 `ros2 topic echo /speech_text` 查看待播报文本。

