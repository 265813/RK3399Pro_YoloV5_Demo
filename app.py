# -*- coding: utf-8 -*-
"""
Created on Sun Sep 10 22:08:38 2023

@author: zjy
"""

import threading
import time
from lib.serialServer import NewQuerySerial
from lib.speech_recognition import MicrophoneController

import threading

import cv2
import sys
import time
from PyQt5 import QtCore, QtGui, uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QMessageBox
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt
from mainwindow import Ui_MainWindow
import color
from rknn.api import RKNN
from lib.yolov5_rknn_detect import *
from lib.serialServer import NewQuerySerial
import subprocess
import requests
import json
import re

from threading import Thread
from Anowindow import Ui_AnoWindow
from pydub import AudioSegment
from pydub.playback import play
import os
# from voice_interactive_assistant.long_conversation_assistant import LongConversationAssistant
from lib.serialServer import NewQuerySerial
from lib.speech_recognition import MicrophoneController

os.environ['XDG_RUNTIME_DIR'] = '/tmp/runtime-root'

from PyQt5.QtCore import QProcess

import time
# from lib.serialServer import NewQuerySerial
from lib.serialServer import TempQuerySerial
from lib.FingerModule import FingerPrintDevManager

DEEPSEEK_API_KEY = ""

# 将预测标签画在原图上
# def plot(results,frame):
#     results_ = results.pandas().xyxy[0].to_numpy()
#     for box in results_:
#         x1,y1,x2,y2 = box[:4].astype(int)
#         conf = round(box[4],2)
#         clas = box[6]
#         cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),2)
#         cv2.putText(frame,f'{clas}  {conf}',(x1,y1),cv2.FONT_ITALIC,1,(255,0,0),2)
#     return frame

def setButtonStyle(object, path):
    pixmap = QtGui.QPixmap(QtGui.QImage(path))
    fixpixmap = pixmap.scaled(436, 363, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)
    icon = QtGui.QIcon(fixpixmap)
    object.setIcon(icon)
    object.setIconSize(QtCore.QSize(436, 363))
    object.setStyleSheet("QPushButton{background:rgb(255,255,255,100);}"
                         "QPushButton:hover{color:rgb(100,100,100,120);}")


# 首页面的按钮设计
def setButtonStyle2(object, path):
    pixmap = QtGui.QPixmap(QtGui.QImage(path))
    rounded_pixmap = pixmap.scaled(660, 530, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)
    icon = QtGui.QIcon(rounded_pixmap)
    object.setIcon(icon)
    object.setIconSize(QtCore.QSize(610, 610))
    #！！！！！！！！！！！！！！（重要）
    object.setStyleSheet("QPushButton{background: transparent; border: none;}")       


def setExitButtonStyle(object, path):
    pixmap = QtGui.QPixmap(QtGui.QImage(path))

    fixpixmap = pixmap.scaled(145, 100, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)

    icon = QtGui.QIcon(fixpixmap)

    object.setIcon(icon)
    object.setIconSize(QtCore.QSize(435, 360))

    object.setStyleSheet("QPushButton{background:rgb(255,255,255,100);}"
                         "QPushButton:hover{color:rgb(100,100,100,120);}")


def broadcast(text):
    # 调用语音合成接口的指令
    # tts_cmd = f'cd ./speech/broadcast/bin/ && chmod +x tts_offline_sample' + ' && ./tts_offline_sample {}'.format(text)
    tts_cmd = f'cd ./speech/broadcast/bin/ && chmod +x tts_offline_sample && ./tts_offline_sample "{text}"'
    # 语音合并并获取返回值
    res_content = subprocess.getstatusoutput(tts_cmd)
    # 如果合并成功
    if res_content[0] == 0 and '合并成功' in res_content[1]:
        print('语音合成成功，开始播报!')

        audio_path = "./speech/broadcast/bin/tts_sample.wav"
        audio = AudioSegment.from_wav(audio_path)
        # 调整音频播放速率
        audio = audio.speedup(playback_speed=1.2)  # 设置为1.2倍速
        # 保存处理后的音频文件
        processed_audio_path = "./speech/broadcast/bin/tts_sample_processed.wav"
        audio.export(processed_audio_path, format="wav")

        broadcast_cmd = f'aplay {processed_audio_path} -D plughw:Device'
        subprocess.Popen(broadcast_cmd, shell=True)
    else:
        print('语音合成失败!')


def broadcast2(class_name):
    label_names = {
        "Drink": "驾驶员，喝水要注意前方车辆。",
        "Text-with-left-hand": "驾驶员，开车发短信很危险。",
        "Text-with-right-hand": "驾驶员，开车发短信很危险。",
        "Call-with-left-hand": "驾驶员，开车打电话很危险。",
        "Talking-to-passengers": "驾驶员，和乘客说话注意前方车辆。",
        "Makeup&Fix-hair": "驾驶员，开车整理头发要注意安全。",
        "Safe-driving": "驾驶员，安全驾驶，一路平安。",
        "Operate-radio": "驾驶员，操作收音机别分心。",
        "Reach-behind": "驾驶员，向后拿东西很危险。",
        "Call-with-right-hand": "驾驶员，开车打电话很危险。",
        "smoke": "驾驶员，开车禁止吸烟噢。"
    }

    # 根据类别名称获取对应的播报内容
    broadcast_content = label_names.get(class_name)

    # 输出播报内容
    print(broadcast_content)

    def run():
        tts_cmd = f'cd ./speech/broadcast/bin/ && chmod +x tts_offline_sample && ./tts_offline_sample "{broadcast_content}"'
        res_content = subprocess.getstatusoutput(tts_cmd)
        if res_content[0] == 0 and '合并成功' in res_content[1]:
            print('语音合成成功，开始播报!')
            audio_path = "./speech/broadcast/bin/tts_sample.wav"
            audio = AudioSegment.from_wav(audio_path)
            audio = audio.speedup(playback_speed=1.3)  # 设置为1.2倍速
            processed_audio_path = "./speech/broadcast/bin/tts_sample_processed.wav"
            audio.export(processed_audio_path, format="wav")
            broadcast_cmd = f'aplay {processed_audio_path} -D plughw:Device'
            subprocess.Popen(broadcast_cmd, shell=True)
        else:
            print('语音合成失败!')

    # 在子线程中运行语音播报
    Thread(target=run).start()


def broadcast3(class_name):
    label_names = {
        "Drink": "同学在喝水",
        "Listen": ",",
        "Play_Phone": "警告警告请勿玩手机",
        "Trance": "同学别走神哦",
        "Write": ","
    }

    # 根据类别名称获取对应的播报内容
    broadcast_content = label_names.get(class_name)

    # 输出播报内容
    print(broadcast_content)

    def run():
        tts_cmd = f'cd ./speech/broadcast/bin/ && chmod +x tts_offline_sample && ./tts_offline_sample "{broadcast_content}"'
        res_content = subprocess.getstatusoutput(tts_cmd)
        if res_content[0] == 0 and '合并成功' in res_content[1]:
            print('语音合成成功，开始播报!')
            audio_path = "./speech/broadcast/bin/tts_sample.wav"
            audio = AudioSegment.from_wav(audio_path)
            audio = audio.speedup(playback_speed=1.3)  # 设置为1.2倍速
            processed_audio_path = "./speech/broadcast/bin/tts_sample_processed.wav"
            audio.export(processed_audio_path, format="wav")
            broadcast_cmd = f'aplay {processed_audio_path} -D plughw:Device'
            subprocess.Popen(broadcast_cmd, shell=True)
        else:
            print('语音合成失败!')

    # 在子线程中运行语音播报
    Thread(target=run).start()

