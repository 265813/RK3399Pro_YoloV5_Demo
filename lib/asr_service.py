from rapid_paraformer import RapidParaformer
import time

import wave
import numpy as np
from typing import List, Union

def pcm_to_wav(pcm_file, wav_file, channels=1, sample_width=2, sample_rate=16000):
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



class ASRService():
    def __init__(self, config_path):
        print("Initializing ASR Service...")
        self.paraformer = RapidParaformer(config_path)
 
    def infer(self, audio_content: Union[str, np.ndarray, List[str]]):
        stime = time.time()
        result = self.paraformer(audio_content)
        if result:
            return result[0]
        # print('ASR Result: %s. time used %.2f.' % (result, time.time() - stime))
        return None

# config_path = 'resources/config.yaml'
# wav_path = 'audio/output_audio.wav'
# service = ASRService(config_path)
# print("PCM->WAV")
# pcm_to_wav('audio/mic_demo_vvui_deno_py.pcm', 'audio/output_audio.wav')
# print("语音识别-wav")
# result = service.infer(wav_path)
# print("语音识别-PCM")
# pcm_data = np.fromfile(wav_path, dtype=np.int16)  # 示例读取方法
# sr = 16000 
# result = service.infer((pcm_data, sr))
# print(result)


