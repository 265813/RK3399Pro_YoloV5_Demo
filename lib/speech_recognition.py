import time, os, sys, signal
import ctypes
from ctypes import CFUNCTYPE, c_char_p, c_int, c_uint8, POINTER, Structure, c_void_p, c_uint
import atexit
import json
# sys.path.append('lib')
from lib.asr_service import ASRService, pcm_to_wav
import numpy as np
import subprocess
import wave
import serial
import threading

try:
    import sounddevice as sd
except:
    pass


# 定义业务消息结构体
class business_msg_t(Structure):
    _fields_ = [
        ("handle", c_uint),  # unsigned char
        ("version", c_uint8),  # unsigned char
        ("opcode", c_uint8),  # unsigned char
        ("modId", c_uint8),  # unsigned char
        ("msgId", c_uint8),  # unsigned char
        ("data", POINTER(c_uint8)),  # unsigned char *data
        ("length", c_int)  # int
    ]


class MicrophoneController:
    def __init__(self, mode=0):
        # 实例化语音识别对象
        self.mode = mode
        if self.mode:  # 启动语音识别功能
            self.service = ASRService('resources/config.yaml')

        # 添加共享库
        self.lib = ctypes.CDLL('/usr/lib/libhid_lib.so')
        # 获取lib的全局变量
        self.is_boot = ctypes.c_int.in_dll(self.lib, 'is_boot')
        # 定义lib内变量及函数映射
        self._setup_ctypes_functions()
        # 必要资源路径
        self.SYSTEM_CONFIG_PATH = b"resources/microphone/config.txt"
        self.SYSTEM_PATH = b"resources/microphone/system.tar"

        # 函数执行结果
        self.exe_results = 255

        # 原始音频流接收回调
        self.original_audio_callback = None
        self.original_audio_save_path = None

        # 降噪音频流接收回调
        self.denoised_audio_callback = None
        self.denoised_audio_save_path = None

        # 唤醒回调
        self.awake_callback = None

        # 麦克风状态
        self.if_awake = False  # 麦克风是否唤醒
        self.major_mic_id = -1  # 主麦ID
        self.deno_recording = False  # 录音中标志
        self.ori_recording = False  # 录音中标志

        # 关闭麦克风
        # self.close()
        self.lib.hid_close()
        # 打开麦克风
        if self.open():
            print(">>>>>打开麦克风成功")
        else:
            print(">>>>>打开麦克风失败")
        if self.start():
            print(">>>>>启动麦克风成功")
            self.set_major_mic(0)  # 默认主麦id为0
            word = '小陆小陆'  # 自动设置离声源最近的麦为主麦的词
            print(f">>>>>说{word}可以自动设置离声源最近的音口为主麦")
            self.set_awake_word(word)
        else:
            if self.start():
                print(">>>>>启动麦克风成功")
                word = '小陆小陆'  # 唤醒麦克风的词
                print(f">>>>>说{word}可以自动设置离声源最近的音口为主麦")
                self.set_awake_word(word)
            else:
                print(">>>>>启动麦克风失败")
                self.close()

    # 打开麦克风设备
    def open(self):
        handle = self.lib.hid_open()
        if not handle:
            print("无法打开麦克风设备, 请检查设备连接")
            return False
        status = self.lib.protocol_proc_init(self.send_to_usb_device_c, self.recv_from_usb_device_c,
                                             self.business_proc_callback, self.err_proc)
        if status == 0:
            print("初始化成功")
        else:
            print("初始化失败")
            return False
        return True

    # 关闭麦克风设备
    def close(self):
        # self.lib.hid_close()
        print(">>>>>已关闭麦克风")
        pid = os.getpid()  # 获取当前进程的PID
        os.kill(pid, signal.SIGTERM)  # 主动结束指定ID的程序运行

    # 启动麦克风
    def start(self):
        self.exe_results = 255
        self.lib.get_system_status()
        if self.wait_for_status(timeout=5) == False:
            return False
        if self.exe_results == 0:
            time.sleep(1)
            return True
        time.sleep(6)
        self.exe_results = 255
        self.lib.get_system_status()
        time.sleep(1)
        return self.wait_for_status(timeout=3)

    # 设置唤醒词
    def set_awake_word(self, word):
        self.exe_results = 255
        self.lib.set_awake_word(word.encode('utf-8'))
        return self.wait_for_status(timeout=3)

    # 设置麦克风主麦
    def set_major_mic(self, mic_id):
        self.exe_results = 255
        self.lib.set_major_mic_id(mic_id)
        if self.wait_for_status() == False:
            return False
        led_id = self.lib.get_led_based_mic_id(mic_id)
        if led_id < 0:
            return False
        self.exe_results = 255
        self.lib.set_target_led_on(led_id)
        if self.wait_for_status() == False:
            return False
        self.if_awake = True
        self.major_mic_id = mic_id
        return True

    # 启动原始音频录制
    def start_record_original(self, callback=None, path=None):
        self.exe_results = 255
        self.original_audio_callback = callback
        self.original_audio_save_path = path
        self.lib.start_to_record_original_sound()
        if self.wait_for_status() == False:
            return False
        self.ori_recording = True
        return True

    # 停止原始音频录制
    def stop_record_original(self):
        self.exe_results = 255
        self.lib.finish_to_record_original_sound()
        self.ori_recording = False
        return self.wait_for_status()

    # 启动降噪音频录制
    def start_record_denoised(self, callback=None, path=None):
        self.exe_results = 255
        self.denoised_audio_callback = callback
        self.denoised_audio_save_path = path
        self.lib.start_to_record_denoised_sound()
        return self.wait_for_status()

    # 停止降噪音频录制
    def stop_record_denoised(self):
        self.exe_results = 255
        self.lib.finish_to_record_denoised_sound()
        return self.wait_for_status()

    # 获取主麦ID
    def get_major_mic_id(self):
        self.exe_results = 255
        self.lib.get_major_mic_id()
        if self.wait_for_status():
            return self.major_mic_id
        return -1

    def set_awake_callback(self, callback=None):
        self.awake_callback = callback

    def wait_for_status(self, timeout=1):
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.exe_results >= 0 and self.exe_results != 255:
                return True
            elif self.exe_results < 0:
                return False
            time.sleep(0.1)  # 每隔100毫秒检查一次状态
        return False

    def _setup_ctypes_functions(self):
        # 定义hid_open函数的参数类型和返回类型
        self.lib.hid_open.argtypes = []
        self.lib.hid_open.restype = ctypes.c_void_p

        # 定义回调函数类型
        self.pfunc_send_msg = CFUNCTYPE(c_int, POINTER(c_uint8), c_int)
        self.pfunc_recv_msg = CFUNCTYPE(c_int, POINTER(c_uint8), c_int)
        self.pfunc_business_proc_callback = CFUNCTYPE(c_int, business_msg_t)
        self.pfunc_err_proc = CFUNCTYPE(None, c_char_p)

        # 定义函数原型
        # get_software_version
        self.lib.get_software_version.restype = ctypes.c_char_p
        # whether_upgrade_succeed
        self.lib.whether_upgrade_succeed.argtypes = [ctypes.POINTER(ctypes.c_ubyte)]
        self.lib.whether_upgrade_succeed.restype = None
        # send_resource
        self.lib.send_resource.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_char_p, ctypes.c_int]
        self.lib.send_resource.restype = None
        # send_resource_info
        self.lib.send_resource_info.argtypes = [ctypes.c_char_p, ctypes.c_int]
        self.lib.send_resource_info.restype = None

        # get_original_sound
        self.lib.get_original_sound.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_ubyte)]
        self.lib.get_original_sound.restype = ctypes.c_int
        # get_denoised_sound
        self.lib.get_denoised_sound.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_ubyte)]
        self.lib.get_denoised_sound.restype = ctypes.c_int

        # whether_set_succeed
        self.lib.whether_set_succeed.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.POINTER(ctypes.c_ubyte)]
        self.lib.whether_set_succeed.restype = ctypes.c_int
        # whether_set_resource_info
        self.lib.whether_set_resource_info.argtypes = [ctypes.POINTER(ctypes.c_ubyte)]
        self.lib.whether_set_resource_info.restype = None
        # set_awake_word
        self.lib.set_awake_word.argtypes = [ctypes.c_char_p]
        self.lib.set_awake_word.restype = ctypes.c_int

        # get_protocol_version
        self.lib.get_protocol_version.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.POINTER(ctypes.c_char)]
        self.lib.get_protocol_version.restype = ctypes.c_int

        # get_awake_mic_id
        self.lib.get_awake_mic_id.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.POINTER(ctypes.c_ubyte)]
        self.lib.get_awake_mic_id.restype = ctypes.c_int

        # get_awake_mic_angle
        self.lib.get_awake_mic_angle.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.POINTER(ctypes.c_ubyte)]
        self.lib.get_awake_mic_angle.restype = ctypes.c_int

        # get_led_based_angle
        self.lib.get_led_based_angle.argtypes = [ctypes.c_int]
        self.lib.get_led_based_angle.restype = ctypes.c_int

        # set_major_mic_id
        self.lib.set_major_mic_id.argtypes = [ctypes.c_int]
        self.lib.set_major_mic_id.restype = ctypes.c_int

        # set_target_led_on
        self.lib.set_target_led_on.argtypes = [ctypes.c_int]
        self.lib.set_target_led_on.restype = ctypes.c_int

        # whether_set_awake_word
        self.lib.whether_set_awake_word.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.POINTER(ctypes.c_ubyte)]
        self.lib.whether_set_awake_word.restype = ctypes.c_int

        # 定义Python回调函数
        self.business_proc_callback = self.pfunc_business_proc_callback(self.business_proc_callback_impl)
        self.err_proc = self.pfunc_err_proc(self.err_proc_impl)

        # 获取C库中的send_to_usb_device和recv_from_usb_device函数
        self.send_to_usb_device_c = self.lib.send_to_usb_device
        self.recv_from_usb_device_c = self.lib.recv_from_usb_device

        # 设置C库函数的参数类型和返回类型
        self.send_to_usb_device_c.argtypes = [POINTER(c_uint8), c_int]
        self.send_to_usb_device_c.restype = c_int
        self.recv_from_usb_device_c.argtypes = [POINTER(c_uint8), c_int]
        self.recv_from_usb_device_c.restype = c_int

        # 将C库中的函数转换为CFUNCTYPE实例
        self.send_to_usb_device_c = self.pfunc_send_msg(self.send_to_usb_device_c)
        self.recv_from_usb_device_c = self.pfunc_recv_msg(self.recv_from_usb_device_c)

        # 定义protocol_proc_init函数的参数类型和返回类型
        self.lib.protocol_proc_init.argtypes = [self.pfunc_send_msg, self.pfunc_recv_msg,
                                                self.pfunc_business_proc_callback, self.pfunc_err_proc]
        self.lib.protocol_proc_init.restype = c_int

    def businessMsg_mod1(self, businessMsg):
        # 开启降噪音频录制返回结果
        if businessMsg.msgId == 0x01:
            key = (ctypes.c_ubyte * 8)(*[ord(c) for c in "errcode"])
            self.exe_results = self.lib.whether_set_succeed(businessMsg.data, key)
        # 降噪录音音频流
        elif businessMsg.msgId == 0x02:
            self.deno_recording = True
            # 降噪音频: 采样率 16khz,  16bit
            if self.denoised_audio_callback != None:
                pcm_data = bytes(businessMsg.data[:businessMsg.length])
                self.denoised_audio_callback(pcm_data)
            if self.denoised_audio_save_path != None:
                self.lib.get_denoised_sound(self.denoised_audio_save_path.encode('utf-8'), businessMsg.data)
        # 关闭降噪音频录制返回结果
        elif businessMsg.msgId == 0x03:
            self.deno_recording = False
            key = (ctypes.c_ubyte * 8)(*[ord(c) for c in "errcode"])
            self.exe_results = self.lib.whether_set_succeed(businessMsg.data, key)
        # 开启/关闭原始音频录制返回结果
        elif businessMsg.msgId == 0x04:
            key = (ctypes.c_ubyte * 8)(*[ord(c) for c in "errcode"])
            self.exe_results = self.lib.whether_set_succeed(businessMsg.data, key)
        # 设置主麦克风和灯光返回结果
        elif businessMsg.msgId == 0x05:
            key = (ctypes.c_ubyte * 8)(*[ord(c) for c in "errcode"])
            self.exe_results = self.lib.whether_set_succeed(businessMsg.data, key)
        # 原始音频流
        elif businessMsg.msgId == 0x06:
            # 原始音频: 采样率 16khz,  32bit, 为八通道, 其中 1-6 通道对应 6 个麦克风, 7-8 是参考信号
            if self.original_audio_callback != None:
                pcm_data = bytes(businessMsg.data[:businessMsg.length])
                self.original_audio_callback(pcm_data)
            if self.original_audio_save_path != None:
                self.lib.get_original_sound(self.original_audio_save_path.encode('utf-8'), businessMsg.data)
        # 获取主麦克风ID返回结果
        elif businessMsg.msgId == 0x07:
            key2 = (ctypes.c_ubyte * 5)(*[ord(c) for c in "beam"])
            major_id = self.lib.whether_set_succeed(businessMsg.data, key2)
            self.major_mic_id = major_id
            print(f">>>>>主麦克风id为{self.major_mic_id}")
            self.exe_results = 0
        # 设置主麦克风返回结果
        elif businessMsg.msgId == 0x08:
            key = (ctypes.c_ubyte * 8)(*[ord(c) for c in "errcode"])
            status = self.lib.whether_set_succeed(businessMsg.data, key)
            if status == 0:
                print(">>>>>设置主麦克风成功")
                self.exe_results = status
        # 设置灯光返回结果
        elif businessMsg.msgId == 0x09:
            key = (ctypes.c_ubyte * 8)(*[ord(c) for c in "errcode"])
            status = self.lib.whether_set_succeed(businessMsg.data, key)
            if status == 0:
                print(">>>>>设置灯光成功")
                self.exe_results = status

    def businessMsg_mod2(self, businessMsg):
        if businessMsg.msgId == 0x01:  # 麦克风唤醒返回结果
            key1 = b"beam"
            key2 = b"angle"
            # 分配内存给 key1 和 key2
            key1_c = (ctypes.c_ubyte * len(key1)).from_buffer_copy(key1)
            key2_c = (ctypes.c_ubyte * len(key2)).from_buffer_copy(key2)

            self.major_mic_id = self.lib.get_awake_mic_id(businessMsg.data, key1_c)
            mic_angle = self.lib.get_awake_mic_angle(businessMsg.data, key2_c)

            if 0 <= self.major_mic_id <= 5 and 0 <= mic_angle <= 360:
                led_id = self.lib.get_led_based_angle(mic_angle)
                ret1 = self.lib.set_major_mic_id(self.major_mic_id)
                ret2 = self.lib.set_target_led_on(led_id)
                if ret1 == 0 and ret2 == 0:
                    print(f">>>>>第{self.major_mic_id}个麦克风被唤醒")
                    print(f">>>>>唤醒角度为:{mic_angle}")
                    print(f">>>>>已点亮{led_id}灯")
                    if self.awake_callback != None:
                        self.awake_callback()

        elif businessMsg.msgId == 0x08:  # 设置唤醒词返回结果
            key1 = b"errstring"
            # 分配内存给 key1
            key1_c = (ctypes.c_ubyte * len(key1)).from_buffer_copy(key1)
            self.exe_results = self.lib.whether_set_awake_word(businessMsg.data, key1_c)

    def businessMsg_mod3(self, businessMsg):
        if businessMsg.msgId != 0x01:
            return
        # 定义key
        key = (ctypes.c_ubyte * 7)(*[ord(c) for c in "status"])
        # 调用whether_set_succeed函数
        status = self.lib.whether_set_succeed(businessMsg.data, key)
        # 定义protocol_version
        protocol_version = (ctypes.c_char * 40)()
        # 调用get_protocol_version函数
        ret = self.lib.get_protocol_version(businessMsg.data, protocol_version)
        # 获取软件版本
        software_version = self.lib.get_software_version().decode('utf-8')
        # 获取软件版本
        print(
            f">>>>>麦克风{(status == 0 and '正常工作' or '正在启动')},软件版本为:{software_version},协议版本为:{protocol_version.value.decode('utf-8')}")
        if status == 1:
            file_name = self.SYSTEM_CONFIG_PATH
            self.lib.send_resource_info(file_name, 0)
        else:
            self.is_boot.value = 1
            self.exe_results = 0

    def businessMsg_mod4(self, businessMsg):
        if businessMsg.msgId == 0x01:
            self.lib.whether_set_resource_info(businessMsg.data)
        elif businessMsg.msgId == 0x03:  # 文件接收结果
            self.lib.whether_set_resource_info(businessMsg.data)
        elif businessMsg.msgId == 0x04:  # 查看设备升级结果
            self.lib.whether_upgrade_succeed(businessMsg.data)
            json_data = ctypes.string_at(businessMsg.data).decode('utf-8')
            data_dict = json.loads(json_data)
            if data_dict['result'] == 0:
                self.exe_results = 1
        elif businessMsg.msgId == 0x05:  # 下发文件
            file_name = self.SYSTEM_PATH
            self.lib.send_resource(businessMsg.data, file_name, 1)
        elif businessMsg.msgId == 0x08:  # 获取升级配置文件
            try:
                print(f"config.json: {ctypes.string_at(businessMsg.data).decode('utf-8')}")
            except Exception as e:
                print(f"businessMsg.msgId == 0x08")

    def business_proc_callback_impl(self, businessMsg):
        if businessMsg.modId == 0x01:
            self.businessMsg_mod1(businessMsg)
        elif businessMsg.modId == 0x02:
            self.businessMsg_mod2(businessMsg)
        elif businessMsg.modId == 0x03:
            self.businessMsg_mod3(businessMsg)
        elif businessMsg.modId == 0x04:
            self.businessMsg_mod4(businessMsg)
        return 0  # 成功

    def err_proc_impl(self, err):
        print(f"Error: {err}")

    def deno_audio_callback(self, pcm_data):
        self.audio_data.append(pcm_data)

    def broadcast(self, text):
        # 调用语音合成接口的指令
        tts_cmd = 'cd ./speech/broadcast/bin/ && chmod +x tts_offline_sample' + ' && ./tts_offline_sample {}'.format(
            text)
        # 语音合并并获取返回值
        res_content = subprocess.getstatusoutput(tts_cmd)
        # 如果合并成功
        if res_content[0] == 0 and '合并成功' in res_content[1]:
            print('语音合成成功，开始播报!')
            # 使用aplay播放语音
            broadcast_cmd = 'aplay ./speech/broadcast/bin/tts_sample.wav -D plughw:Device'
            subprocess.Popen(broadcast_cmd, shell=True)
        else:
            print('语音合成失败!')

    def recognition(self, sec=4):
        self.audio_data = []  # 音频流存储
        print(">>>>>监听中")
        time.sleep(0.5)
        self.start_record_denoised(self.deno_audio_callback)
        time.sleep(sec)
        self.stop_record_denoised()
        print(">>>>>监听结束")
        all_pcm_data = b''.join(self.audio_data)
        audio_data = np.frombuffer(all_pcm_data, dtype=np.int16)
        result = self.service.infer((audio_data, 16000))
        return result

    def record(self, filepath='output.pcm', sec=4):
        if os.path.exists(filepath):
            os.remove(filepath)
            time.sleep(0.5)
        self.audio_data = []  # 音频流存储
        print(">>>>>录制中")
        time.sleep(0.5)
        self.start_record_denoised(self.deno_audio_callback, filepath)
        time.sleep(sec)
        self.stop_record_denoised()
        print(">>>>>录制结束")
        print(f"播放音频命令:aplay {filepath} -r 16000 -f S16_LE -c 1 -D plughw:Device")

    def pcm_to_wav(self, pcm_file, wav_file, channels=1, sample_width=2, sample_rate=16000):
        """
        将PCM文件转换为WAV文件。

        :param pcm_file: 输入的PCM文件路径。
        :param wav_file: 输出的WAV文件路径。
        :param channels: 声道数（默认为1，即单声道）。
        :param sample_width: 采样宽度（字节），通常为2（16位）。
        :param sample_rate: 采样率（Hz），例如16000表示16kHz。
        """
        with open(pcm_file, 'rb') as pcm_file_handle:
            pcm_data = pcm_file_handle.read()

        # 使用numpy将二进制数据转换为合适的格式，这里假设是16位整型数据
        audio_data = np.frombuffer(pcm_data, dtype=np.int16)

        with wave.open(wav_file, 'w') as wf:
            wf.setnchannels(channels)  # 设置声道数
            wf.setsampwidth(sample_width)  # 设置采样宽度（字节）
            wf.setframerate(sample_rate)  # 设置采样率（Hz）
            wf.writeframes(audio_data.tobytes())  # 写入音频数据
        print(">>>>>转换成功")
        print(f"播放音频命令:aplay {wav_file} -D plughw:Device")