def broadcast4(class_name):
    label_names = {
        "right": "蒜苗朝左",
        "left": "大蒜朝右"
    }

    # 根据类别名称获取对应的播报内容
    broadcast_content = label_names.get(class_name)

    # 输出播报内容
    print(broadcast_content)

    def run():
        tts_cmd = f'cd ./speech/broadcast/bin/ && chmod +x tts_offline_sample && ./tts_offline_sample "{broadcast_content}"'
        res_content = subprocess.getstatusoutput(tts_cmd)
        if res_content[0] == 0 and '合并成功' in res_content[1]:
            print('语音合成成功，开始播报!')
            audio_path = "./speech/broadcast/bin/tts_sample.wav"
            audio = AudioSegment.from_wav(audio_path)
            audio = audio.speedup(playback_speed=1.3)  # 设置为1.2倍速
            processed_audio_path = "./speech/broadcast/bin/tts_sample_processed.wav"
            audio.export(processed_audio_path, format="wav")
            broadcast_cmd = f'aplay {processed_audio_path} -D plughw:Device'
            subprocess.Popen(broadcast_cmd, shell=True)
        else:
            print('语音合成失败!')

    # 在子线程中运行语音播报
    Thread(target=run).start()
    

class MainWindows(QMainWindow, Ui_MainWindow):

    def __init__(self):
        # 没有父窗口
        super(MainWindows, self).__init__(None)
        # 设置UI
        self.setupUi(self)
        # 隐藏标题栏
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        # 更新用户界面，包括背景图和按钮样式
        self.UpdateUi()
        # 为界面按钮设置点击事件处理函数
        self.SetButtonConnected()
        self.speech_ctrl_th = None

        self.assistant_process = None  # 用于保存子进程对象
        self.assistant_running = False  # 跟踪助手是否正在运行

        # #打开串口
        # serial_port = '/dev/ttyS0' # 串口位置
        # control = NewQuerySerial(serial_port)
        # control.turn_off_fan()
        # control.turn_off_red()
        # control.turn_off_yellow()
        # control.turn_off_green()
        # time.sleep(0.5)
        self.light_control = NewQuerySerial('/dev/ttyS0')
        # 关闭串口
        # control.close_serial()

    # 为界面按钮设置点击时间处理函数
    def SetButtonConnected(self):
        self.showlocationbutton.pressed.connect(self.ButtonPressed1)
        self.showvirusbutton.pressed.connect(self.ButtonPressed2)
        self.showperiodbutton.pressed.connect(self.ButtonPressed3)
        self.showpestsbutton.pressed.connect(self.ButtonPressed4)
        self.showvoice.pressed.connect(self.ButtonPressed5)
        self.showdeepseek.pressed.connect(self.ButtonPressed6)
        self.newButton1.pressed.connect(self.ButtonPressed7)
        self.newButton2.pressed.connect(self.ButtonPressed8)
        self.exitbutton.pressed.connect(self.ExitButtonPressed)

    # 更新用户界面，包括背景图和按钮样式
    def UpdateUi(self):
        # 设置背景图片
        self.setStyleSheet("#MainWindow{border-image:url(img/icon/background1.PNG);}")
        self.backgroundlable.setPixmap(QtGui.QPixmap("img/icon/background1.PNG"))
        self.backgroundlable.setScaledContents(True)

        setButtonStyle2(self.showvirusbutton, "img/icon/SSS/S11.png")
        setButtonStyle2(self.showperiodbutton, "img/icon/SSS/S22.png")
        setButtonStyle2(self.showpestsbutton, "img/icon/SSS/S33.png")
        setButtonStyle2(self.showlocationbutton, "img/icon/SSS/S44.png")
        setButtonStyle2(self.showvoice, "img/icon/SSS/S55.png")
        setButtonStyle2(self.showdeepseek, "img/icon/SSS/S66.png")
        setButtonStyle2(self.newButton1, "img/icon/SSS/S99.png")
        setButtonStyle2(self.newButton2, "img/icon/SSS/S88.png")
        setExitButtonStyle(self.exitbutton, "img/icon/exit.png")

        self.School.setPixmap(QtGui.QPixmap('img/icon/nle.png'))
        self.School.setStyleSheet("QPushButton{background:rgb(255,255,255,50);}"
                                  "QPushButton:hover{color:rgb(100,100,100,120);}")
        self.School.setScaledContents(True)

        font = QtGui.QFont()
        font.setPointSize(15)
        font.setBold(True)
        self.ShowIPLabel.setFont(font)

    # 第一个按钮的点击事件，打开 VideoWindow1
    def ButtonPressed1(self):
        # 先关闭所有灯光
        control = NewQuerySerial('/dev/ttyS0')
        control.turn_off_red()
        control.turn_off_yellow()
        control.turn_off_green()
        control.close_serial()
        self.showlocationbutton.setEnabled(False)
        self.video_window = VideoWindow1(
            # vid='driver_det.mp4',
            vid=0,
            model_path='./Model/class.rknn',
            label_names=("Drink", "Listen", "Play_Phone", "Trance", "Write"),
            img_size=640
        )  # 创建 VideoWindow1 实例
        self.video_window.ui.showFullScreen()  # 显示 VideoWindow1
        self.showlocationbutton.setEnabled(True)

    # 第二个按钮的点击事件，打开 VideoWindow2
    def ButtonPressed2(self):
        # 先关闭所有灯光
        control = NewQuerySerial('/dev/ttyS0')
        control.turn_off_red()
        control.turn_off_yellow()
        control.turn_off_green()
        control.close_serial()
        self.showvirusbutton.setEnabled(False)
        self.video_window = VideoWindow2(
            vid='driver_det12.mp4',
            # vid=0,
            model_path='./Model/smoke.rknn',
            label_names=("Drink", "Text-with-left-hand", "Text-with-right-hand", "Call-with-left-hand",
                         "Talking-to-passengers", "Makeup&Fix-hair", "Safe-driving", "Operate-radio",
                         "Reach-behind", "Call-with-right-hand", "smoke"),
            img_size=640
        )  # 创建 VideoWindow2 实例
        self.video_window.ui.showFullScreen()  # 显示 VideoWindow2
        self.showvirusbutton.setEnabled(True)

    # 第三个按钮的点击事件，打开 VideoWindow3
    def ButtonPressed3(self):
        # 先关闭所有灯光
        control = NewQuerySerial('/dev/ttyS0')
        control.turn_off_red()
        control.turn_off_yellow()
        control.turn_off_green()
        control.close_serial()
        self.showperiodbutton.setEnabled(False)
        self.video_window = VideoWindow3(
            # vid='driver_det.mp4',
            vid=0,
            model_path='./Model/fall.rknn',
            label_names=("Fall",),
            img_size=640
        )  # 创建 VideoWindow3 实例
        self.video_window.ui.showFullScreen()  # 显示 VideoWindow3
        self.showperiodbutton.setEnabled(True)

    # 第四个按钮的点击事件
    def ButtonPressed4(self):
        # 先关闭所有灯光
        control = NewQuerySerial('/dev/ttyS0')
        control.turn_off_red()
        control.turn_off_yellow()
        control.turn_off_green()
        control.close_serial()
        self.showpestsbutton.setEnabled(False)
        self.Ano_window = AnoWindow()
        self.Ano_window.showFullScreen()
        self.showpestsbutton.setEnabled(True)

    # 第五个按钮的点击事件，语音控制按键
    def ButtonPressed5(self):
        self.showvoice.setEnabled(False)

        # 实例化对象
        speech_ctrl_th = speechControlThread()
        # 启动线程
        speech_ctrl_th.start()
        # # 停止线程
        # speech_ctrl_th.stop()
        self.showvoice.setEnabled(True)

    # 第六个按钮的点击事件，语音助手
    def ButtonPressed6(self):
        self.showdeepseek.setEnabled(False)  # 防重复点击

        if not hasattr(self, 'assistant_process'):  # 首次点击初始化
            self.assistant_process = None

        if self.assistant_process is None:  # 启动
            try:
                self.assistant_process = subprocess.Popen(
                    ["python3", "./voice_interactive_assistant/long_conversation_assistant.py"]
                )
                # broadcast("语音助手已启动")
            except Exception as e:
                print(f"启动失败: {e}")  # 先用print调试
                # broadcast(f"启动失败: {e}")
        else:  # 停止
            self.assistant_process.terminate()
            self.assistant_process = None
            # broadcast("语音助手已停止")
        self.showdeepseek.setEnabled(True)

    # # 第七个按钮的点击事件，打开 VideoWindow1
    # def ButtonPressed7(self):
    #     # 先关闭所有灯光
    #     control = NewQuerySerial('/dev/ttyS0')
    #     control.turn_off_red()
    #     control.turn_off_yellow()
    #     control.turn_off_green()
    #     control.close_serial()
    #     self.showlocationbutton.setEnabled(False)
    #     self.video_window = VideoWindow7(
    #         # vid='driver_det.mp4',
    #         vid=0,
    #         model_path='./Model/class.rknn',
    #         label_names=("left", "right"),
    #         img_size=640
    #     )  # 创建 VideoWindow1 实例
    #     self.video_window.ui.showFullScreen()  # 显示 VideoWindow1
    #     self.showlocationbutton.setEnabled(True)

    # def ButtonPressed7(self):
    #     self.newButton1.setEnabled(False)
    #     # TODO: 在这里写按钮1的功能
    #     print("新按钮1被点击")
    #     self.newButton1.setEnabled(True)

    def ButtonPressed7(self):
        self.newButton1.setEnabled(False)
        print("正在启动 posePoint.py ...")

        try:
            # 运行同目录下的 posePoint.py
            subprocess.run(["python3", "/home/nle/notebook/device/pose_video.py"], check=True)
        except Exception as e:
            print("启动 posePoint.py 失败：", e)

        self.newButton1.setEnabled(True)
    

    # 端口扫描
    # 1️⃣ 执行 nmap 扫描
    def run_nmap(self, target):
        cmd = ["nmap", "-sT", "-T3", "-Pn", target]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout

    # 2️⃣ 调用 DeepSeek 分析
    def analyze_with_ai(self,nmap_output):
        prompt = f"""
    你是一个专业的网络安全分析师。

    请分析以下 nmap 扫描结果，并返回 JSON：

    要求：
    1. 提取所有开放端口
    2. 判断风险等级（低/中/高）
    3. 给出可能问题
    4. 给出修复建议

    返回格式：
    {{
      "ports": [
        {{
          "port": 22,
          "service": "ssh",
          "risk": "中",
          "issue": "",
          "suggestion": ""
        }}
      ],
      "summary": ""
    }}

    nmap结果：
    {nmap_output[:3000]}
    """

        url = "https://api.deepseek.com/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是网络安全专家"},
                {"role": "user", "content": prompt}
            ]
        }

        response = requests.post(url, headers=headers, json=data)
        result = response.json()

        content = result["choices"][0]["message"]["content"]

        # 3️⃣ 提取 JSON（关键！）
        match = re.search(r"\{[\s\S]*\}", content)

        if match:
            return json.loads(match.group())
        else:
            return {"error": "AI返回格式错误", "raw": content}

    def ButtonPressed8(self):
        self.newButton2.setEnabled(False)
        target = "192.168.1.115"  # 改成你要扫的IP
        print("正在扫描...")
        nmap_result = self.run_nmap(target)
        print("扫描完成，AI分析中...")
        analysis = self.analyze_with_ai(nmap_result)
        print(json.dumps(analysis, indent=2, ensure_ascii=False))
        broadcast("端口扫描完成")  # 语音提示
        self.newButton2.setEnabled(True)

    # 响应退出按钮点击，关闭应用程序
    def ExitButtonPressed(self):
        # # 关闭所有灯光
        # control = NewQuerySerial('/dev/ttyS0')
        # control.turn_off_red()
        # control.turn_off_yellow()
        # control.turn_off_green()
        # control.close_serial()
        self.light_control.turn_off_all()  # 需要添加这个方法
        self.light_control.close_serial()
        self.close()  # 关闭主窗口
        sys.exit()  # 退出程序


