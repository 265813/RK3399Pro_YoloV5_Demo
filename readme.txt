code
├── Algorithm                 # 算法工具模块
│   └── posePoint.py          # 人体姿态关键点检测算法
├── img                       # UI界面图片资源（背景、按钮图标、logo）
├── lib                       # 底层核心库文件
│   ├── serialServer.py       # 串口驱动：灯光、风扇设备控制
│   ├── speech_recognition.py # 离线语音识别
│   ├── yolov5_rknn_detect.py # RKNN模型推理与后处理
│   ├── FingerModule.py       # 指纹识别驱动
│   ├── FingerPrintDecode/Encode.py # 指纹数据编解码
│   └── 各类工具类与动态库
├── microphone                # 麦克风音频采集与预处理
├── speech                    # 离线TTS语音合成、音频播报
├── voice_interactive_assistant # 本地AI语音对话模块
├── Model                     # 已量化完成的RKNN部署模型
│   ├── class.rknn            # 学生课堂行为检测模型
│   ├── smoke.rknn            # 驾驶员危险行为检测模型
│   └── fall.rknn             # 人体跌倒检测模型
└── app.py                    # 项目主入口，UI界面+所有功能调度


