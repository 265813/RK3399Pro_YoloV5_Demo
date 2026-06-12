import time
import ctypes
from ctypes import CFUNCTYPE, c_char_p, c_int, c_uint8, POINTER, Structure, c_void_p, c_uint
import atexit
import json

# 定义业务消息结构体
class business_msg_t(Structure):
    _fields_ = [
        ("handle", c_uint),           # unsigned char
        ("version", c_uint8),          # unsigned char
        ("opcode", c_uint8),           # unsigned char
        ("modId", c_uint8),            # unsigned char
        ("msgId", c_uint8),            # unsigned char
        ("data", POINTER(c_uint8)),    # unsigned char *data
        ("length", c_int)              # int
    ]

class MicrophoneController:
    def __init__(self):
        # 添加共享库
        self.lib = ctypes.CDLL('/usr/lib/libhid_lib.so')  
        # 获取lib的全局变量
        self.is_boot = ctypes.c_int.in_dll(self.lib, 'is_boot')
        # 定义lib内变量及函数映射
        self._setup_ctypes_functions()
        #必要资源路径
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
        self.if_awake = False # 麦克风是否唤醒
        self.major_mic_id = -1  # 主麦ID
        self.deno_recording = False # 录音中标志
        self.ori_recording = False # 录音中标志
        
    # 打开麦克风设备
    def open(self):
        handle = self.lib.hid_open()
        if not handle:
            print("无法打开麦克风设备, 请检查设备连接")
            return False
        status = self.lib.protocol_proc_init(self.send_to_usb_device_c, self.recv_from_usb_device_c, self.business_proc_callback, self.err_proc)
        if status == 0:
            print("初始化成功")
        else:
            print("初始化失败")
            return False 
        return True
    
    # 关闭麦克风设备
    def close(self):
        self.lib.hid_close()
    
    # 启动麦克风
    def start(self):
        self.exe_results = 255
        self.lib.get_system_status()
        if self.wait_for_status(timeout=5) == False:
            return False
        if self.exe_results == 0 :
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
    def set_major_mic(self, mic_id) :
        self.exe_results = 255
        self.lib.set_major_mic_id(mic_id)
        if self.wait_for_status() == False :
            return False
        led_id = self.lib.get_led_based_mic_id(mic_id)
        if led_id < 0:
            return False
        self.exe_results = 255
        self.lib.set_target_led_on(led_id)
        if self.wait_for_status() == False :
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
        if self.wait_for_status() == False :
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
        if self.wait_for_status() :
            return self.major_mic_id
        return -1

    def set_awake_callback(self,callback=None):
        self.awake_callback = callback


    def wait_for_status(self, timeout=1):
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.exe_results >= 0 and self.exe_results != 255 :
                return True
            elif self.exe_results < 0 :
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
        self.lib.protocol_proc_init.argtypes = [self.pfunc_send_msg, self.pfunc_recv_msg, self.pfunc_business_proc_callback, self.pfunc_err_proc]
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
            if self.denoised_audio_callback != None :
                pcm_data = bytes(businessMsg.data[:businessMsg.length])
                self.denoised_audio_callback(pcm_data)
            if self.denoised_audio_save_path != None :
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
            if self.original_audio_callback != None :
                pcm_data = bytes(businessMsg.data[:businessMsg.length])
                self.original_audio_callback(pcm_data)
            if self.original_audio_save_path != None :
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
        if businessMsg.msgId == 0x01: # 麦克风唤醒返回结果
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

        elif businessMsg.msgId == 0x08: # 设置唤醒词返回结果
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
        print(f">>>>>麦克风{(status == 0 and '正常工作' or '正在启动')},软件版本为:{software_version},协议版本为:{protocol_version.value.decode('utf-8')}")
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
            if data_dict['result'] == 0 :
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