class VideoWindow1(QMainWindow):
    def __init__(self, vid, model_path, label_names, img_size):
        super(VideoWindow1, self).__init__()
        self.vid = vid
        self.model_path = model_path
        self.label_names = label_names
        self.img_size = img_size
        self.setup_ui()

    def setup_ui(self):
        # 实例化定时器
        self.timer = QtCore.QTimer()
        self.ui = uic.loadUi("main.ui")  # 加载UI文件
        self.w, self.h = self.ui.label.width(), self.ui.label.height()  # 视频显示框宽高
        self.ui.start.clicked.connect(self.detect)  # 若该按键被点击，则调用detect
        self.timer.timeout.connect(self.show)  # 若定时器停止，则调用show()，作用是每隔一定时间从摄像头中取一帧显示
        self.ui.stop.clicked.connect(self.cancel)  # 若该按键被点击，则调用cancel
        self.cap = cv2.VideoCapture()

        # Create RKNN object
        self.rknn = RKNN(verbose=True)
        # Load RKNN model
        ret = self.rknn.load_rknn(self.model_path)
        # init runtime environment
        ret = self.rknn.init_runtime(async_mode=True)

        setExitButtonStyle(self.ui.exitbutton, "img/icon/exit.png")  # 设置退出按钮样式
        # 为界面按钮设置点击事件处理函数
        self.SetButtonConnected()

    def SetButtonConnected(self):
        # self.exitButton.pressed.connect(self.ExitButtonPressed)
        # self.pushButton.clicked.connect(self.load_data)
        self.ui.exitbutton.clicked.connect(self.ExitButtonPressed)

    def detect(self):
        ret = self.cap.open(self.vid)  # 参数是0，表示打开笔记本的内置摄像头，参数如果是视频文件路径则打开视频
        time.sleep(1)
        if ret:
            self.ui.textBrowser.setText("摄像头打开成功！")  # 设置内容，会覆盖之前的内容
            self.ui.textBrowser.append("开始进行检测！")  # 添加内容，不会覆盖之前的内容
            self.timer.start(30)  # 定时器开始计时每隔30ms停止并重新启动定时器

    def show(self):
        ret, frame = self.cap.read()  # 获取新的一帧图片
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # 视频色彩转换回RGB，这样才是现实的颜色

            # ------------人体行为检测-------------
            img, ratio, (dw, dh) = letterbox(frame, new_shape=(self.img_size, self.img_size))
            # 模型预测
            t1 = time.time()
            outputs = self.rknn.inference(inputs=[img])  # 模型推理
            t2 = time.time()
            fps = 1 / (t2 - t1)  # 计算帧率评估模型性能
            self.ui.textBrowser.append(f'fps:{fps}')
            # post process
            input_data = post_process(outputs)
            boxes, classes, scores = yolov5_post_process(input_data, self.img_size)
            # if boxes is not None:
            #     draw(frame, boxes, scores, classes, dw, dh, ratio,self.label_names)
            if boxes is not None:
                detected = False
                for box, clas, score in zip(boxes, classes, scores):
                    # 将类别索引转换为类别名称
                    class_name = self.label_names[clas]
                    # 播报类别和置信度
                    # broadcast(f"检测到 {class_name}，置信度为 {score:.2f}")
                    broadcast3(f"{class_name}")

                    #
                    if class_name in ["Drink", "Play_Phone", "Trance"]:
                        detected = True

                    # 绘制框和标签
                    draw(frame, [box], [score], [clas], dw, dh, ratio, self.label_names)

                # 灯光控制（需要先初始化control对象）
                serial_port = '/dev/ttyS0'
                control = NewQuerySerial(serial_port)
                if detected:
                    control.turn_on_red()
                else:
                    control.turn_off_red()
                control.close_serial()
                # ------------人脸口罩检测-------------
            showImage = QtGui.QImage(frame, frame.shape[1], frame.shape[0], QtGui.QImage.Format_RGB888)
            self.ui.label.setPixmap(QtGui.QPixmap.fromImage(showImage))
            self.ui.label.setScaledContents(True)
        else:
            self.cancel()

    def cancel(self):
        self.ui.textBrowser.setText('已关闭检测！')
        self.ui.label.clear()
        if self.timer.isActive():
            self.timer.stop()
        if self.cap.isOpened():
            self.cap.release()
        control = NewQuerySerial('/dev/ttyS0')
        control.turn_off_red()
        control.close_serial()

    def ExitButtonPressed(self):
        # 关闭所有灯光
        control = NewQuerySerial('/dev/ttyS0')
        control.turn_off_red()
        control.turn_off_yellow()
        control.turn_off_green()
        control.close_serial()
        self.ui.close()  # 关闭当前窗口


