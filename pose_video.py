# -*- coding: utf-8 -*-
import os
import sys, signal
import time
from ctypes import *
import cv2
import numpy as np
from PyQt5 import QtCore
from PyQt5.QtCore import QThread, QMutex, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QWidget, QApplication, QLabel, QPushButton, QStyle, QHBoxLayout, QVBoxLayout

from Algorithm.posePoint import NLPose, gColors, gPosePairs


class PoseThread(QThread):
    """
    骨骼描点算法sdk调用线程
    """
    updatedImage = QtCore.pyqtSignal(int)

    def __init__(self, mw):
        self.mutex = QMutex()
        self.mw = mw
        self.nlPose = None
        self.working = True
        self.isInit = False
        QThread.__init__(self)

    def __del__(self):
        self.wait()

    def myInit(self):
        if not self.isInit:
            self.nlPose = NLPose(self.mw.libNamePath)
            print('初始化')
            if self.nlPose == -1001:
                print('NL_Pose Error code:', self.nlPose)
                quit()
            ret = self.nlPose.NL_Pose_ComInit(self.mw.configPath)  # 初始化
            print('加载模型')
            if ret != 0:
                print('ComInit Error code:', ret)
            self.isInit = True
            print('初始化成功')

    def run(self):
        self.myInit()
        while self.working:
            self.mutex.lock()
            if self.mw.AlgIsbasy == False and not (self.mw.limg is None):
                self.mw.AlgIsbasy = True
                limg = self.mw.limg
                ret = self.nlPose.NL_Pose_InitVarIn(limg)
                if ret == 0:
                    ret = self.nlPose.NL_Pose_Process_C()  # 返回值是目标个数
                    height, width, bytesPerComponent = limg.shape
                    bytesPerLine = bytesPerComponent * width
                    rgb = cv2.cvtColor(limg, cv2.COLOR_BGR2RGB)
                    if ret > 0:
                        # 结果输出
                        lineType = 8
                        threshold = 0.05
                        numberColors = len(gColors)
                        for i in range(int(self.nlPose.djACTVarOut.dwPersonNum)):
                            djActionInfors = self.nlPose.djACTVarOut.pdjActionInfors[i]
                            # 绘制关节点
                            for pose in range(djActionInfors.dwPoseNum):
                                djfPosePos = djActionInfors.fPosePos[pose]
                                if djfPosePos.p_score > threshold:
                                    colorIndex = pose * 3
                                    centerPoint = (int(djfPosePos.x), int(djfPosePos.y))  # 关节点坐标
                                    color = (
                                    gColors[(colorIndex + 2) % numberColors], gColors[(colorIndex + 1) % numberColors],
                                    gColors[colorIndex % numberColors])
                                    cv2.circle(rgb, centerPoint, 3, color, 1, lineType)
                            # 绘制关节点连线
                            for pair in range(0, len(gPosePairs), 2):
                                fPosePos1 = djActionInfors.fPosePos[gPosePairs[pair]]
                                fPosePos2 = djActionInfors.fPosePos[gPosePairs[pair + 1]]
                                if (fPosePos1.p_score > threshold) and (fPosePos2.p_score > threshold):
                                    colorIndex = gPosePairs[pair + 1] * 3
                                    color = (gColors[(colorIndex + 2) % numberColors],
                                             gColors[(colorIndex + 1) % numberColors],
                                             gColors[colorIndex % numberColors])
                                    LineScaled = 5
                                    keypoint1 = (int(fPosePos1.x), int(fPosePos1.y))
                                    keypoint2 = (int(fPosePos2.x), int(fPosePos2.y))
                                    cv2.line(rgb, keypoint1, keypoint2, color, LineScaled, lineType)

                            # 绘制上半身矩形框
                            RectPoint1 = (
                            self.nlPose.djACTVarOut.pdjUpBodyPos[i].x, self.nlPose.djACTVarOut.pdjUpBodyPos[i].y)
                            RectPoint2 = (
                            self.nlPose.djACTVarOut.pdjUpBodyPos[i].x + self.nlPose.djACTVarOut.pdjUpBodyPos[i].width,
                            self.nlPose.djACTVarOut.pdjUpBodyPos[i].y + self.nlPose.djACTVarOut.pdjUpBodyPos[i].height)
                            cv2.rectangle(rgb, RectPoint1, RectPoint2, (200, 0, 125), 5, 8)
                            # 输出文本信息：行为
                            actPoint = (int(self.nlPose.djACTVarOut.pdjUpBodyPos[i].x + self.nlPose.djACTVarOut.pdjUpBodyPos[i].width / 2 - 3),
                                        int(self.nlPose.djACTVarOut.pdjUpBodyPos[i].y + self.nlPose.djACTVarOut.pdjUpBodyPos[i].height / 2 - 3))
                            textOut_action = "Action: "
                            mask = 0
                            if self.nlPose.djACTVarOut.pdjActionInfors[i].pdwHandUp:
                                mask = 1
                                textOut_action = textOut_action + "hand up "  # 举手
                            if self.nlPose.djACTVarOut.pdjActionInfors[i].pdwStandUp:
                                mask = 1
                                textOut_action = textOut_action + "stand up "  # 起立
                            if self.nlPose.djACTVarOut.pdjActionInfors[i].pdwBowHead and self.nlPose.djACTVarOut.pdjActionInfors[i].pdwBendOverDesk == 0:
                                mask = 1
                                textOut_action = textOut_action + "bow head "  # 抬头
                            if self.nlPose.djACTVarOut.pdjActionInfors[i].pdwBendOverDesk:
                                mask = 1
                                textOut_action = textOut_action + "bend desk "  # 趴桌子
                            if self.nlPose.djACTVarOut.pdjActionInfors[i].pdwPlayPhone:
                                mask = 1
                                textOut_action = textOut_action + "play phone "  # 玩手机
                            if self.nlPose.djACTVarOut.pdjActionInfors[i].pdwStudy:
                                mask = 1
                                textOut_action = textOut_action + "learn "  # 学习
                            if mask != 1:
                                cv2.putText(rgb, textOut_action, actPoint, cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2, 8)
                                print(textOut_action)
                            else:
                                cv2.putText(rgb, textOut_action, actPoint, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, 8)
                                print(textOut_action)

                    showImage = QImage(rgb.data, width, height, bytesPerLine, QImage.Format_RGB888)
                    self.mw.showImage = QPixmap.fromImage(showImage)
                    self.updatedImage.emit(self.mw.frameID)
                else:
                    print('Var Init Error code:', ret)
                    time.sleep(0.001)
                self.mw.AlgIsbasy = False
            else:
                time.sleep(0.001)
            self.mutex.unlock()

    def stop(self):  # 重写stop方法
        self.working = False
        self.mutex.lock()
        if self.isInit:
            self.nlPose.NL_Pose_Exit()
        self.mutex.unlock()
        print('算法线程退出了')