class SerialCommunicationProtocol:
    def __init__(self):
        self.sync_header = 0xA5
        self.user_id = 0x01

        self.count = 0
        self.frame_len = 0
        self.frame_data = []

    def calculate_checksum(self, message_bytes):
        # 计算除校验码外的所有字节的和
        checksum = sum(message_bytes) & 0xFF
        # 取反并加1得到校验码
        return (~checksum + 1) & 0xFF

    def judge_frame_recv_ok(self, data):
        # 找到帧头
        if self.count == 0 and data == self.sync_header:
            self.count = 1
            self.frame_data.clear()
            self.frame_data.append(data)
            return None
        elif self.count == 1:
            if data == self.user_id:  # 找到用户ID
                self.count = 2
                self.frame_data.append(data)
            else:  # 未找到用户ID，丢弃帧数据
                self.frame_data.clear()
                self.count = 0
            return None

        if self.count > 1:
            self.count += 1
            self.frame_data.append(data)

        if self.count == 5:  # 此时应该已接收到消息长度
            self.frame_len = int.from_bytes(self.frame_data[3:5], byteorder='little')
            return None

        if self.count == (self.frame_len + 8):  # 此时帧数据应该已接收完成
            self.count = 0
            return self.frame_data

        return None

    def parse_message(self, message_bytes):
        if len(message_bytes) < 7:
            return None

        sync_header = message_bytes[0]
        user_id = message_bytes[1]
        message_type = message_bytes[2]
        message_length = int.from_bytes(message_bytes[3:5], byteorder='little')
        message_id = int.from_bytes(message_bytes[5:7], byteorder='little')
        message_data = message_bytes[7:-1]
        checksum = message_bytes[-1]

        # Validate the message
        if sync_header != self.sync_header or user_id != self.user_id:
            return None

        calculated_checksum = self.calculate_checksum(message_bytes[:-1])
        if calculated_checksum != checksum:
            return None

        if isinstance(message_data, list):
            message_data = bytes(message_data)  # 将列表转换为字节序列

        # 尝试将message_data解码为UTF-8字符串
        try:
            message_data_str = message_data.decode('utf-8')
        except UnicodeDecodeError:
            # 如果解码失败，则保持原始字节数据
            message_data_str = message_data

        return {
            'sync_header': sync_header,
            'user_id': user_id,
            'message_type': message_type,
            'message_length': message_length,
            'message_id': message_id,
            'message_data': message_data_str,
            'checksum': checksum
        }

    def generate_message(self, message_type, message_id, message_data):
        message_length = len(message_data)
        length_bytes = message_length.to_bytes(2, byteorder='little')
        message_id = message_id % 65535

        message_bytes = bytearray([
            self.sync_header,
            self.user_id,
            message_type,
            length_bytes[0],
            length_bytes[1],
            (message_id >> 8) & 0xFF,
            message_id & 0xFF
        ])
        message_bytes.extend(message_data)

        checksum = self.calculate_checksum(message_bytes)
        message_bytes.append(checksum)

        return bytes(message_bytes)

    def get_type_from_message(self, message_str):
        try:
            # 将输入的字符串解析为Python字典
            message = json.loads(message_str['message_data'])
            if not message:
                return None
            type_value = message.get('type')
            return type_value
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            return None
        except Exception as e:
            print(f"处理过程中发生错误: {e}")
            return None

    def get_version_from_message(self, message_str):
        try:
            # 将输入的字符串解析为Python字典
            message = json.loads(message_str['message_data'])
            if not message:
                return None
            version = message.get('content')
            return version
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            return None
        except Exception as e:
            print(f"处理过程中发生错误: {e}")
            return None

    def get_code_from_message(self, message_str):
        try:
            # 将输入的字符串解析为Python字典
            message = json.loads(message_str['message_data'])
            if not message:
                return None
            code = message.get('code')
            return code
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            return None
        except Exception as e:
            print(f"处理过程中发生错误: {e}")
            return None

    def get_keyword_from_message(self, message_str):
        try:
            # 将输入的字符串解析为Python字典
            message = json.loads(message_str['message_data'])
            # 获取info字段的内容，并再次解析为字典
            keyword = message.get('content', {}).get('keyword', '')
            if not keyword:
                return None

            return keyword

        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            return None
        except Exception as e:
            print(f"处理过程中发生错误: {e}")
            return None

    def get_angle_from_message(self, message_str):
        try:
            # 将输入的字符串解析为Python字典
            message = json.loads(message_str['message_data'])
            # 获取info字段的内容，并再次解析为字典
            info_str = message.get('content', {}).get('info', '')
            if not info_str:
                return None

            info = json.loads(info_str)

            # 从info字典中获取angle值
            angle = info.get('ivw', {}).get('angle')

            return angle

        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            return None
        except Exception as e:
            print(f"处理过程中发生错误: {e}")
            return None