class VideoWindow2(QMainWindow):
    #     def motion_detected():
    #         """当检测到运动时调用此函数更新最后一次运动时间"""
    #         global last_motion_time, alarm_triggered, red_light_on
    #         last_motion_time = time.time()

    #         # 如果报警已触发则重置状态
    #         if alarm_triggered:
    #             alarm_triggered = False
    #             red_light_on = False
    #             print("运动恢复! 关闭红灯并重置报警状态")

    #     def check_motion_status():
    #         """定期检查运动状态的线程函数"""
    #         global alarm_triggered, red_light_on

    #         while True:
    #             time.sleep(60)  # 每分钟检查一次

    #             current_time = time.time()
    #             time_since_last_motion = current_time - last_motion_time
    #             eight_hours = 8 * 60 * 60  # 8小时（秒）

    #             # 如果超过8小时无运动且未触发报警
    #             if time_since_last_motion >= eight_hours and not alarm_triggered:
    #                 alarm_triggered = True
    #                 red_light_on = True

    #                 # 触发报警操作
    #                 print("\n[ALARM] 8小时无人运动！")
    #                 print("红灯状态: ON")
    #                 send_alert_message()  # 发送警报消息

    #     def send_alert_message():
    #         """模拟发送警报消息（可替换为实际通知逻辑）"""
    #         # 实际应用中可替换为：
    #         # - 电子邮件（smtplib）
    #         # - 短信（Twilio API）
    #         # - 即时通讯（Slack/钉钉 Webhook）
    #         # - 手机推送（Pushbullet）
    #         print("警报消息: 警告！8小时内未检测到任何运动！")

    #     def start_motion_monitoring():
    #         """启动运动监控线程"""
    #         monitor_thread = threading.Thread(target=check_motion_status)
    #         monitor_thread.daemon = True  # 设置为守护线程
    #         monitor_thread.start()
    #         print("运动监控已启动... (8小时无运动将触发报警)")
    def __init__(self, vid, model_path, label_names, img_size):
        super(VideoWindow2, self).__init__()
        self.vid = vid
        self.model_path = model_path
        self.label_names = label_names
        self.img_size = img_size
        self.setup_ui()

    def setup_ui(self):
        # 实例化定时器
        self.timer = QtCore.QTimer()
        self.ui = uic.loadUi("main.ui")  # 加载UI文件
        self.w, self.h = self.ui.label.width(), self.ui.label.height()  # 视频显示框宽高
        self.ui.start.clicked.connect(self.detect)  # 若该按键被点击，则调用detect
        self.timer.timeout.connect(self.show)
        self.ui.stop.clicked.connect(self.cancel)  # 若该按键被点击，则调用cancel
        self.cap = cv2.VideoCapture()

        # Create RKNN object
        self.rknn = RKNN(verbose=True)
        # Load RKNN model
        ret = self.rknn.load_rknn(self.model_path)
        # init runtime environment
        ret = self.rknn.init_runtime(async_mode=True)

        setExitButtonStyle(self.ui.exitbutton, "img/icon/exit.png")  # 设置退出按钮样式
        # 为界面按钮设置点击事件处理函数
        self.SetButtonConnected()

    # 11111111111111
    def SetButtonConnected(self):
        # self.exitButton.pressed.connect(self.ExitButtonPressed)
        # self.pushButton.clicked.connect(self.load_data)
        self.ui.exitbutton.clicked.connect(self.ExitButtonPressed)

    def detect(self):
        ret = self.cap.open(self.vid)  # 参数是0，表示打开笔记本的内置摄像头，参数如果是视频文件路径则打开视频
        time.sleep(1)
        if ret:
            self.ui.textBrowser.setText("摄像头打开成功！")  # 设置内容，会覆盖之前的内容
            self.ui.textBrowser.append("开始进行检测！")  # 添加内容，不会覆盖之前的内容
            self.timer.start(30)  # 定时器开始计时每隔30ms停止并重新启动定时器

    def show(self):
        ret, frame = self.cap.read()  # 获取新的一帧图片
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # 视频色彩转换回RGB，这样才是现实的颜色

            img, ratio, (dw, dh) = letterbox(frame, new_shape=(self.img_size, self.img_size))
            # 模型预测
            t1 = time.time()
            outputs = self.rknn.inference(inputs=[img])  # 模型推理
            t2 = time.time()
            fps = 1 / (t2 - t1)  # 计算帧率评估模型性能
            self.ui.textBrowser.append(f'fps:{fps}')
            # post process
            input_data = post_process(outputs)
            boxes, classes, scores = yolov5_post_process(input_data, self.img_size)
            # if boxes is not None:
            #     draw(frame, boxes, scores, classes, dw, dh, ratio,self.label_names)
            if boxes is not None:
                detected = False
                for box, clas, score in zip(boxes, classes, scores):
                    # 将类别索引转换为类别名称
                    class_name = self.label_names[clas]
                    # 播报类别和置信度
                    # broadcast(f"检测到 {class_name}，置信度为 {score:.2f}")
                    broadcast2(f"{class_name}")

                    if class_name in ["Drink", "Text-with-left-hand", "Text-with-right-hand",
                                      "Call-with-left-hand", "Talking-to-passengers",
                                      "Makeup&Fix-hair", "Operate-radio", "Reach-behind",
                                      "Call-with-right-hand", "smoke"]:
                        detected = True

                    # 绘制框和标签
                    draw(frame, [box], [score], [clas], dw, dh, ratio, self.label_names)

                # 灯光控制（需要先初始化control对象）
                serial_port = '/dev/ttyS0'
                control = NewQuerySerial(serial_port)
                if detected:
                    control.turn_on_red()
                else:
                    control.turn_off_red()
                control.close_serial()

            showImage = QtGui.QImage(frame, frame.shape[1], frame.shape[0],
                                     QtGui.QImage.Format_RGB888)  # 把读取到的视频数据变成QImage形式
            self.ui.label.setPixmap(QtGui.QPixmap.fromImage(showImage))  # 往显示视频的Label里 显示QImage
            self.ui.label.setScaledContents(True)  # 图像自适应窗口大小
        else:
            self.cancel()

    def cancel(self):
        self.ui.textBrowser.setText('已关闭检测！')
        self.ui.label.clear()  # 清空视频显示区域
        if self.timer.isActive():
            self.timer.stop()  # 关闭定时器
        if self.cap.isOpened():
            self.cap.release()  # 释放摄像头
        control = NewQuerySerial('/dev/ttyS0')
        control.turn_off_red()
        control.close_serial()

    def ExitButtonPressed(self):
        # 关闭所有灯光
        control = NewQuerySerial('/dev/ttyS0')
        control.turn_off_red()
        control.turn_off_yellow()
        control.turn_off_green()
        control.close_serial()
        self.ui.close()  # 关闭当前窗口


