# 基于 YOLOv5 与 AI 语音交互的多场景人体行为检测系统

[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.7+-blue)](https://www.python.org/)
[![YOLOv5](https://img.shields.io/badge/YOLOv5-6.0-red)](https://github.com/ultralytics/yolov5)
[![RK3399Pro](https://img.shields.io/badge/RK3399Pro-NPU-orange)](https://www.rock-chips.com/)

**中国大学生计算机设计大赛  · 边缘人工智能挑战赛作品**  


基于 **YOLOv5** 算法与 **RK3399Pro** 边缘计算平台的多场景人体行为检测系统。集成驾驶员行为识别、跌倒检测、学生课堂行为检测三大场景，结合 **DeepSeek 大模型** 实现 AI 语音交互，支持语音及 QT 界面双通道智能硬件控制。

---

## 📋 作品简介

本作品基于 YOLOv5 算法实现驾驶员行为识别、跌倒检测及学生课堂行为检测，结合大语言模型实现 AI 语音交互，可语音控制智能设备和体温检测及指纹识别。系统具备多场景检测能力，可广泛应用于交通、养老、教育等领域。

---

## 🎯 核心功能

| 功能模块 | 场景 | 说明 |
|---------|------|------|
| **驾驶员行为检测** | 交通 | 10种行为识别（打电话、发短信、喝水、操作收音机等） |
| **跌倒检测** | 养老 | 老人跌倒实时识别与告警 |
| **学生课堂行为检测** | 教育 | 5种行为识别（喝水、听讲、玩手机、发呆、写字） |
| **AI语音交互** | 全场景 | 基于DeepSeek大模型的智能问答与语音播报 |
| **智能硬件控制** | 全场景 | 语音+QT界面双通道控制指示灯、风扇、测温、指纹模块 |

---

## 🏆 作品创新点

| 创新维度 | 技术内容 |
|---------|---------|
| **多阶段模型优化** | CBAM注意力机制 + pre-BiFPN特征金字塔 + SPPF轻量化 |
| **边缘端部署** | PyTorch → ONNX → RKNN 跨平台转换，INT8量化，NPU加速 |
| **多模态交互** | DeepSeek API + Edge-TTS 语音合成，Markdown符号过滤 |
| **双通道控制** | 语音控制 + QT界面按钮控制，异构协议统一管理 |

---

## 📊 模型性能

| 检测场景 | 数据集规模 | mAP@0.5 | 推理延迟 |
|---------|-----------|---------|---------|
| 驾驶员行为 | 3198张 | 0.993 | <15ms |
| 跌倒检测 | 2040张 | 0.995 | <15ms |
| 学生课堂行为 | 3000张 | 0.945 | <15ms |

---

## 🔧 硬件平台

| 硬件 | 型号 | 功能 |
|-----|------|------|
| 核心开发板 | NLE-AI800 (RK3399Pro) | 4.0Tops NPU加速 |
| 摄像头 | 高清USB摄像头 | 视频采集 |
| 麦克风阵列 | 科大讯飞6麦 | 声源定位、语音采集 |
| 指纹模块 | 电容式 | 指纹识别 |
| 测温模块 | 红外 | 体温检测 |
| 指示灯 | RGB三色 | 状态指示 |
| 风扇 | 5V | 散热控制 |

---

## 📦 软件架构

- **code/**
  - **Algorithm/** - 算法工具模块
    - posePoint.py - 人体姿态关键点检测算法
  - **img/** - UI界面图片资源（背景、按钮图标、logo）
  - **lib/** - 底层核心库文件
    - serialServer.py - 串口驱动：灯光、风扇设备控制
    - speech_recognition.py - 离线语音识别
    - yolov5_rknn_detect.py - RKNN模型推理与后处理
    - FingerModule.py - 指纹识别驱动
    - FingerPrintDecode.py - 指纹数据解码
    - FingerPrintEncode.py - 指纹数据编码
  - **microphone/** - 麦克风音频采集与预处理
  - **speech/** - 离线TTS语音合成、音频播报
  - **voice_interactive_assistant/** - 本地AI语音对话模块
  - **Model/** - 已量化完成的RKNN部署模型
    - class.rknn - 学生课堂行为检测模型
    - smoke.rknn - 驾驶员危险行为检测模型
    - fall.rknn - 人体跌倒检测模型
  - app.py - 项目主入口，UI界面+所有功能调度

---

