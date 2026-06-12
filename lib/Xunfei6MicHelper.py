import ctypes
import os
import threading
import re
import subprocess
import time
from ctypes import *
from configparser import ConfigParser
from PyQt5 import QtCore
from PyQt5.QtCore import QThread
from lib.serialServer import NewQuerySerial
word_str = ""
BASE_PATH='./'

class Xunfei6MicHelper:

    def __init__(self):
        """
        语音阵列初始化
        """
        # 状态值
        self.error = 0
        self.sucess = 0

        self.voice_broadcast = '/usr/local/speech/broadcast/bin/'
        self.lib = ctypes.cdll.LoadLibrary('/usr/lib/libNLEIflytekSoundCardLib.so')
        
        config_path = BASE_PATH + "/appInfo/AppInfo.ini"
        config = ConfigParser()  # 读取通用配置
        config.read(config_path)
        gWorkMode = config.get('XunFei', 'gWorkMode')
        wakeupWord = config.get('XunFei', 'wakeupWord')
        appId = config.get('XunFei', 'appId')
        with open(BASE_PATH + "/configs/aiui.cfg") as f:
            lines = f.read()
        self.invalidSound = config.get('XunFei', 'invalidSound')
        self.recognizeFail = config.get('XunFei', 'recognizeFail')
        self.sec = config.get('XunFei', 'sec')
        
        self.gWorkMode = gWorkMode
        self.wakeupWord = wakeupWord
        self.appId = appId
        self.cfgs = lines
        
        
        
        
        self.lib.gTTS.argtypes = [c_char_p]

        self.lib.initSoundCard.restype = ctypes.c_bool
        self.lib.initSoundCard.argtypes = [c_int, c_char_p, c_char_p, c_char_p, c_int, c_char_p, c_char_p, c_int, c_int,
                                           c_int]
        self.lib.read_and_play1.argtypes = [c_char_p, c_int]
        self.lib.createAsrAgentNew.argtypes = [c_int]
        self.lib.open_play1.argtypes = [c_char_p]
        self.lib.setTargetLedOn.argtypes = [c_int]
        self.lib.set_awake_word_once.argtypes = [c_char_p]

    def start(self, invalidSound, recognizeFail, sec, devName):
        """
        启动声卡初始化线程

        参数说明:
        invalidSound - 单轮识别最大次数
        recognizeFail - 单轮识别最大失败次数
        sec - 识别前最大等待时间
        devName - 声卡设备名
        """
        self.devMainLoop = threading.Thread(target=self.init_dev, args=(invalidSound, recognizeFail, sec, devName))
        self.devMainLoop.start()

    def init_dev(self, invalidSound, recognizeFail, sec, devName):
        """
        初始化声卡函数

        参数说明:
        invalidSound - 单轮识别最大次数
        recognizeFail - 单轮识别最大失败次数
        sec - 识别前最大等待时间
        devName - 声卡设备名
        """
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # 启动语音识别
        self.lib.initSoundCard(int(self.gWorkMode), self.wakeupWord.encode('utf-8'),
                               self.appId.encode('utf-8'),
                               self.cfgs.encode('utf-8'), 1,
                               devName.encode('utf-8'),
                               base_path.encode('utf-8'), int(invalidSound), int(recognizeFail), int(sec))

    def wait(self):
        """
        主线程等待函数，用户阻塞initSoundCard线程.
        """
        self.devMainLoop.join()

    def set_led(self, led_id):
        self.lib.setTargetLedOn(led_id)

    def set_wakeup_info_callback(self, ledLightFunc):
        """
        设置声卡唤醒回调

        参数说明:
        ledLightFunc - 声卡唤醒后回调该函数
        """
        WAKE_UP_FUNC = CFUNCTYPE(c_void_p, c_int, c_int, c_int, c_int)
        self.wake_up_func = WAKE_UP_FUNC(ledLightFunc)
        self.lib.setWakeupInfoCallBack(self.wake_up_func)

    def before_set_wakeup_word_func(self):
        print("延时设置")
        time.sleep(1)

    def SetBeforeSetWakeupWordCallback(self, BeforeSetWakeupWordFunc):
        print("SetBeforeSetWakeupWordCallback")
        BeforeSetWakeupWordType = CFUNCTYPE(c_void_p)
        self.BeforeSetWakeupWordFunc = BeforeSetWakeupWordType(BeforeSetWakeupWordFunc)
        self.lib.setBeforeSetWakeupWordCallback(self.BeforeSetWakeupWordFunc)

    def set_offline_agent_sleep_callback(self, OfflineAgentSleepFunc):
        """
        设置离线引擎休眠时回调

        参数说明:
        OfflineAgentSleepFunc - 在离线引擎休眠时回调该函数
        """
        OfflineAgentSleepType = CFUNCTYPE(c_void_p)
        self.offline_agent_sleep_type_func = OfflineAgentSleepType(OfflineAgentSleepFunc)
        self.lib.setOfflineAgentSleepCallback(self.offline_agent_sleep_type_func)

    def set_sound_record_finish_callback(self, SoundRecordFinishFunc):
        """
        设置声音录制结束回调

        参数说明:
        SoundRecordFinishFunc - 声音录制结束后回调该函数
        """
        SoundRecordFinishType = CFUNCTYPE(c_void_p)
        self.sound_record_finish_func = SoundRecordFinishType(SoundRecordFinishFunc)
        self.lib.setSoundRecordFinishCallBack(self.sound_record_finish_func)

    def set_effective_ans_callback(self, EffectiveAnsFunc):
        """
        设置声音录制回调

        参数说明:
        SoundRecordFinishFunc - 声音录制结束后回调该函数
        """
        EffectiveAnsType = CFUNCTYPE(c_void_p, c_bool, c_int, c_char_p, c_char_p)
        self.effective_ans_func = EffectiveAnsType(EffectiveAnsFunc)
        self.lib.setEffectiveAnsCallBack(self.effective_ans_func)

    def set_nlp_event_callback(self, NlpEventCallbackFunc):
        """
        设置在线模式下，获取问与答语音文字内容的回调

        参数说明:
        NlpEventCallbackFunc - 获取问与答语音文字内容的回调
        """
        NlpEventCallbackType = CFUNCTYPE(c_void_p, c_char_p, c_char_p)
        self.nlp_event_callback_func = NlpEventCallbackType(NlpEventCallbackFunc)
        self.lib.setNlpEventCallback(self.nlp_event_callback_func)

    def set_tts_event_callback(self, TtsEventCallbackFunc):
        """
        设置在线模式下，获取回答语音文字内容的回调，此时库内部会负责语音播放

        参数说明:
        TtsEventCallbackFunc - 获取回答语音文字内容的回调
        """
        TtsEventCallbackType = CFUNCTYPE(c_void_p, c_char_p)
        self.tts_event_callback_func = TtsEventCallbackType(TtsEventCallbackFunc)
        self.lib.setTtsEventCallback(self.tts_event_callback_func)

    def set_wakeup_word(self, wakeupWord):
        print(wakeupWord)
        self.lib.set_awake_word_once(wakeupWord.encode('utf-8'))

    def set_init_dev_done_callback(self, InitDevDoneFunc):
        """
        设置初始化声卡设备成功后回调

        参数说明:
        InitDevDoneFunc - 初始化声卡设备成功后回调
        """
        InitDevDoneCallbackType = CFUNCTYPE(c_void_p)
        self.init_dev_done_func = InitDevDoneCallbackType(InitDevDoneFunc)
        self.lib.setInitDevDoneCallback(self.init_dev_done_func)

    def set_wakeup_work_callback(self, WakeupWordFunc):
        """
        唤醒词设置完成回调

        参数说明:
        WakeupWordFunc - 唤醒词设置完成回调
        """
        WakeupWordCallbackType = CFUNCTYPE(c_void_p, c_int)
        self.wakeup_word_func = WakeupWordCallbackType(WakeupWordFunc)
        self.lib.setWackupWordCallback(self.wakeup_word_func)

    def set_init_start_callback(self, InitStartFunc):
        """
        声卡初始化开始的回调

        参数说明:
        InitStartFunc - 声卡初始化开始的回调
        """
        InitStartCallbackType = CFUNCTYPE(c_void_p)
        self.init_start_func = InitStartCallbackType(InitStartFunc)
        self.lib.setInitStartCallback(self.init_start_func)

    def play_sound_file(self, filename):
        """
        PCM音频文件播放回调
        注：某些情况下会失败，不建议使用，建议使用aplay命令播放

        参数说明:
        filename - pcm音频文件
        """
        with open(filename, 'rb') as f:  # 声卡启动中启动成功嗯我在好的
            tts = f.read()

        self.lib.read_and_play1(tts, len(tts))

    def get_device_id(self):
        """
        获取音频设备id
        :return: 返回设备id号
        """
        try:
            pattern = re.compile(r'.*card (.*?): .*, device (.*?): USB Audio.*')
            dev_cmd = "aplay -l"
            res_content = subprocess.getstatusoutput(dev_cmd)
            if res_content[0] == 0 and res_content[1] != '':
                result = pattern.findall(res_content[1])
                if result:
                    return result[0]
                else:
                    return ''
            else:
                return ''
        except Exception as e:
            print('系统错误，获取设备id失败：' + str(e))
            return ''

    def led_light(self, ledNum, degree, ledstatus, workmode):
        """
        唤醒成功回调

        参数说明:
        ledNum - 点亮的led号
        degree - 声源角度
        ledstatus - 灯转态
        workmode - 0，无引擎模式，1，离线语音模式，2在线语音模式
        """
        print(ledNum, "-------------", degree, "----------------------", ledstatus, "---------------------", workmode)
        # self.lib.createAsrAgent()
        self.lib.createAsrAgentNew(2000)
        self.lib.startToRecordDenoisedSound()
        self.error = 0
        self.play_text("我在")
        if workmode == 2:
            reportWord = "恩?我在!"
            print(reportWord)
            self.lib.gWackUp()
            self.lib.gTTS(reportWord.encode('utf-8'))

    def run_switch(self):
        """
        切换工作模式

        参数说明:
        workmode - 1：切换到离线语音模式，2：切换到在线语音模式
        """
        print("------------>:切换设备模式")
        time.sleep(3)
        self.lib.switch2offlineMode()

    def init_dev_done(self):
        """
        初始化声卡设备完成回调
        """
        print("+++++++>:设备启动成功")
        if self.gWorkMode == 1:
            self.play_text("欢迎使用，边缘计算平台，您可以说：小陆小陆，唤醒我")
            # self.sound_broadcast("configs/welcome.pcm")
        # 退出主循环
        # self.lib.mainLoopDiscard()
        # switchFunc = threading.Thread(target=runSwitch)
        # switchFunc.start()

    def offline_agent_sleep(self):
        """
        离线引擎休眠回调
        """
        global word_str
        print("------------>:离线模式下,已经休眠，请重新唤醒")
        if not self.sucess:
            self.play_text("无法识别，请重新唤醒")
            word_str = ""
            # self.sound_broadcast("configs/error.pcm")
        return

    def sound_record_finish(self):
        """
        声音录制完成时回调
        """
        # print("------------>:重置离线引擎中,准备新一轮识别")
        return

    def effective_ans(self, isSuccess, confidence, word, result):
        """
        离线识别回调

        参数识别:
        isSuccess - 是否识别成功
        confidence - 置信度
        word - 识别到的文字内容
        result - 识别后的报文，包含识别到的文字内容
        """
        global word_str
        word_str = word.decode("utf-8")
        print(word_str)
        res_str = result.decode("utf-8")
        self.sucess = 0
        if isSuccess is not True:
            # self.error += 1
            # if self.error == 4:
            #     print("agent reser!!!!!!!!!")
            # self.sound_broadcast('无法识别，请重试')

            self.lib.deleteAsrAgent()
            # self.lib.createAsrAgent()
            self.lib.createAsrAgentNew(2000)
        if isSuccess is True:
            self.error = 0
            self.sucess = 1
            # self.sound_broadcast("configs/success.pcm")
            # time.sleep(2)
            self.lib.finishToRecordDenoisedSound()
            self.lib.deleteAsrAgent()
            # self.lib.createAsrAgent()
            # self.lib.createAsrAgentNew(2000)
            # self.lib.startToRecordDenoisedSound()
            # self.PlaySoundFile("configs/success.pcm")
            # time.sleep(3)
            print(isSuccess, "+++++++++++++++++", confidence, "+++++++++++++++++++", str)
            print(res_str)

    def nlp_event_callback(self, eventInfo, resultString):
        """
        在线语音识别问与答内容回调

        参数说明:
        eventInfo - 识别事件报文回调
        resultString - 包含问与答文字内容报文回调
        """
        eventStr = eventInfo.decode("utf-8")
        resStr = resultString.decode("utf-8")
        skill_id = "\"OS1763379980.sleep1\"\n"
        reportWord = '好的,那我先走了!'
        if resultString == skill_id:
            self.lib.gSleep()
            self.lib.gTTS(reportWord.encode('utf-8'))
        if len(resultString) > 20:
            print(eventStr, "-----and-----", resStr)

    def tts_event_callback(self, eventInfo):
        """
        在线语音识别回答内容内容回调，库内部负载pcm数据的直接播报

        参数说明:
        eventInfo - 识别事件报文回调，包括单次回答pcm语音结果的回调
        """
        eventStr = eventInfo.decode("utf-8")
        print(eventStr)

    def wakeup_word_Callback(self, result):
        """
        唤醒词设置结果的回调

        Parameters:
        result - 唤醒词是否设置成功
        """
        if result == 0:
            print("set wakeup word success!")
        else:
            print("set wakeup word failed!")

    def init_start_callback(self):
        """
        设备初始化开始回调
        """
        if self.gWorkMode == 1:
            self.play_text("声卡启动中")
            # self.PlaySoundFile("configs/声卡启动中.pcm")

    def broadcast(self, text):
        """
        语音合成
        :param text: 文本内容
        :return: 返回状态值，与信息
        """
        try:
            print('语音合成开始')
            broadcast_cmd = 'cd ' + self.voice_broadcast + " && ./tts_offline_sample {}".format(text)
            res_content = subprocess.getstatusoutput(broadcast_cmd)
            if res_content[0] == 0 and '合并成功' in res_content[1]:
                return 1, '语音合并成功'
            else:
                return 0, '语音合并失败'
        except Exception as e:
            print('系统错误，语音合成失败：' + str(e))
            return 0, '系统错误，语音合成播报失败：' + str(e)

    def play_sound(self, dev_id):
        """
        语音播报
        :param dev_id: 设备id号
        :return: 返回布尔值
        """
        try:
            play_cmd = 'cd ' + self.voice_broadcast + " && aplay -Dplughw:{},{} tts_sample.wav".format(dev_id[0],
                                                                                                       dev_id[1])
            res_content = subprocess.getstatusoutput(play_cmd)
            if res_content[0] == 0 and "Playing WAVE 'tts_sample.wav'" in res_content[1]:
                return True
            else:
                return False
        except Exception as e:
            print('系统错误，播报失败：' + str(e))

    def sound_broadcast(self, pcm_path):
        """

        """
        dev_id = self.get_device_id()
        if dev_id:
            try:
                play_cmd = "aplay -Dplughw:{},{} -f S16_LE -r 16000 {}".format(dev_id[0], dev_id[1], pcm_path)
                res_content = subprocess.getstatusoutput(play_cmd)
                if res_content[0] == 0 and "Playing raw data '{}'".format(pcm_path) in res_content[1]:
                    print(True)
                    return True
                else:
                    return False
            except Exception as e:
                print('系统错误，播报失败：' + str(e))

    def play_text(self, text):
        """
        语音合成并播报
        """
        dev_id = self.get_device_id()
        if dev_id:
            ret = self.broadcast(text)
            print(ret)
            ret2 = self.play_sound(dev_id)
            print(ret2)