class VideoWindow3(QMainWindow):
    def __init__(self, vid, model_path, label_names, img_size):
        super(VideoWindow3, self).__init__()
        self.vid = vid
        self.model_path = model_path
        self.label_names = label_names
        self.img_size = img_size
        self.setup_ui()

    def setup_ui(self):
        # 实例化定时器
        self.timer = QtCore.QTimer()
        self.ui = uic.loadUi("main.ui")  # 加载UI文件
        self.w, self.h = self.ui.label.width(), self.ui.label.height()  # 视频显示框宽高
        self.ui.start.clicked.connect(self.detect)  # 若该按键被点击，则调用detect
        self.timer.timeout.connect(self.show)  # 若定时器停止，则调用show()，作用是每隔一定时间从摄像头中取一帧显示
        self.ui.stop.clicked.connect(self.cancel)  # 若该按键被点击，则调用cancel
        self.cap = cv2.VideoCapture()

        # Create RKNN object
        self.rknn = RKNN(verbose=True)
        # Load RKNN model
        ret = self.rknn.load_rknn(self.model_path)
        # init runtime environment
        ret = self.rknn.init_runtime(async_mode=True)

        setExitButtonStyle(self.ui.exitbutton, "img/icon/exit.png")  # 设置退出按钮样式
        # 为界面按钮设置点击事件处理函数
        self.SetButtonConnected()

    def SetButtonConnected(self):
        # self.exitButton.pressed.connect(self.ExitButtonPressed)
        # self.pushButton.clicked.connect(self.load_data)
        self.ui.exitbutton.clicked.connect(self.ExitButtonPressed)

    def detect(self):
        ret = self.cap.open(self.vid)  # 参数是0，表示打开笔记本的内置摄像头，参数如果是视频文件路径则打开视频
        time.sleep(1)
        if ret:
            self.ui.textBrowser.setText("摄像头打开成功！")  # 设置内容，会覆盖之前的内容
            self.ui.textBrowser.append("开始进行检测！")  # 添加内容，不会覆盖之前的内容
            self.timer.start(30)  # 定时器开始计时每隔30ms停止并重新启动定时器

    def show(self):
        ret, frame = self.cap.read()  # 获取新的一帧图片
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # 视频色彩转换回RGB，这样才是现实的颜色

            img, ratio, (dw, dh) = letterbox(frame, new_shape=(self.img_size, self.img_size))
            # 模型预测
            t1 = time.time()
            outputs = self.rknn.inference(inputs=[img])  # 模型推理
            t2 = time.time()
            fps = 1 / (t2 - t1)  # 计算帧率评估模型性能
            self.ui.textBrowser.append(f'fps:{fps}')
            # post process
            input_data = post_process(outputs)
            boxes, classes, scores = yolov5_post_process(input_data, self.img_size)
            # if boxes is not None:
            #     draw(frame, boxes, scores, classes, dw, dh, ratio,self.label_names)
            if boxes is not None:
                detected = False
                for box, clas, score in zip(boxes, classes, scores):
                    # 检查 clas 是否在有效范围内
                    if clas >= len(self.label_names):
                        print(f"Invalid class index: {clas}")
                        continue

                    # 将类别索引转换为类别名称
                    class_name = self.label_names[clas]
                    # 播报类别和置信度
                    # broadcast(f"检测到 {class_name}，置信度为 {score:.2f}")
                    broadcast(f"检测到有人摔倒了")

                    if class_name == "Fall":
                        detected = True

                    # 绘制框和标签
                    draw(frame, [box], [score], [clas], dw, dh, ratio, self.label_names)

                # 灯光控制（需要先初始化control对象）
                serial_port = '/dev/ttyS0'
                control = NewQuerySerial(serial_port)
                if detected:
                    control.turn_on_red()
                else:
                    control.turn_off_red()
                control.close_serial()

                # ------------人脸口罩检测-------------
            showImage = QtGui.QImage(frame, frame.shape[1], frame.shape[0],
                                     QtGui.QImage.Format_RGB888)  # 把读取到的视频数据变成QImage形式
            self.ui.label.setPixmap(QtGui.QPixmap.fromImage(showImage))  # 往显示视频的Label里 显示QImage
            self.ui.label.setScaledContents(True)  # 图像自适应窗口大小
        else:
            self.cancel()

    def cancel(self):
        self.ui.textBrowser.setText('已关闭检测！')
        self.ui.label.clear()  # 清空视频显示区域
        if self.timer.isActive():
            self.timer.stop()  # 关闭定时器
        if self.cap.isOpened():
            self.cap.release()  # 释放摄像头
        control = NewQuerySerial('/dev/ttyS0')
        control.turn_off_red()
        control.close_serial()

    # def ExitButtonPressed(self):
    #     self.ui.close()  # 关闭当前窗口

    def ExitButtonPressed(self):
        # 关闭所有灯光
        control = NewQuerySerial('/dev/ttyS0')
        control.turn_off_red()
        control.turn_off_yellow()
        control.turn_off_green()
        control.close_serial()
        self.ui.close()  # 关闭当前窗口