class CameraThread(QThread):
    """
    摄像头采集图片线程
    """
    updatedM = QtCore.pyqtSignal(int)

    def __init__(self, mw):
        self.mw = mw
        self.working = True
        self.mutex = QMutex()
        QThread.__init__(self)

    def __del__(self):
        self.wait()

    def run(self):
        while self.working:
            self.mutex.lock()
            QApplication.processEvents()
            if not self.mw.CapIsbasy:
                # 采集图像的过程中
                self.mw.CapIsbasy = True
                ret, image = self.mw.cap.read()  # 获取新的一帧图片
                if not ret:
                    print("Capture Image Failed")
                    self.mw.CapIsbasy = False
                    continue
                height = image.shape[0]
                width = image.shape[1]
                if height != 960 or width != 1280:
                    image_resize = cv2.resize(image, (1280, 960), interpolation=cv2.INTER_CUBIC)
                else:
                    image_resize = image
                img_len = len(image_resize.shape)
                if img_len == 3:
                    self.mw.limg = image_resize
                else:
                    self.mw.limg = cv2.cvtColor(image_resize, cv2.COLOR_GRAY2BGR)
                self.mw.CapIsbasy = False
                self.updatedM.emit(self.mw.frameID)
            else:
                time.sleep(1.0 / 50)

            self.mutex.unlock()

    def stop(self):
        self.mutex.unlock()
        if self.working:
            self.working = False
            print('摄像头采集线程退出')