# ============================================= 麦克风阵列 =========================================
class MicrophoneController2:
    def __init__(self, uartname="/dev/wheeltec_mic", rec_dev_name="hw:CARD=XFMDPV0018,DEV=0", mode=0):
        self.rec_dev_name = rec_dev_name
        # 串口
        self.uartname = uartname
        self.ser = None
        self.thread = None
        self.running = False
        self.protocol = SerialCommunicationProtocol()
        self.code = 255
        self.handshake = False
        self.msgid = 1000
        # 唤醒
        self.if_awake = 0
        self.angle_int = 0
        self.awake_callback = None
        self.wakeup_keywords = ""
        # 版本信息
        self.version = None
        # 录音
        self.recording = False
        self.stream = None
        self.record_callback = None

        # 实例化语音识别对象
        self.mode = mode
        if self.mode:  # 启动语音识别功能
            self.service = ASRService('resources/config.yaml')
        # 打开麦克风
        print(">>>>>麦克风启动中，请等待")
        ret = self.open()
        if ret == False:
            print(">>>>>麦克风启动失败")
            return
        else:
            print(">>>>>麦克风启动成功")

        # 设置主麦
        mic_id = 0
        ret = self.set_major_mic(mic_id)
        if ret:
            print(f">>>>>设置主麦ID{mic_id}成功")
        else:
            print(f">>>>>设置主麦ID{mic_id}失败")

        # 设置自动将离声源最近的麦设为主麦的词，设置过程需要十几秒的时间，关机后仍可以保留上次设置的唤醒词
        # print('已自动设置主麦的词：',dir(self))
        # word = "xiao3 lu4 xiao3 lu4" # 自动设置离声源最近的麦为主麦的词,拼音+声调，例如：唤醒词“你好小陆”，输入“xiao3 lu4 xiao3 lu4”
        # if len(word) >= 12 :
        #     print("自动设置主麦的词:",word)
        #     print(">>>>>词设置中，请稍等")
        #     ret = self.set_awake_word(word)
        #     if ret :
        #         print(">>>>>词设置成功")
        #         print(f">>>>>说{word}可以自动设置离声源最近的音口为主麦")

    def open(self):
        if self.running == True:
            return True
        try:
            self.handshake = False
            self.ser = serial.Serial(self.uartname, baudrate=115200, timeout=3)
            self.running = True
            self.thread = threading.Thread(target=self.serial_listen)
            self.thread.daemon = True
            self.thread.start()
            return True
        except serial.SerialException as e:
            print(f"Can't Open Serial Port: {e}")
            return False

    def close(self):
        if not self.running:
            return
        self.running = False
        self.thread.join()
        self.ser.close()
        print('>>>>>已关闭麦克风')
        pid = os.getpid()  # 获取当前进程的PID
        os.kill(pid, signal.SIGTERM)  # 主动结束指定ID的程序运行

    def get_link_sta(self):
        return self.handshake

    def set_awake_callback(self, callback=None):
        self.awake_callback = callback

    # 设置唤醒词,内容为拼音+声调，例如：设置唤醒词“你好小陆”，输入work的为"ni2 hao3 xiao3 lu4"
    def set_awake_word(self, word):
        message = {
            "type": "wakeup_keywords",
            "content": {
                "keyword": word,  # 唤醒词
                "threshold": "600",  # 阈值
            }
        }
        self.handshake = False
        self.msgid += 1
        sendByte = self.protocol.generate_message(0x05, self.msgid, json.dumps(message).encode('utf-8'))
        self.ser.write(sendByte)
        self.wait_for_handshake(30)
        return True

    # 获取版本信息
    def get_version(self):
        message = {
            "type": "version"
        }
        self.code = 255
        self.msgid += 1
        sendByte = self.protocol.generate_message(0x05, self.msgid, json.dumps(message).encode('utf-8'))
        self.ser.write(sendByte)
        if self.wait_for_status():
            return self.version
        return None

    # 设置主麦ID(手动唤醒)
    def set_major_mic(self, num):
        if num < 0 or num > 5:
            print("num must in 0~5")
            return False
        message = {
            "type": "manual_wakeup",
            "content": {
                "beam": num
            }
        }
        self.code = 255
        self.msgid += 1
        sendByte = self.protocol.generate_message(0x05, self.msgid, json.dumps(message).encode('utf-8'))
        self.ser.write(sendByte)
        if self.wait_for_status():
            self.if_awake = 1
            return True
        return False

    def start_recording(self, cb=None):
        """开始录音。"""
        if not self.recording:
            self.record_callback = cb
            self.recording = True
            self.audio_data = []  # 清空之前的数据
            self.stream = sd.InputStream(callback=self._audio_callback, channels=1,
                                         samplerate=16000, dtype='int16')
            self.stream.start()

    def stop_recording(self):
        """停止录音并返回录音数据。"""
        if self.recording:
            self.recording = False
            self.stream.stop()

            # 关闭流
            self.stream.close()
        else:
            print("当前没有正在进行的录音。")

    def wait_for_status(self, timeout=3):
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.code == 0:
                return True
            time.sleep(0.1)  # 每隔100毫秒检查一次状态
        return False

    def wait_for_handshake(self, timeout=5):
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.handshake == True:
                return True
            time.sleep(0.1)  # 每隔100毫秒检查一次状态
        return False

    def serial_listen(self):
        while self.running:
            if self.ser.in_waiting > 0:
                buffer = self.ser.read(self.ser.in_waiting)
                for one in buffer:
                    self.serial_recv_deal(one)

            else:
                time.sleep(0.1)

    def serial_recv_deal(self, data):
        res = self.protocol.judge_frame_recv_ok(data)
        if res == None:
            return
        packet = self.protocol.parse_message(res)
        if packet == None:
            return

        if packet['message_type'] == 0x01:
            self.handshake = True
            sendByte = self.protocol.generate_message(0xff, packet['message_id'], bytearray([0xA5, 0x00, 0x00, 0x00]))
            self.ser.write(sendByte)
        if packet['message_type'] == 0x04:
            typestr = self.protocol.get_type_from_message(packet)
            if typestr == "version":  # 版本信息
                self.version = self.protocol.get_version_from_message(packet)

            if typestr == "aiui_event":  # 唤醒
                self.if_awake = 1
                self.angle_int = self.protocol.get_angle_from_message(packet)
                if self.awake_callback != None:
                    self.awake_callback()
                print("麦克风唤醒，角度:", self.angle_int)

            if typestr == "wakeup_keywords":  # 修改唤醒词
                pass
            if typestr == "manual_wakeup":  # 手动唤醒
                pass

            self.code = self.protocol.get_code_from_message(packet)

    def _audio_callback(self, indata, frames, time, status):
        """回调函数，在每次有新的音频数据可用时被调用。"""
        if status:
            print(status)
        if self.recording:
            if self.record_callback != None:
                self.record_callback(indata.copy())

    def audio_callback(self, pcm_data):
        self.audio_data.append(pcm_data)

    def awake_callback(self):
        pass

    def broadcast(self, text):
        # 调用语音合成接口的指令
        tts_cmd = 'cd ./speech/broadcast/bin/ && chmod +x tts_offline_sample' + ' && ./tts_offline_sample {}'.format(
            text)
        # 语音合并并获取返回值
        res_content = subprocess.getstatusoutput(tts_cmd)
        # 如果合并成功
        if res_content[0] == 0 and '合并成功' in res_content[1]:
            print('语音合成成功，开始播报!')
            # 使用aplay播放语音
            broadcast_cmd = 'aplay ./speech/broadcast/bin/tts_sample.wav -D plughw:Device'
            subprocess.Popen(broadcast_cmd, shell=True)
        else:
            print('语音合成失败!')

    def recognition(self, sec=4):
        self.audio_data = []  # 音频流存储
        print(">>>>>监听中")
        time.sleep(0.5)
        self.start_recording(self.audio_callback)
        time.sleep(sec)
        self.stop_recording()
        print(">>>>>监听结束")
        all_pcm_data = b''.join(self.audio_data)
        audio_data = np.frombuffer(all_pcm_data, dtype=np.int16)
        result = self.service.infer((audio_data, 16000))
        return result

    def record(self, filepath='output.pcm', sec=4):
        self.audio_data = []  # 音频流存储
        print(">>>>>录制中")
        time.sleep(0.5)
        self.start_recording(self.audio_callback)
        time.sleep(sec)
        self.stop_recording()
        audio_data_np = np.concatenate(self.audio_data, axis=0)
        print(f"录音长度: {len(audio_data_np)} samples")
        with open(filepath, 'wb') as pcm_file:
            pcm_file.write(audio_data_np.tobytes())
        print(">>>>>录制结束")
        print(f"播放音频命令:aplay {filepath} -r 16000 -f S16_LE -c 1 -D plughw:Device")

    def pcm_to_wav(self, pcm_file, wav_file, channels=1, sample_width=2, sample_rate=16000):
        """
        将PCM文件转换为WAV文件。

        :param pcm_file: 输入的PCM文件路径。
        :param wav_file: 输出的WAV文件路径。
        :param channels: 声道数（默认为1，即单声道）。
        :param sample_width: 采样宽度（字节），通常为2（16位）。
        :param sample_rate: 采样率（Hz），例如16000表示16kHz。
        """
        with open(pcm_file, 'rb') as pcm_file_handle:
            pcm_data = pcm_file_handle.read()

        # 使用numpy将二进制数据转换为合适的格式，这里假设是16位整型数据
        audio_data = np.frombuffer(pcm_data, dtype=np.int16)

        with wave.open(wav_file, 'w') as wf:
            wf.setnchannels(channels)  # 设置声道数
            wf.setsampwidth(sample_width)  # 设置采样宽度（字节）
            wf.setframerate(sample_rate)  # 设置采样率（Hz）
            wf.writeframes(audio_data.tobytes())  # 写入音频数据
        print(f"播放音频命令:aplay {wav_file} -D plughw:Device")


if __name__ == "__main__":
    # 实例化麦克风对象
    mic = MicrophoneController()
    result = mic.recognition()
    print(f'识别结果为：{result}')
    mic.close()