class VideoWindow7(QMainWindow):
    def __init__(self, vid, model_path, label_names, img_size):
        super(VideoWindow7, self).__init__()
        self.vid = vid
        self.model_path = model_path
        self.label_names = label_names
        self.img_size = img_size
        self.setup_ui()

    def setup_ui(self):
        # 实例化定时器
        self.timer = QtCore.QTimer()
        self.ui = uic.loadUi("main.ui")  # 加载UI文件
        self.w, self.h = self.ui.label.width(), self.ui.label.height()  # 视频显示框宽高
        self.ui.start.clicked.connect(self.detect)  # 若该按键被点击，则调用detect
        self.timer.timeout.connect(self.show)  # 若定时器停止，则调用show()，作用是每隔一定时间从摄像头中取一帧显示
        self.ui.stop.clicked.connect(self.cancel)  # 若该按键被点击，则调用cancel
        self.cap = cv2.VideoCapture()

        # Create RKNN object
        self.rknn = RKNN(verbose=True)
        # Load RKNN model
        ret = self.rknn.load_rknn(self.model_path)
        # init runtime environment
        ret = self.rknn.init_runtime(async_mode=True)

        setExitButtonStyle(self.ui.exitbutton, "img/icon/exit.png")  # 设置退出按钮样式
        # 为界面按钮设置点击事件处理函数
        self.SetButtonConnected()

    def SetButtonConnected(self):
        # self.exitButton.pressed.connect(self.ExitButtonPressed)
        # self.pushButton.clicked.connect(self.load_data)
        self.ui.exitbutton.clicked.connect(self.ExitButtonPressed)

    def detect(self):
        ret = self.cap.open(self.vid)  # 参数是0，表示打开笔记本的内置摄像头，参数如果是视频文件路径则打开视频
        time.sleep(1)
        if ret:
            self.ui.textBrowser.setText("摄像头打开成功！")  # 设置内容，会覆盖之前的内容
            self.ui.textBrowser.append("开始进行检测！")  # 添加内容，不会覆盖之前的内容
            self.timer.start(30)  # 定时器开始计时每隔30ms停止并重新启动定时器

    # def detect(self):
    #     ret = self.cap.open(self.vid)  # 参数是0，表示打开笔记本的内置摄像头，参数如果是视频文件路径则打开视频
    #     time.sleep(1)
    #     if ret:
    #         self.ui.textBrowser.setText("摄像头打开成功！")  # 设置内容，会覆盖之前的内容
    #         self.ui.textBrowser.append("开始进行检测！")  # 添加内容，不会覆盖之前的内容
    #         self.timer.start(30)  # 定时器开始计时每隔30ms停止并重新启动定时器

    def show(self):
        ret, frame = self.cap.read()  # 获取新的一帧图片
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # 视频色彩转换回RGB，这样才是现实的颜色

            img, ratio, (dw, dh) = letterbox(frame, new_shape=(self.img_size, self.img_size))
            # 模型预测
            t1 = time.time()
            outputs = self.rknn.inference(inputs=[img])  # 模型推理
            t2 = time.time()
            fps = 1 / (t2 - t1)  # 计算帧率评估模型性能
            self.ui.textBrowser.append(f'fps:{fps}')
            # post process
            input_data = post_process(outputs)
            boxes, classes, scores = yolov5_post_process(input_data, self.img_size)
            # if boxes is not None:
            #     draw(frame, boxes, scores, classes, dw, dh, ratio,self.label_names)
            if boxes is not None:
                detected = False
                for box, clas, score in zip(boxes, classes, scores):
                    # 将类别索引转换为类别名称
                    class_name = self.label_names[clas]
                    # 播报类别和置信度
                    # broadcast(f"检测到 {class_name}，置信度为 {score:.2f}")
                    broadcast4(f"{class_name}")

                    #
                    if class_name in ["right", "left"]:
                        detected = True

                    # 绘制框和标签
                    draw(frame, [box], [score], [clas], dw, dh, ratio, self.label_names)

                # 灯光控制（需要先初始化control对象）
                # serial_port = '/dev/ttyS0'
                # control = NewQuerySerial(serial_port)
                # if detected:
                #     control.turn_on_red()
                # else:
                #     control.turn_off_red()
                # control.close_serial()
                
            showImage = QtGui.QImage(frame, frame.shape[1], frame.shape[0], QtGui.QImage.Format_RGB888)
            self.ui.label.setPixmap(QtGui.QPixmap.fromImage(showImage))
            self.ui.label.setScaledContents(True)
        else:
            self.cancel()

    def cancel(self):
        self.ui.textBrowser.setText('已关闭检测！')
        self.ui.label.clear()
        if self.timer.isActive():
            self.timer.stop()
        if self.cap.isOpened():
            self.cap.release()
        # control = NewQuerySerial('/dev/ttyS0')
        # control.turn_off_red()
        # control.close_serial()

    def ExitButtonPressed(self):
        # 关闭所有灯光
        # control = NewQuerySerial('/dev/ttyS0')
        # control.turn_off_red()
        # control.turn_off_yellow()
        # control.turn_off_green()
        # control.close_serial()
        self.ui.close()  # 关闭当前窗口


