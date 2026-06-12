# Multi-Scenario Human Behavior Detection System Based on YOLOv5 and AI Voice Interaction

[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.7+-blue)](https://www.python.org/)
[![YOLOv5](https://img.shields.io/badge/YOLOv5-6.0-red)](https://github.com/ultralytics/yolov5)
[![RK3399Pro](https://img.shields.io/badge/RK3399Pro-NPU-orange)](https://www.rock-chips.com/)

**China Collegiate Computing Competition 2025 · Edge Artificial Intelligence Challenge**  

A multi-scenario human behavior detection system based on **YOLOv5** algorithm and **RK3399Pro** edge computing platform. Integrates three major scenarios: driver behavior recognition, fall detection, and student classroom behavior detection, combined with **DeepSeek LLM** for AI voice interaction, supporting dual-channel intelligent hardware control via voice and QT interface.

---

## 📋 Introduction

This work implements driver behavior recognition, fall detection, and student classroom behavior detection based on the YOLOv5 algorithm, combined with large language models for AI voice interaction, enabling voice control of smart devices, temperature measurement, and fingerprint recognition. The system possesses multi-scenario detection capabilities and can be widely applied in transportation, elderly care, education, and other fields.

---

## 🎯 Core Features

| Feature Module | Scenario | Description |
|---------------|----------|-------------|
| **Driver Behavior Detection** | Transportation | 10 types of behavior recognition (phone calling, texting, drinking, radio operation, etc.) |
| **Fall Detection** | Elderly Care | Real-time fall recognition and alert for the elderly |
| **Student Classroom Behavior Detection** | Education | 5 types of behavior recognition (drinking, listening, phone playing, dazing, writing) |
| **AI Voice Interaction** | All Scenarios | Intelligent Q&A and voice broadcast based on DeepSeek LLM |
| **Smart Hardware Control** | All Scenarios | Dual-channel control of indicators, fan, temperature measurement, and fingerprint module via voice and QT interface |

---

## 🏆 Innovations

| Innovation Dimension | Technical Content |
|---------------------|-------------------|
| **Multi-stage Model Optimization** | CBAM attention mechanism + pre-BiFPN feature pyramid + SPPF lightweight design |
| **Edge Deployment** | PyTorch → ONNX → RKNN cross-platform conversion, INT8 quantization, NPU acceleration |
| **Multi-modal Interaction** | DeepSeek API + Edge-TTS voice synthesis, Markdown symbol filtering |
| **Dual-channel Control** | Voice control + QT interface button control, unified heterogeneous protocol management |

---

## 📊 Model Performance

| Detection Scenario | Dataset Size | mAP@0.5 | Inference Latency |
|--------------------|--------------|---------|-------------------|
| Driver Behavior | 3198 images | 0.993 | <15ms |
| Fall Detection | 2040 images | 0.995 | <15ms |
| Student Classroom Behavior | 3000 images | 0.945 | <15ms |

---

## 🔧 Hardware Platform

| Hardware | Model | Function |
|----------|-------|----------|
| Core Development Board | NLE-AI800 (RK3399Pro) | 4.0Tops NPU acceleration |
| Camera | HD USB Camera | Video capture |
| Microphone Array | iFLYTEK 6-Mic | Sound source localization, voice capture |
| Fingerprint Module | Capacitive | Fingerprint recognition |
| Temperature Measurement Module | Infrared | Body temperature detection |
| Indicators | RGB Three-color | Status indication |
| Fan | 5V | Heat dissipation control |

---

## 📦 Software Architecture

- **code/**
  - **Algorithm/** - Algorithm utility module
    - posePoint.py - Human pose keypoint detection algorithm
  - **img/** - UI image resources (backgrounds, button icons, logo)
  - **lib/** - Core library files
    - serialServer.py - Serial port driver: light and fan device control
    - speech_recognition.py - Offline speech recognition
    - yolov5_rknn_detect.py - RKNN model inference and post-processing
    - FingerModule.py - Fingerprint recognition driver
    - FingerPrintDecode.py - Fingerprint data decoding
    - FingerPrintEncode.py - Fingerprint data encoding
  - **microphone/** - Microphone audio capture and preprocessing
  - **speech/** - Offline TTS voice synthesis and audio broadcast
  - **voice_interactive_assistant/** - Local AI voice conversation module
  - **Model/** - Quantized RKNN deployment models
    - class.rknn - Student classroom behavior detection model
    - smoke.rknn - Driver dangerous behavior detection model
    - fall.rknn - Human fall detection model
  - app.py - Main project entry, UI interface + all function scheduling

---
