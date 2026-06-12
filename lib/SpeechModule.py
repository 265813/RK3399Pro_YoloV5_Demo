# -*- coding: UTF-8 -*-
import re
import subprocess
import time
BASE_PATH = '/usr/local'  # 语音目录
# BASE_PATH = './'  # 语音目录

class SpeechSolve(object):

    def __init__(self):
        self.voice_broadcast = BASE_PATH + '/speech/broadcast/bin/'
        self.voice_recognition = BASE_PATH + '/speech/recognition/bin/'

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

    def broadcast(self, text):
        """
        语音合成
        :param text: 文本内容
        :return: 返回状态值，与信息
        """
        try:
            # print('语音合成开始')
            broadcast_cmd = 'cd ' + self.voice_broadcast + " && chmod +x tts_offline_sample && ./tts_offline_sample {}".format(text)
            res_content = subprocess.getstatusoutput(broadcast_cmd)
            if res_content[0] == 0 and '合并成功' in res_content[1]:
                print('语音合成成功，开始播报!')
                dev_id=self.get_device_id()
                ret=self.play_sound(dev_id)
            else:
                print('语音合并失败',res_content)
        except Exception as e:
            print('系统错误，语音合成失败：' + str(e))
            # return 0, '系统错误，语音合成播报失败：' + str(e)

    def play_sound(self, dev_id):
        """
        语音播报
        :param dev_id: 设备id号
        :return: 返回布尔值
        """
        try:
            play_cmd = 'cd ' + self.voice_broadcast + " && aplay -Dplughw:{},{} tts_sample.wav".format(dev_id[0], dev_id[1])
            res_content = subprocess.getstatusoutput(play_cmd)
            if res_content[0] == 0 and "Playing WAVE 'tts_sample.wav'" in res_content[1]:
                return True
            else:
                return False
        except Exception as e:
            print('系统错误，播报失败：' + str(e))
            return False

    def recognition(self):
        """
        语音识别
        :return: 返回识别结果，或者None
        """
        try:
            pattern = re.compile(r'<rawtext>(.*?)</rawtext>')
            recognition_cmd = 'cd ' + self.voice_recognition + ' && chmod +x asr_offline_record_sample && ./asr_offline_record_sample'
            print('正在监听......')
            time.sleep(0.5)
            res_content = subprocess.getstatusoutput(recognition_cmd)
            if res_content[0] == 0 and 'Result' in res_content[1]:
                result = pattern.findall(res_content[1])
                # print(result)
                if result:
                    return result[0]
                else:
                    return None
            else:
                return None
        except Exception as e:
            print('系统错误，识别失败：' + str(e))
            return None