class AnoWindow(QMainWindow, Ui_AnoWindow):
    def __init__(self):
        super(AnoWindow, self).__init__(None)
        # 设置UI
        self.setupUi(self)
        # 隐藏标题栏
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        # 更新用户界面，包括背景图和按钮样式
        self.UpdateUi()
        # 为界面按钮设置点击事件处理函数
        self.SetButtonConnected()
        # 初始化按钮状态
        self.redButtonState = False  # False 表示灯是关闭的，True 表示灯是打开的
        self.yellowButtonState = False  # False 表示灯是关闭的，True 表示灯是打开的
        self.greenButtonState = False  # False 表示灯是关闭的，True 表示灯是打开的
        self.fanButtonState = False  # False 表示灯是关闭的，True 表示灯是打开的

    # 更新用户界面，包括背景图和按钮样式
    def UpdateUi(self):
        # 设置字体样式
        font = QtGui.QFont()  # 创建一个 QFont 对象，用于定义字体的样式
        font.setBold(True)
        font.setPointSize(14)
        self.ShowIPLabel.setFont(font)

        # 设置背景图片
        # self.setStyleSheet("#AnoWindow{border-image:url(img/icon/backgroundpic.jpg);}")
        # self.backgroundlable.setPixmap(QtGui.QPixmap("img/icon/backgroundpic.jpg"))
        # self.backgroundlable.setScaledContents(True)
        self.backgroundlable.setGeometry(QtCore.QRect(0, 0, 1920, 1080))  # 设置背景图片的大小和位置
        self.setStyleSheet("#AnoWindow{border-image:url(img/icon/background1.PNG);}")
        self.backgroundlable.setPixmap(QtGui.QPixmap("img/icon/background1.PNG"))
        self.backgroundlable.setScaledContents(True)

        setButtonStyle2(self.redButton, "img/icon/FFF/f11.png")
        setButtonStyle2(self.yellowButton, "img/icon/FFF/f22.png")
        setButtonStyle2(self.greenButton, "img/icon/FFF/f33.png")
        setButtonStyle2(self.fanButton, "img/icon/FFF/f44.png")
        setButtonStyle2(self.fingerButton, "img/icon/FFF/f55.png")
        setButtonStyle2(self.tempButton, "img/icon/FFF/f66.png")

        # 设置退出按钮样式
        setExitButtonStyle(self.exitbutton, "img/icon/btn_back_r_normal.png")

        self.School.setPixmap(QtGui.QPixmap('img/icon/nle.png'))
        self.School.setStyleSheet("QPushButton{background:rgb(255,255,255,50);}"
                                  "QPushButton:hover{color:rgb(100,100,100,120);}")
        self.School.setScaledContents(True)
        # 新大陆logo
        self.School.setPixmap(QtGui.QPixmap('img/icon/nle.png'))
        self.School.setStyleSheet("QPushButton{background:rgb(255,255,255,50);}"
                                  "QPushButton:hover{color:rgb(100,100,100,120);}")
        self.School.setScaledContents(True)

        font = QtGui.QFont()
        font.setPointSize(15)
        font.setBold(True)
        self.ShowIPLabel.setFont(font)

    # 将按钮的点击信号连接到对应的槽函数
    def SetButtonConnected(self):
        self.redButton.pressed.connect(self.ButtonPressed1)
        self.yellowButton.pressed.connect(self.ButtonPressed2)
        self.greenButton.pressed.connect(self.ButtonPressed3)
        self.fanButton.pressed.connect(self.ButtonPressed4)
        self.fingerButton.pressed.connect(self.ButtonPressed5)
        self.tempButton.pressed.connect(self.ButtonPressed6)
        self.exitbutton.pressed.connect(self.ExitButtonPressed)

    # 第一个按钮的点击事件，打开 VideoWindow1
    def ButtonPressed1(self):
        self.redButton.setEnabled(False)  # 禁用按钮，防止重复点击
        # 打开串口
        serial_port = '/dev/ttyS0'  # 串口位置
        control = NewQuerySerial(serial_port)
        if not self.redButtonState:  # 如果灯是关闭的
            control.turn_on_red()  # 打开红灯
            self.redButtonState = True  # 更新状态为打开
            broadcast("红灯已打开")
        else:  # 如果灯是打开的
            control.turn_off_red()  # 关闭红灯
            self.redButtonState = False  # 更新状态为关闭
            broadcast("红灯已关闭")
        time.sleep(0.5)  # 等待一段时间，确保灯的状态已经改变
        # 关闭串口
        control.close_serial()
        self.redButton.setEnabled(True)

    # 第二个按钮的点击事件，打开 VideoWindow2
    def ButtonPressed2(self):
        self.yellowButton.setEnabled(False)
        serial_port = '/dev/ttyS0'
        control = NewQuerySerial(serial_port)
        if not self.yellowButtonState:
            control.turn_on_yellow()
            self.yellowButtonState = True
            broadcast("黄灯已打开")
        else:
            control.turn_off_yellow()
            self.yellowButtonState = False
            broadcast("黄灯已关闭")
        time.sleep(0.5)
        # 关闭串口
        control.close_serial()
        self.yellowButton.setEnabled(True)

    # 第三个按钮的点击事件，打开 VideoWindow3
    def ButtonPressed3(self):
        self.greenButton.setEnabled(False)
        serial_port = '/dev/ttyS0'
        control = NewQuerySerial(serial_port)
        if not self.greenButtonState:
            control.turn_on_green()
            self.greenButtonState = True
            broadcast("绿灯已打开")
        else:
            control.turn_off_green()
            self.greenButtonState = False
            broadcast("绿灯已关闭")
        time.sleep(0.5)
        # 关闭串口
        control.close_serial()
        self.greenButton.setEnabled(True)

    # 第四个按钮的点击事件
    def ButtonPressed4(self):
        self.fanButton.setEnabled(False)
        serial_port = '/dev/ttyS0'
        control = NewQuerySerial(serial_port)
        if not self.fanButtonState:
            control.turn_on_fan()
            self.fanButtonState = True
            broadcast("风扇已打开")
        else:
            control.turn_off_fan()
            self.fanButtonState = False
            broadcast("风扇已关闭")
        time.sleep(1)
        # 关闭串口
        control.close_serial()
        self.fanButton.setEnabled(True)

    # 第六个按钮的点击事件
    def ButtonPressed6(self):
        self.tempButton.setEnabled(False)
        serial_port = '/dev/ttyS4'  # 串口位置
        tempser = TempQuerySerial(serial_port)
        temp = tempser.get_temp()
        tempser.close_serial()
        print(temp)
        self.read_temp(temp)
        # broadcast(f"当前温度是{temp}摄氏度")
        self.tempButton.setEnabled(True)

        serial_port = '/dev/ttyS0'
        control = NewQuerySerial(serial_port)
        temp1 = float(temp)
        if temp1 < 36.5:
            control.turn_on_yellow()
            time.sleep(0.5)
            control.turn_off_yellow()
            time.sleep(0.5)
        elif 36.5 <= temp1 <= 37.3:
            control.turn_on_green()
            time.sleep(0.5)
            control.turn_off_green()
            time.sleep(0.5)
        else:
            control.turn_on_red()
            time.sleep(0.5)
            control.turn_off_red()
            time.sleep(0.5)
        control.close_serial()

        self.fanButton.setEnabled(True)

        # chinese_temp = self.number_to_chinese(temp)
        # print(f"当前温度是{chinese_temp}摄氏度")
        # broadcast(f"当前温度是{chinese_temp}摄氏度")

    def read_temp(self, temp):
        # 拆分整数部分和小数部分
        integer_part, decimal_part = str(temp).split('.')
        integer_part = int(integer_part)
        decimal_part = int(decimal_part)
        a = integer_part // 10  # 十位数
        b = integer_part % 10  # 个位数
        # c=decimal_part%10
        broadcast(f"当前温度是{a}十{b}.{decimal_part}摄氏度")

    # def ButtonPressed5(self):
    #     self.tempButton.setEnabled(False)

    #     self.tempButton.setEnabled(True)

    #     def waitFingerUp(self):
    #         print("请抬起手指")
    #         time.sleep(2)
    #     def recognisePerTime(self,times):
    #         print(f"录制第 {times} 次指纹完成")
    #     def ButtonPressed5(self):
    #         self.fingerButton.setEnabled(False)
    #         # print("开始录入指纹")
    #         try:
    #             devName = '/dev/ttyUSB0'
    #             baudrate = 57600
    #             finger = FingerPrintDevManager(devName, baudrate)
    #             finger.deviceInit()  # 指纹设备初始化
    #             # broadcast("指纹设备初始化成功")
    #             # time.sleep(2)
    #             print("请抬起手指")
    #             broadcast("请抬起手指")
    #             self.waitFingerUp()

    #             # 指纹录入
    #             finger_id = 1  # 指纹id
    #             times = 3  # 录入次数
    #             record_result = finger.recordeFingerPoint(
    #                 fingerId=finger_id,
    #                 times=times,
    #                 waitFingerUp=self.waitFingerUp,
    #                 recognisePerTime=self.recognisePerTime
    #             )
    #             print("1")
    #             if record_result:
    #                 print('指纹录制成功')
    #                 broadcast("指纹录制成功")
    #             else:
    #                 print('指纹录制失败')
    #                 broadcast("指纹录制失败")

    #             # 读取指纹库
    #             tables = finger.readFingerTables()
    #             print("指纹表内容:", tables)
    #             # 指纹识别
    #             if tables:
    #                 startCharIdx = min(tables)
    #                 endCharIdx = max(tables)
    #                 while True:
    #                     print('指纹比对开始，请按下手指')
    #                     broadcast("指纹比对开始，请按下手指")
    #                     foundId = finger.checkFingerChar(startCharIdx, endCharIdx)
    #                     if foundId[0] is not None:
    #                         break
    #                     print("比对失败，请更换手指角度")
    #                     broadcast("比对失败，请更换手指角度")
    #                 print('***' * 8)
    #                 # print("检测到手指Id:", foundId[0])
    #                 # print("检测结果得分:", foundId[1])
    #                 print(f"检测到手指Id: {foundId[0]}")
    #                 print(f"检测结果得分: {foundId[1]}")
    #                 broadcast(f"检测到手指{foundId[0]},检测结果得分{foundId[1]}")

    #             else:
    #                 print("指纹表为空，无法进行比对")
    #             broadcast("指纹表为空，无法进行比对")

    #         except Exception as e:
    #             print(f"指纹操作失败: {e}")
    #         finally:
    #             self.fingerButton.setEnabled(True)

    def ButtonPressed5(self):
        detected = False

        devName = '/dev/ttyUSB0'
        baudrate = 57600
        finger = FingerPrintDevManager(devName, baudrate)
        finger.deviceInit()  ##指纹设备初始化
        broadcast("指纹设备初始化成功")
        time.sleep(2)
        broadcast("请按下手指")

        def waitFingerUp(times):
            print("请抬起手指")
            broadcast("请抬起手指")

        def recognisePerTime(times):
            print("录制第", times, "次指纹完成")
            broadcast(f"录制第{times}次指纹完成")
            time.sleep(2)
            if (times < 3):
                broadcast("请按下手指")

        finger_id = 1  # 指纹id
        times = 3  # 录入次数
        time.sleep(2)
        record_result = finger.recordeFingerPoint(fingerId=finger_id, times=times, waitFingerUp=waitFingerUp,
                                                  recognisePerTime=recognisePerTime)
        if record_result:
            print('指纹录制成功')
            broadcast("指纹录制成功")
            time.sleep(3)
        else:
            print('指纹录制失败')
            broadcast("指纹录制失败")
            time.sleep(2)
        tables = finger.readFingerTables()
        print(tables)

        tables = finger.readFingerTables()
        startCharIdx = min(tables)
        endCharIdx = max(tables)
        while True:
            print('指纹比对开始，请按下手指')
            broadcast("指纹比对开始，请按下手指")
            time.sleep(2)

            control = NewQuerySerial('/dev/ttyS0')
            foundId = finger.checkFingerChar(startCharIdx, endCharIdx)
            if foundId[0] is not None:
                control.turn_on_green()  # 匹配成功亮绿灯
                control.turn_off_yellow()
                break
            else:
                control.turn_on_yellow()  # 匹配失败亮黄灯
                control.turn_off_green()
                print("比对失败，请更换手指角度")
                broadcast("比对失败 请更换手指角度")
            control.close_serial()

        print('***' * 8)
        print("检测到手指Id:", foundId[0])
        print("检测结果得分:", foundId[1])
        time.sleep(2)
        broadcast(f"指纹匹配成功")

    # 退出按钮点击事件
    def ExitButtonPressed(self):
        # 关闭所有灯光
        control = NewQuerySerial('/dev/ttyS0')
        control.turn_off_red()
        control.turn_off_yellow()
        control.turn_off_green()
        control.close_serial()
        self.close()  # 关闭当前窗口