OPEN = "打开"
CLOSE = "关闭"
CLASSSIFY = ["物品分类识别", "物品分类"]
DETECT = ["物品目标检测", "目标检测"]
CAR = ["车牌识别"]
FACE = ["人脸识别"]
FACEATTR = ["人脸属性识别", "人脸属性"]
SMARTHOME = ["智能家居"]
STAR = ["趣味明星脸"]
RUBBISH = ["智能垃圾分类", "垃圾分类"]
PARK = ["智能停车场", "停车场"]
EPIDEMIC = ["疫情防控检测站", "疫情防控"]
BONE = ["人体关键点", "骨骼描点"]
SET = ["设置"]
FAN = ["风扇"]
LED = ["红灯", "黄灯", "绿灯", "灯"]


class speechControlThread(QThread):
    """
    语音识别结果获取线程
    """
    
    def __init__(self):
        QThread.__init__(self)
        xunfei_mic=Xunfei6MicHelper()
        invalidSound=xunfei_mic.invalidSound
        recognizeFail=xunfei_mic.recognizeFail
        sec=xunfei_mic.sec
        dev_id = xunfei_mic.get_device_id()
        if dev_id:
            devName = 'plughw:{},{}'.format(dev_id[0], dev_id[1])
        else:
            devName = 'plughw:1,0'
        xunfei_mic.set_wakeup_info_callback(xunfei_mic.led_light)
        xunfei_mic.set_offline_agent_sleep_callback(xunfei_mic.offline_agent_sleep)
        xunfei_mic.set_sound_record_finish_callback(xunfei_mic.sound_record_finish)
        xunfei_mic.set_effective_ans_callback(xunfei_mic.effective_ans)
        xunfei_mic.set_nlp_event_callback(xunfei_mic.nlp_event_callback)
        xunfei_mic.set_tts_event_callback(xunfei_mic.tts_event_callback)
        xunfei_mic.set_init_dev_done_callback(xunfei_mic.init_dev_done)
        xunfei_mic.SetBeforeSetWakeupWordCallback(xunfei_mic.before_set_wakeup_word_func)
        xunfei_mic.set_wakeup_work_callback(xunfei_mic.wakeup_word_Callback)
        xunfei_mic.set_init_start_callback(xunfei_mic.init_start_callback)
        xunfei_mic.start(invalidSound, recognizeFail, sec, devName)

        self.xunfei = xunfei_mic
        self.new_qs = NewQuerySerial('/dev/ttyS0')
        self.new_qs.reset()
        # led状态
        self.red_state = False
        self.yellow_state = False
        self.green_state = False
        self.fan_state = False
        self.working = True

    def __del__(self):
        self.wait()

    def sence_solve(self, result):
        if result in [OPEN + s for s in FAN]:
            if not self.fan_state:
                self.xunfei.play_text("好的，正在" + result)
                self.new_qs.turn_on_fan()
                self.fan_state = True
            else:
                self.xunfei.play_text("风扇已打开")

        elif result in [CLOSE + s for s in FAN]:
            if self.fan_state:
                self.fan_state = False
                self.xunfei.play_text("好的，正在" + result)
                self.new_qs.turn_off_fan()
            else:
                self.xunfei.play_text("风扇已关闭")

        elif result in [OPEN + LED[0]]:
            if not self.red_state:
                self.red_state = True
                self.xunfei.play_text("好的，正在" + result)
                self.new_qs.turn_on_red()
            else:
                self.xunfei.play_text("红灯已打开")

        elif result in [CLOSE + LED[0]]:
            if self.red_state:
                self.red_state = False
                self.xunfei.play_text("好的，正在" + result)
                self.new_qs.turn_off_red()
            else:
                self.xunfei.play_text("红灯已关闭")

        elif result in [OPEN + LED[1], OPEN + LED[3]]:
            if not self.yellow_state:
                self.yellow_state = True
                self.xunfei.play_text("好的，正在" + result)
                self.new_qs.turn_on_yellow()
            else:
                self.xunfei.play_text("黄灯已打开")

        elif result in [CLOSE + LED[1], CLOSE + LED[3]]:
            if self.yellow_state:
                self.yellow_state = False
                self.xunfei.play_text("好的，正在" + result)
                self.new_qs.turn_off_yellow()
            else:
                self.xunfei.play_text("黄灯已关闭")

        elif result in [OPEN + LED[2]]:
            if not self.green_state:
                self.green_state = True
                self.xunfei.play_text("好的，正在" + result)
                self.new_qs.turn_on_green()
            else:
                self.xunfei.play_text("绿灯已打开")

        elif result in [CLOSE + LED[2]]:
            if self.green_state:
                self.green_state = False
                self.xunfei.play_text("好的，正在" + result)
                self.new_qs.turn_off_green()
            else:
                self.xunfei.play_text("绿灯已关闭")

        else:
            self.xunfei.play_text("无法识别，请重新唤醒我")


    def run(self):
        global word_str
        while self.working:
            try:
                # print(word_str)
                result = word_str
                if result:
                    if result in [OPEN + s for s in CLASSSIFY]:
                        self.xunfei.play_text("好的，正在" + result)
                        # self.result_signal.emit("classify")
                    elif result in [OPEN + s for s in DETECT]:
                        self.xunfei.play_text("好的，正在" + result)
                        # self.result_signal.emit("detect")
                    elif result in [OPEN + s for s in CAR]:
                        self.xunfei.play_text("好的，正在" + result)
                        # self.result_signal.emit("car")
                    elif result in [OPEN + s for s in FACE]:
                        self.xunfei.play_text("好的，正在" + result)
                        # self.result_signal.emit("face")
                    elif result in [OPEN + s for s in FACEATTR]:
                        self.xunfei.play_text("好的，正在" + result)
                        # self.result_signal.emit("faceAttr")
                    elif result in [OPEN + s for s in SMARTHOME]:
                        self.xunfei.play_text("好的，正在" + result)
                        # self.result_signal.emit("smartHome")
                    elif result in [OPEN + s for s in STAR]:
                        self.xunfei.play_text("好的，正在" + result)
                        # self.result_signal.emit("star")
                    elif result in [OPEN + s for s in RUBBISH]:
                        self.xunfei.play_text("好的，正在" + result)
                        # self.result_signal.emit("rubbish")
                    elif result in [OPEN + s for s in PARK]:
                        self.xunfei.play_text("好的，正在" + result)
                        # self.result_signal.emit("parking")
                    elif result in [OPEN + s for s in EPIDEMIC]:
                        self.xunfei.play_text("好的，正在" + result)
                        # self.result_signal.emit("epidemic")
                    elif result in [OPEN + s for s in BONE]:
                        self.xunfei.play_text("好的，正在" + result)
                        # self.result_signal.emit("bone")
                    elif result in [OPEN + s for s in SET]:
                        self.xunfei.play_text("好的，正在" + result)
                        # self.result_signal.emit("set")
                    else:
                        self.sence_solve(result)
                    word_str = ""
            except Exception as e:
                print('VoiceThread: ' + str(e))
            time.sleep(0.1)

    def stop(self):
        global word_str
        if self.working:
            word_str = ""
            self.working = False
            self.new_qs.turn_off_red()
            time.sleep(0.5)
            self.new_qs.turn_off_yellow()
            time.sleep(0.5)
            self.new_qs.turn_off_green()
            time.sleep(0.5)
            self.new_qs.turn_off_fan()
            time.sleep(0.5)
            self.new_qs.close_serial()
            del self.xunfei.devMainLoop
            del self.xunfei
            print('已退出语音控制线程!')