# 设置qt显示窗口
class VideoBox(QWidget):
    """
    显示界面
    """
    def __init__(self, libNamePath, configPath, capWidth, capHeight):
        QWidget.__init__(self)
        self.setWindowFlags(Qt.CustomizeWindowHint)
        self.move(0, 0)
        self.label_show_camera = QLabel()
        self.label_show_camera.setObjectName("Picture")
        self.label_show_camera.setScaledContents(True)

        # 设置停止按钮组件 QPushButton
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setMaximumSize(QtCore.QSize(150, 60))
        self.stop_btn.setEnabled(True)
        self.stop_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.stop_btn.clicked.connect(self.stop_btn_func)

        # 设置开始按钮组件 QPushButton
        self.start_btn = QPushButton("start")
        self.start_btn.setMaximumSize(QtCore.QSize(150, 60))
        self.start_btn.setEnabled(True)
        self.start_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.start_btn.clicked.connect(self.start_btn_func)

        # 信息提示
        self.info_label = QLabel()
        self.info_label.setText('')
        self.info_label.setMaximumSize(QtCore.QSize(150, 60))

        # 设置按键大小边框 QHBoxLayout
        control_box = QHBoxLayout()
        control_box.setContentsMargins(0, 0, 0, 0)
        control_box.addWidget(self.start_btn)
        control_box.addWidget(self.info_label)
        control_box.addWidget(self.stop_btn)

        layout = QVBoxLayout()
        layout.addWidget(self.label_show_camera)
        layout.addLayout(control_box)
        self.setLayout(layout)

        self.capWidth = capWidth
        self.capHeight = capHeight
        self.libNamePath = libNamePath
        self.configPath = configPath

        # 设置双线程
        self.frameID = 0
        self.CapIsbasy = False
        self.AlgIsbasy = False

        # 设计视频采集参数
        self.cap = cv2.VideoCapture(0)  # 打开摄像头
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, capWidth)  # 设置摄像头分辨率宽度
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, capHeight)  # 设置摄像头分辨率高度
        self.showImage = None
        self.limg = None

    def start_btn_func(self):
        self.info_label.setText('加载中......')
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # 线程1相机采集
        self.camera_th = CameraThread(self)
        self.camera_th.start()

        # hikang_thread = HiKangThread()
        # hikang_thread.start()

        # 线程2算法处理
        self.pose_th = PoseThread(self)
        self.pose_th.updatedImage.connect(self.showframe)
        self.pose_th.start()

    def showframe(self):
        self.info_label.setText('已加载完成！')
        self.label_show_camera.setPixmap(self.showImage)
        if not self.stop_btn.isEnabled():
            self.info_label.setText('已停止！')

    def stop_btn_func(self):
        self.close_camera_th()
        self.close_pose_th()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def close_camera_th(self):
        try:
            self.camera_th.stop()
            self.camera_th.quit()
            self.camera_th.wait()
            self.camera_th.exec_()
            self.camera_th.exit()
            del self.camera_th
        except Exception as e:
            pass
    def close_pose_th(self):
        try:
            self.pose_th.stop()
            self.pose_th.quit()
            self.pose_th.wait()
            self.pose_th.exec_()
            self.pose_th.exit()
            del self.pose_th
        except Exception as e:
            pass


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        libs_path = '/usr/local/lib'
        modelPath = b"/usr/local/lib/rk3399_AI_model"
        libNamePath = "{}/libNL_ACTIONENC.so".format(libs_path)  # 模型名字
        box = VideoBox(libNamePath, modelPath, 640, 480)
        box.showFullScreen()
        sys.exit(app.exec_())
    except Exception as e:
        pass
    