class speechControlThread(threading.Thread):
    def __init__(self):
        super(speechControlThread, self).__init__()
        self.working = True
        self.control = NewQuerySerial('/dev/ttyS0')
        self.control.turn_off_red()
        self.control.turn_off_yellow()
        self.control.turn_off_green()
        self.speak = MicrophoneController(1)  # 实例化语音识别对象,1表示可以进行语音识别

    def run(self):
        while self.working:
            try:
                command = self.speak.recognition(sec=3)
                print(command)
                # 成功识别到唤醒词
                if '打开红灯' in command:
                    self.control.turn_on_red()
                    self.speak.broadcast('已打开红灯')
                elif '打开黄灯' in command:
                    self.control.turn_on_yellow()
                    self.speak.broadcast('已打开黄灯')
                elif '打开绿灯' in command:
                    self.control.turn_on_green()
                    self.speak.broadcast('已打开绿灯')
                elif '打开风扇' in command:
                    self.control.turn_on_fan()
                    self.speak.broadcast('已打开风扇')
                elif '关闭红灯' in command:
                    self.control.turn_off_red()
                    self.speak.broadcast('已关闭红灯')
                elif '关闭黄灯' in command:
                    self.control.turn_off_yellow()
                    self.speak.broadcast('已关闭黄灯')
                elif '关闭绿灯' in command:
                    self.control.turn_off_green()
                    self.speak.broadcast('已关闭绿灯')
                elif '关闭风扇' in command:
                    self.control.turn_off_fan()
                    self.speak.broadcast('已关闭风扇')
                elif '关闭灯' in command:
                    self.control.turn_off_red()
                    self.control.turn_off_yellow()
                    self.control.turn_off_green()
                    self.speak.broadcast('已关闭灯')
            except Exception as e:
                print(e)
        self.stop()

    def stop(self):
        if self.working:
            self.working = False
        self.control.turn_off_red()
        self.control.turn_off_yellow()
        self.control.turn_off_green()
        self.control.close_serial()
        self.speak.close()
        print('已退出语音控制线程！')


if __name__ == '__main__':
    # 参数设置
    # vid = 'driver_det.mp4'
    # model_path = 'best.rknn'
    # label_names = ("Drink", "Text-with-left-hand", "Text-with-right-hand", "Call-with-left-hand",
    #                "Talking-to-passengers", "Makeup&Fix-hair", "Safe-driving", "Operate-radio",
    #                "Reach-behind", "Call-with-right-hand")
    # img_size = 640  # 训练时的图像尺寸

    # 界面启动
    app = QApplication(sys.argv)
    main_window = MainWindows()  # 创建 MainWindows 实例
    main_window.show()  # 显示主窗口
    sys.exit(app.exec_())