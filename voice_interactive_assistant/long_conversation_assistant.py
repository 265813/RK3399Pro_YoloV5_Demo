#!/usr/bin/env python3
"""
长对话语音助手 - 专注于自动语音检测的连续对话
"""

import os
import asyncio
import pygame
import time
import re
import threading
import queue
import json
import base64
import requests
import wave
import pyaudio
import datetime
import numpy as np
from openai import OpenAI
from edge_tts import Communicate
from dotenv import load_dotenv
from config import VOICE_OPTIONS, DEFAULT_VOICE, TTS_CONFIG, BAIDU_SPEECH_CONFIG, RECORDING_CONFIG

class LongConversationAssistant:
    def __init__(self):
        # 加载环境变量
        load_dotenv()

        # 工作目录
        self.work_dir = os.path.dirname(os.path.abspath(__file__))
        self.audio_temp = os.path.join(self.work_dir, "audio_temp")

        # 确保音频临时目录存在
        os.makedirs(self.audio_temp, exist_ok=True)

        # 创建提示音文件
        self.create_notification_sounds()

        # DeepSeek API 配置
        self.api_key = os.environ.get("DEEPSEEK_API_KEY")
        self.base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

        # 对话参数
        self.max_tokens = int(os.environ.get("MAX_TOKENS", "1000"))
        self.temperature = float(os.environ.get("TEMPERATURE", "0.7"))
        self.stream = os.environ.get("STREAM", "true").lower() == "true"

        # 语音配置
        self.current_voice = os.environ.get("TTS_VOICE", DEFAULT_VOICE)
        # 确保使用正确的Edge-TTS语音名称
        if self.current_voice in VOICE_OPTIONS:
            self.voice_name = VOICE_OPTIONS[self.current_voice]
        else:
            self.current_voice = DEFAULT_VOICE
            self.voice_name = VOICE_OPTIONS[DEFAULT_VOICE]
        self.enable_streaming_tts = os.environ.get("STREAMING_TTS", "true").lower() == "true"

        # 流式语音合成
        self.sentence_buffer = ""
        self.audio_queue = queue.Queue()
        self.is_playing = False
        self.audio_thread = None

        # 百度云API配置
        self.baidu_app_id = os.environ.get("BAIDU_APP_ID")
        self.baidu_api_key = os.environ.get("BAIDU_API_KEY")
        self.baidu_secret_key = os.environ.get("BAIDU_SECRET_KEY")
        self.baidu_access_token = None
        self.use_baidu_tts = os.environ.get("USE_BAIDU_TTS", "false").lower() == "true"

        # 对话记录
        self.conversation_history = []
        self.conversation_file = os.path.join(self.work_dir, "conversation_history.json")
        self.load_conversation_history()

        # 优化的自动语音检测配置
        self.silence_threshold = float(os.environ.get("SILENCE_THRESHOLD", "0.005"))  # 更敏感的静音阈值
        self.silence_duration = float(os.environ.get("SILENCE_DURATION", "1.5"))     # 缩短等待时间
        self.min_recording_duration = float(os.environ.get("MIN_RECORDING_DURATION", "0.5"))  # 缩短最小时长
        self.voice_start_threshold = float(os.environ.get("VOICE_START_THRESHOLD", "0.015"))  # 降低语音开始阈值
        self.pre_recording_buffer = int(os.environ.get("PRE_RECORDING_BUFFER", "8"))  # 增加预录制缓冲
        self.voice_timeout = float(os.environ.get("VOICE_TIMEOUT", "15.0"))  # 等待语音超时时间

        # 录音状态
        self.is_recording = False
        self.audio_data = []
        self.audio_buffer = []  # 预录制缓冲区

        # 音频播放
        pygame.mixer.init()
        self.audio_queue = queue.Queue()
        self.is_playing = False

        # 初始化百度云API
        if self.baidu_api_key and self.baidu_secret_key:
            self.get_baidu_access_token()

    def get_baidu_access_token(self):
        """获取百度云API访问令牌"""
        try:
            url = "https://aip.baidubce.com/oauth/2.0/token"
            params = {
                "grant_type": "client_credentials",
                "client_id": self.baidu_api_key,
                "client_secret": self.baidu_secret_key
            }
            response = requests.post(url, params=params)
            result = response.json()

            if "access_token" in result:
                self.baidu_access_token = result["access_token"]
                print("✅ 百度云API访问令牌获取成功")
                return True
            else:
                print(f"获取百度云API访问令牌: {result}")
                return False
        except Exception as e:
            print(f"获取百度云API访问: {e}")
            return False

    def load_conversation_history(self):
        """加载对话历史记录"""
        try:
            if os.path.exists(self.conversation_file):
                with open(self.conversation_file, 'r', encoding='utf-8') as f:
                    self.conversation_history = json.load(f)
                print(f"✅ 加载了 {len(self.conversation_history)} 条对话记录")
            else:
                self.conversation_history = []
        except Exception as e:
            print(f"❌ 加载对话历史失败: {e}")
            self.conversation_history = []

    def save_conversation_history(self):
        """保存对话历史记录"""
        try:
            # 只保留最近的50条对话记录
            if len(self.conversation_history) > 50:
                self.conversation_history = self.conversation_history[-50:]

            with open(self.conversation_file, 'w', encoding='utf-8') as f:
                json.dump(self.conversation_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存对话历史: {e}")

    def add_conversation_record(self, user_input, ai_response):
        """添加对话记录"""
        record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "user_input": user_input,
            "ai_response": ai_response,
            "input_type": "voice"
        }
        self.conversation_history.append(record)
        self.save_conversation_history()

    def get_recent_context(self, max_messages=6):
        """获取最近的对话上下文"""
        if not self.conversation_history:
            return []

        recent_history = self.conversation_history[-max_messages:]
        context = []

        for record in recent_history:
            context.append({"role": "user", "content": record["user_input"]})
            context.append({"role": "assistant", "content": record["ai_response"]})

        return context

    def optimized_voice_detection(self):
        """优化的语音检测录音"""
        try:
            print("🎤 智能语音检测已启动...")
            print("💡 开始说话，系统会自动检测语音开始和结束")

            # 初始化PyAudio
            audio = pyaudio.PyAudio()

            # 录音参数
            sample_rate = RECORDING_CONFIG["sample_rate"]
            channels = RECORDING_CONFIG["channels"]
            chunk_size = RECORDING_CONFIG["chunk_size"]
            audio_format = pyaudio.paInt16

            # 开始录音流
            stream = audio.open(
                format=audio_format,
                channels=channels,
                rate=sample_rate,
                input=True,
                frames_per_buffer=chunk_size
            )

            # 状态变量
            self.audio_data = []
            self.audio_buffer = []
            silence_counter = 0
            voice_detected = False
            recording_started = False

            # 计算阈值相关参数
            silence_chunks_needed = int(self.silence_duration * sample_rate / chunk_size)
            min_recording_chunks = int(self.min_recording_duration * sample_rate / chunk_size)
            total_chunks = 0
            voice_chunks = 0

            print(f"🔧 检测参数:")
            print(f"   语音开始阈值: {self.voice_start_threshold}")
            print(f"   静音阈值: {self.silence_threshold}")
            print(f"   静音时长: {self.silence_duration}秒")
            print(f"   最小录音时长: {self.min_recording_duration}秒")
            print("🔊 等待语音输入...")

            while True:
                try:
                    data = stream.read(chunk_size, exception_on_overflow=False)

                    # 计算音频能量（RMS）
                    audio_array = np.frombuffer(data, dtype=np.int16)
                    if len(audio_array) > 0:
                        # 计算RMS能量，避免除零错误
                        rms = np.sqrt(np.mean(audio_array.astype(np.float64)**2))
                        energy = rms / 32768.0  # 归一化到0-1
                        # 防止NaN值
                        energy = max(0.0, min(1.0, energy)) if not np.isnan(energy) else 0.0
                    else:
                        energy = 0.0

                    # 维护预录制缓冲区
                    self.audio_buffer.append(data)
                    if len(self.audio_buffer) > self.pre_recording_buffer:
                        self.audio_buffer.pop(0)

                    # 检测语音开始
                    if not voice_detected and energy > self.voice_start_threshold:
                        voice_detected = True
                        recording_started = True
                        # 将缓冲区的数据加入录音
                        self.audio_data.extend(self.audio_buffer)
                        print("🎙️ 检测到语音，开始录音...")

                    # 如果已经检测到语音，继续录音
                    if recording_started:
                        self.audio_data.append(data)
                        total_chunks += 1

                        # 检测静音
                        if energy < self.silence_threshold:
                            silence_counter += 1
                            if total_chunks % 5 == 0:  # 每5个chunk显示一次
                                print(f"🔇 静音检测中... ({silence_counter}/{silence_chunks_needed})")
                        else:
                            silence_counter = 0
                            voice_chunks += 1
                            if total_chunks % 10 == 0:
                                print(f"🔊 录音中... (能量: {energy:.3f})")

                        # 检查停止条件
                        if (silence_counter >= silence_chunks_needed and
                            total_chunks >= min_recording_chunks):
                            print("✅ 检测到语音结束，停止录音")
                            break

                        # 防止录音时间过长
                        if total_chunks > sample_rate * 30 / chunk_size:  # 最大30秒
                            print("⏰ 录音时间过长，自动停止")
                            break

                    # 如果长时间没有检测到语音，超时退出
                    if not voice_detected:
                        total_chunks += 1
                        if total_chunks > sample_rate * self.voice_timeout / chunk_size:
                            print(f"⏰ 等待语音超时 ({self.voice_timeout}秒)")
                            stream.stop_stream()
                            stream.close()
                            audio.terminate()
                            return None

                except Exception as e:
                    print(f"录音错误: {e}")
                    break

            # 停止录音
            stream.stop_stream()
            stream.close()
            audio.terminate()

            if self.audio_data and len(self.audio_data) >= min_recording_chunks:
                # 保存录音文件
                audio_file_path = os.path.join(self.audio_temp, "voice_input.wav")
                with wave.open(audio_file_path, 'wb') as wf:
                    wf.setnchannels(channels)
                    wf.setsampwidth(audio.get_sample_size(audio_format))
                    wf.setframerate(sample_rate)
                    wf.writeframes(b''.join(self.audio_data))

                duration = len(self.audio_data) * chunk_size / sample_rate
                voice_ratio = voice_chunks / total_chunks if total_chunks > 0 else 0
                print(f"✅ 录音完成 - 时长: {duration:.1f}秒, 语音比例: {voice_ratio:.1%}")
                return audio_file_path
            else:
                print("录音时间")
                return None

        except Exception as e:
            print(f"语音检测录音: {e}")
            return None

    def baidu_speech_recognition(self, audio_file_path):
        """使用百度云API进行语音识别"""
        try:
            if not self.baidu_access_token:
                print("百度云API访问令牌")
                return None

            # 读取音频文件
            with open(audio_file_path, 'rb') as f:
                audio_data = f.read()

            # 编码音频数据
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            # 构建请求参数
            asr_config = BAIDU_SPEECH_CONFIG["asr"]
            data = {
                "format": asr_config["format"],
                "rate": asr_config["rate"],
                "channel": asr_config["channel"],
                "cuid": "long_conversation_assistant",
                "token": self.baidu_access_token,
                "dev_pid": asr_config["dev_pid"],
                "speech": audio_base64,
                "len": len(audio_data)
            }

            # 发送请求
            headers = {'Content-Type': 'application/json'}
            response = requests.post(asr_config["url"],
                                   data=json.dumps(data),
                                   headers=headers)

            result = response.json()

            if result.get("err_no") == 0 and "result" in result:
                recognized_text = result["result"][0]
                print(f"🎯 语音识别: {recognized_text}")
                return recognized_text
            else:
                print(f"语音识别: {result}")
                return None

        except Exception as e:
            print(f"语音识别: {e}")
            return None

    def create_notification_sounds(self):
        """创建提示音文件"""
        try:
            import numpy as np
            import wave

            # 录音开始提示音（高音调）
            self.recording_start_sound = os.path.join(self.audio_temp, "recording_start.wav")
            self.create_beep_sound(self.recording_start_sound, frequency=800, duration=0.3)

            # 录音结束提示音（低音调）
            self.recording_end_sound = os.path.join(self.audio_temp, "recording_end.wav")
            self.create_beep_sound(self.recording_end_sound, frequency=400, duration=0.3)

        except Exception as e:
            print(f"创建提示音: {e}")
            self.recording_start_sound = None
            self.recording_end_sound = None

    def create_beep_sound(self, filename, frequency=800, duration=0.3, sample_rate=44100):
        """创建提示音文件"""
        try:
            import numpy as np
            import wave

            # 生成正弦波
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            wave_data = np.sin(2 * np.pi * frequency * t)

            # 添加淡入淡出效果
            fade_samples = int(0.05 * sample_rate)  # 50ms淡入淡出
            wave_data[:fade_samples] *= np.linspace(0, 1, fade_samples)
            wave_data[-fade_samples:] *= np.linspace(1, 0, fade_samples)

            # 转换为16位整数
            wave_data = (wave_data * 32767).astype(np.int16)

            # 保存为WAV文件
            with wave.open(filename, 'w') as wav_file:
                wav_file.setnchannels(1)  # 单声道
                wav_file.setsampwidth(2)  # 16位
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(wave_data.tobytes())

        except Exception as e:
            print(f"创建提示音文件: {e}")

    def play_notification_sound(self, sound_type="start"):
        """播放提示音"""
        try:
            if sound_type == "start" and hasattr(self, 'recording_start_sound') and self.recording_start_sound and os.path.exists(self.recording_start_sound):
                print("🔔 播放录音开始提示音")
                pygame.mixer.init()
                pygame.mixer.music.load(self.recording_start_sound)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                pygame.mixer.quit()
            elif sound_type == "end" and hasattr(self, 'recording_end_sound') and self.recording_end_sound and os.path.exists(self.recording_end_sound):
                print("🔔 播放录音结束提示音")
                pygame.mixer.init()
                pygame.mixer.music.load(self.recording_end_sound)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                pygame.mixer.quit()
        except Exception as e:
            print(f"播放提示音: {e}")

    def call_deepseek_api(self, prompt, retries=3, delay=5):
        """调用 DeepSeek API 获取回复"""
        # 过滤掉非法字符（例如表情符号等）
        prompt = prompt.encode('utf-8', 'ignore').decode('utf-8')

        for attempt in range(retries):
            try:
                print(f"🔄 正在调用 API (尝试 {attempt + 1}/{retries})...")

                # 构建消息列表，包含上下文
                messages = []
                context = self.get_recent_context(max_messages=6)  # 最近3轮对话
                messages.extend(context)

                if context:
                    print(f"📚 使用了 {len(context)//2} 轮历史对话作为上下文")

                # 添加当前用户输入
                messages.append({
                    "role": "user",
                    "content": prompt,
                })

                chat_completion_res = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=self.stream,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    extra_body={}
                )

                if self.stream:
                    # 流式响应处理
                    if self.enable_streaming_tts:
                        print("💬 AI 回复（流式+语音）：", end="", flush=True)
                        full_response = asyncio.run(self.streaming_tts_handler(chat_completion_res))
                        print()  # 换行
                        return full_response
                    else:
                        print("💬 AI 回复（流式）：", end="", flush=True)
                        full_response = ""
                        for chunk in chat_completion_res:
                            if chunk.choices[0].delta.content:
                                content = chunk.choices[0].delta.content
                                print(content, end="", flush=True)
                                full_response += content
                        print()  # 换行
                        return full_response
                else:
                    # 非流式响应处理
                    response_content = chat_completion_res.choices[0].message.content
                    print(f"💬 AI 回复：{response_content}")
                    return response_content

            except Exception as e:
                print(f"请求 DeepSeek API ：{e}")
                if attempt < retries - 1:
                    print(f"重试中... (尝试 {attempt + 1}/{retries})")
                    time.sleep(delay)
                else:
                    return "请求 DeepSeek API 超过最大重试次数"





    def clean_markdown(self, text):
        """清理 Markdown 格式"""
        # 移除 Markdown 语法
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # 粗体
        text = re.sub(r'\*(.*?)\*', r'\1', text)      # 斜体
        text = re.sub(r'`(.*?)`', r'\1', text)        # 代码
        text = re.sub(r'#{1,6}\s*', '', text)         # 标题
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # 链接
        text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)  # 图片

        return text.strip()

    def remove_emojis_and_symbols(self, text):
        """更彻底地移除表情符号和特殊符号"""
        import unicodedata

        # 移除所有 Unicode 表情符号和符号
        cleaned_text = ""
        for char in text:
            # 获取字符的 Unicode 类别
            category = unicodedata.category(char)
            # 保留字母、数字、标点符号、空格，过滤掉符号和其他特殊字符
            if category.startswith(('L', 'N', 'P', 'Z')):  # Letter, Number, Punctuation, Separator
                # 但是排除一些特殊的标点符号
                if char not in '🔥💯⭐️✨🎉🎊🎈🎁🎀🎂🍰🎄🎃👻🎅🤶🧙‍♀️🧙‍♂️🧚‍♀️🧚‍♂️':
                    cleaned_text += char

        return cleaned_text

    def split_into_sentences(self, text):
        """将文本分割成句子"""
        # 中文句子分割符
        sentence_endings = ['。', '！', '？', '；', '\n']
        sentences = []
        current_sentence = ""

        for char in text:
            current_sentence += char
            if char in sentence_endings:
                sentence = current_sentence.strip()
                if sentence:
                    sentences.append(sentence)
                current_sentence = ""

        # 处理最后一个句子
        if current_sentence.strip():
            sentences.append(current_sentence.strip())

        return sentences

    async def generate_audio_for_sentence(self, sentence, audio_index):
        """为单个句子生成音频"""
        try:
            # 清理句子
            cleaned_sentence = self.clean_markdown(sentence)
            cleaned_sentence = self.remove_emojis_and_symbols(cleaned_sentence)

            if len(cleaned_sentence.strip()) < 2:
                return None

            output_path = os.path.join(self.audio_temp, f"sentence_{audio_index}.mp3")
            communicate = Communicate(cleaned_sentence, self.voice_name)
            await communicate.save(output_path)
            return output_path
        except Exception as e:
            print(f"句子语音合成: {e}")
            return None

    def audio_player_worker(self):
        """音频播放工作线程"""
        while self.is_playing:
            try:
                # 从队列中获取音频文件路径，超时1秒
                audio_path = self.audio_queue.get(timeout=1)
                if audio_path is None:  # 结束信号
                    break

                # 播放音频
                try:
                    pygame.mixer.init()
                    pygame.mixer.music.load(audio_path)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        pygame.time.Clock().tick(10)
                        if not self.is_playing:  # 检查是否需要停止
                            pygame.mixer.music.stop()
                            break
                except pygame.error as e:
                    print(f"音频播放: {e}")
                finally:
                    pygame.mixer.quit()
                    # 删除临时文件
                    try:
                        os.remove(audio_path)
                    except:
                        pass

                self.audio_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"音频播放线程: {e}")

    async def streaming_tts_handler(self, text_stream):
        """处理流式文本转语音"""
        if not self.enable_streaming_tts:
            return text_stream

        self.sentence_buffer = ""
        self.is_playing = True

        # 启动音频播放线程
        self.audio_thread = threading.Thread(target=self.audio_player_worker)
        self.audio_thread.start()

        audio_index = 0
        full_text = ""

        try:
            for chunk in text_stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    print(content, end="", flush=True)
                    full_text += content
                    self.sentence_buffer += content

                    # 检查是否有完整的句子
                    sentences = self.split_into_sentences(self.sentence_buffer)
                    if len(sentences) > 1:
                        # 处理除最后一个外的所有句子
                        for sentence in sentences[:-1]:
                            if sentence.strip():
                                audio_path = await self.generate_audio_for_sentence(sentence, audio_index)
                                if audio_path:
                                    self.audio_queue.put(audio_path)
                                    audio_index += 1

                        # 保留最后一个未完成的句子
                        self.sentence_buffer = sentences[-1]

            # 处理最后的缓冲区内容
            if self.sentence_buffer.strip():
                audio_path = await self.generate_audio_for_sentence(self.sentence_buffer, audio_index)
                if audio_path:
                    self.audio_queue.put(audio_path)

            # 发送结束信号
            self.audio_queue.put(None)

            # 等待音频播放完成
            if self.audio_thread:
                self.audio_thread.join()

        except Exception as e:
            print(f"流式语音处理: {e}")
        finally:
            self.is_playing = False

        return full_text

    async def text_to_speech(self, text, output_path):
        """使用Edge-TTS进行语音合成"""
        try:
            communicate = Communicate(text, self.current_voice)
            await communicate.save(output_path)
            return True
        except Exception as e:
            print(f"Edge-TTS语音合成: {e}")
            return False

    def play_audio(self, file_path):
        """播放音频文件"""
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()

            # 等待播放完成
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)

            return True
        except Exception as e:
            print(f"音频播放: {e}")
            return False

    def start_long_conversation(self):
        """开始长对话模式"""
        print("🎙️ 长对话模式启动")
        print("=" * 50)
        print("💡 智能语音检测 - 自动开始和停止录音")
        print("🧠 上下文记忆 - 保持对话连贯性")
        print("📚 对话记录 - 自动保存对话历史")
        print()

        # 显示配置信息
        print("🔧 当前配置:")
        print(f"   语音开始阈值: {self.voice_start_threshold}")
        print(f"   静音检测阈值: {self.silence_threshold}")
        print(f"   静音持续时间: {self.silence_duration}秒")
        print(f"   最小录音时长: {self.min_recording_duration}秒")
        print(f"   历史对话记录: {len(self.conversation_history)}条")
        print()

        if not self.baidu_access_token:
            print("百度云API")
            return

        conversation_count = 0

        print("🚀 长对话模式已就绪")
        print("💬 按 Enter 开始第一轮对话，输入 'quit' 退出")

        # 等待用户开始第一轮对话
        user_input = input("\n按 Enter 开始第一轮语音输入，或输入 'quit' 退出: ").strip()
        if user_input.lower() in ['quit', 'exit', 'q', '退出']:
            print("� 退出长对话模式")
            return

        # 播放第一轮录音开始提示音
        self.play_notification_sound("start")

        while True:
            try:
                conversation_count += 1
                print(f"\n� 第 {conversation_count} 轮对话")
                print("-" * 40)

                # 1. 智能语音检测录音（自动开始）
                print("\n🎤 第1步: 智能语音检测")
                audio_file = self.optimized_voice_detection()

                if not audio_file:
                    print("录音失败")
                    conversation_count -= 1  # 不计入失败的对话
                    continue

                # 2. 语音识别
                print("\n🔍 第2步: 语音识别")
                recognized_text = self.baidu_speech_recognition(audio_file)

                if not recognized_text:
                    print("语音识别失败")
                    conversation_count -= 1
                    continue

                # 检查是否要退出
                if recognized_text.lower() in ['退出', '结束', '再见', 'quit', 'exit', 'bye']:
                    print("👋 检测到退出指令，结束长对话模式")
                    break

                # 3. 播放录音结束提示音
                self.play_notification_sound("end")

                # 4. AI对话生成（包含流式语音合成）
                print("\n🤖 第3步: AI对话生成")
                ai_response = self.call_deepseek_api(recognized_text)

                if not ai_response:
                    print("AI回复生成失败")
                    conversation_count -= 1
                    continue

                # 5. 保存对话记录
                self.add_conversation_record(recognized_text, ai_response)

                # 如果没有启用流式语音合成，则进行传统语音合成
                if not (self.stream and self.enable_streaming_tts):
                    print("\n🔊 第4步: 语音合成和播放")
                    cleaned_text = self.clean_markdown(ai_response)
                    cleaned_text = self.remove_emojis_and_symbols(cleaned_text)

                    if len(cleaned_text.strip()) >= 2:
                        output_path = os.path.join(self.audio_temp, f"reply_{conversation_count}.mp3")

                        print("🎵 正在生成语音...")
                        if asyncio.run(self.text_to_speech(cleaned_text, output_path)):
                            print("🔊 正在播放AI回复...")
                            if self.play_audio(output_path):
                                print("✅ 语音播放完成")
                            else:
                                print("语音播放")
                        else:
                            print("语音合成")
                    else:
                        print("⚠️ 文本过短，跳过语音合成")
                else:
                    print("✅ 流式语音合成已完成")

                # 6. 播放录音开始提示音，准备下一轮录音
                if conversation_count < 999:  # 避免无限循环
                    print("\n🔔 准备下一轮对话...")
                    time.sleep(0.5)  # 短暂停顿
                    self.play_notification_sound("start")

                # 清理临时文件
                try:
                    if os.path.exists(audio_file):
                        os.remove(audio_file)
                except:
                    pass

                print(f"✅ 第 {conversation_count} 轮对话完成")

                # 显示简要统计
                if conversation_count % 5 == 0:
                    print(f"\n📊 对话统计: 已完成 {conversation_count} 轮对话，共 {len(self.conversation_history)} 条记录")

            except KeyboardInterrupt:
                print("\n🛑 对话被中断")
                break
            except Exception as e:
                print(f"对话过程中发生: {e}")
                conversation_count -= 1

        # 显示最终统计
        print(f"\n📊 对话结束统计:")
        print(f"   本次对话轮数: {conversation_count}")
        print(f"   总对话记录: {len(self.conversation_history)} 条")
        print("💾 对话记录已自动保存")

    def run(self):
        """运行长对话助手"""
        print("🎙️ 长对话语音助手")
        print("=" * 50)
        print("🚀 专注于智能语音检测的连续对话体验")
        print()

        # 检查配置
        print("📋 系统检查:")
        print(f"   DeepSeek API: {'✅' if self.api_key else ' '} {'已配置' if self.api_key else '未配置'}")
        print(f"   百度云API: {'✅' if self.baidu_access_token else ' '} {'已配置' if self.baidu_access_token else '未配置'}")
        print(f"   语音合成: ✅ Edge-TTS")
        print(f"   音频播放: ✅ Pygame")
        print()

        if not self.api_key:
            print(" DeepSeek API配置，请检查.env文件")
            return

        if not self.baidu_access_token:
            print(" 百度云APIs配置，请检查.env文件")
            return

        print("✅ 系统检查通过，准备开始长对话")

        try:
            self.start_long_conversation()
        except Exception as e:
            print(f" 程序运行异常: {e}")
        finally:
            print("\n👋 感谢使用长对话语音助手！")

if __name__ == "__main__":
    assistant = LongConversationAssistant()
    assistant.run()