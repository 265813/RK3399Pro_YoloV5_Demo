import threading
import time
from lib.serialServer import NewQuerySerial
from lib.speech_recognition import MicrophoneController


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
                elif '关闭红灯' in command:
                    self.control.turn_off_red()
                    self.speak.broadcast('已关闭红灯')
                elif '关闭黄灯' in command:
                    self.control.turn_off_yellow()
                    self.speak.broadcast('已关闭黄灯')
                elif '关闭绿灯' in command:
                    self.control.turn_off_green()
                    self.speak.broadcast('已关闭绿灯')
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

# 实例化对象
speech_ctrl_th = speechControlThread()
# 启动线程
speech_ctrl_th.start()
# 停止线程
speech_ctrl_th.stop()