# =============================================== 使用示例 =============================================== #
def Direction():
    print("demo示例为输入命令, 调用对应的函数, 可以简单熟悉麦克风相关的基本功能, 如:")
    print("1命令, 获取麦克风的工作状态, 若麦克风未启动, 则麦克风会自动启动至工作状态")
    print("2命令, 开启降噪音频录音功能, 执行该命令前请务必保持设备为唤醒状态")
    print("3命令, 停止降噪音频录音功能,在指定的路径中保存音频文件")
    print("4命令, 开启原始音频录音功能, 执行该命令前请务必保持设备为唤醒状态")
    print("5命令, 停止原始音频录音功能,在指定的路径保存音频文件")
    print("6命令, 设置主麦id")
    print("7命令, 获取主麦克风id")
    print("8命令, 设置自定义唤醒词")

# 读取唤醒词
def read_awake_word():
    while True:
        word = input(">>>>>请输入唤醒词,4-6个汉字:")
        if 12 <= len(word.encode('utf-8')) <= 18:
            break
        else:
            print(">>>>>唤醒词不符合要求,请重新输入")
    return word

import os

def delete_if_exists(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        else:
            return False
    except Exception as e:
        return False


def deno_audio_callback(pcm_data):
    print("\r", end='', flush=True)
    print("deno data len:", len(pcm_data), end='', flush=True)

def ori_audio_callback(pcm_data):
    print("\r", end='', flush=True)
    print("ori data len:", len(pcm_data), end='', flush=True)

def awake_callback():
    print("this is awake_callback")

if __name__ == "__main__":
    mic = MicrophoneController()
    mic.close()
    # 打开麦克风
    if mic.open() :
        print(">>>>>打开麦克风成功")
    else :
        print(">>>>>打开麦克风失败")
    Direction()
    while True:
        print("\n>>>>>请输入指令:")
        try:
            a = input().strip()
            cmd = int(a)
        except Exception as e:
            print(">>>>>指令有误, 请重新输入")
            time.sleep(1)
            continue
        if cmd == 0:
            break
        if cmd == 1:
            if mic.start() :
                print(">>>>>启动麦克风成功")
            else :
                print(">>>>>启动麦克风失败")
        elif cmd == 2:
            if mic.major_mic_id > 5 or mic.major_mic_id < 0:
                print(">>>>>您还未唤醒或设置主麦方向, 请唤醒或设置后再进行录音操作")
            else :
                delete_if_exists('./deno_audio.pcm')
                mic.start_record_denoised(deno_audio_callback,'./deno_audio.pcm')
        elif cmd == 3:
            print("播放降噪音频命令:aplay deno_audio.pcm -r 16000 -f S16_LE -c 1 -D plughw:Device")
            mic.stop_record_denoised()
        elif cmd == 4:
            if mic.major_mic_id > 5 or mic.major_mic_id < 0:
                print(">>>>>您还未唤醒或设置主麦方向, 请唤醒或设置后再进行录音操作")
            else :
                delete_if_exists('./ori_audio.pcm')
                mic.start_record_original(ori_audio_callback,'./ori_audio.pcm')
        elif cmd == 5:
            print("播放原始音频命令:aplay ori_audio.pcm -r 16000 -f S32_LE -c 8 -D plughw:Device")
            mic.stop_record_original()
        elif cmd == 6:
            mic_id = 0
            print(">>>>>请输入主麦克风id:")
            while True:
                try:
                    micstr = input().strip()
                    if int(micstr) > 5 or int(micstr) < 0:
                        print(">>>>>请重新输入主麦克风id:")
                    else:
                        break
                except Exception as e:
                    print(">>>>>请重新输入主麦克风id:")
                    time.sleep(0.1)
            mic_id = int(micstr)
            mic.set_major_mic(mic_id)
        elif cmd == 7:
            mic.get_major_mic_id()
        elif cmd == 8:
            print(">>>>>请输入唤醒词,4-6个汉字:")
            while True:
                word = input().strip()
                if len(word.encode('utf-8')) < 12 or len(word.encode('utf-8')) > 18:
                    print(">>>>>唤醒词不符合要求,请重新输入:")
                else:
                    break
            mic.set_awake_word(word)
            mic.set_awake_callback(awake_callback)
        else :
            print(">>>>>指令有误, 请重新输入:")
            time.sleep(1)
        cmd = -1
    if mic.if_awake:
        mic.stop_record_original()
        mic.stop_record_denoised()




    