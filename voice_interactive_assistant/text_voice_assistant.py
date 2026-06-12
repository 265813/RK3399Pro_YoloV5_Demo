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

class TextVoiceAssistant:
    def __init__(self):
        # 加载 .env 文件
        load_dotenv()

        self.work_dir = os.path.dirname(os.path.abspath(__file__))
        self.audio_temp = os.path.join(self.work_dir, "tmp_audio")
        os.makedirs(self.audio_temp, exist_ok=True)

        # API 配置
        self.api_key = os.environ.get("DEEPSEEK_API_KEY")
        self.base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.ppinfra.com/v3/openai")
        self.model = os.environ.get("DEEPSEEK_MODEL", "deepseek/deepseek-v3/community")
        self.stream = os.environ.get("STREAM_RESPONSE", "true").lower() == "true"
        self.max_tokens = int(os.environ.get("MAX_TOKENS", "1000"))
        self.temperature = float(os.environ.get("TEMPERATURE", "0.7"))

        if not self.api_key:
            raise RuntimeError("❌ 请先在 .env 文件中设置 DEEPSEEK_API_KEY 或设置环境变量")

        # 初始化 OpenAI 客户端
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )

        # 语音配置
        self.current_voice = os.environ.get("TTS_VOICE", DEFAULT_VOICE)
        self.voice_name = VOICE_OPTIONS.get(self.current_voice, VOICE_OPTIONS[DEFAULT_VOICE])

        # 流式语音配置
        self.enable_streaming_tts = os.environ.get("STREAMING_TTS", "true").lower() == "true"
        self.sentence_buffer = ""
        self.audio_queue = queue.Queue()
        self.is_playing = False
        self.audio_thread = None

        # 百度云API配置
        self.baidu_app_id = os.environ.get("BAIDU_APP_ID")
        self.baidu_api_key = os.environ.get("BAIDU_API_KEY")
        self.baidu_secret_key = os.environ.get("BAIDU_SECRET_KEY")
        self.baidu_access_token = None

        # 语音对话配置
        self.enable_voice_chat = os.environ.get("ENABLE_VOICE_CHAT", "false").lower() == "true"
        self.use_baidu_tts = os.environ.get("USE_BAIDU_TTS", "false").lower() == "true"

        # 录音相关
        self.is_recording = False
        self.audio_data = []

        # 对话记录
        self.conversation_history = []
        self.conversation_file = os.path.join(self.work_dir, "conversation_history.json")
        self.load_conversation_history()

        # 自动语音检测配置
        self.auto_voice_detection = os.environ.get("AUTO_VOICE_DETECTION", "true").lower() == "true"
        self.silence_threshold = float(os.environ.get("SILENCE_THRESHOLD", "0.01"))  # 静音阈值
        self.silence_duration = float(os.environ.get("SILENCE_DURATION", "2.0"))  # 静音持续时间（秒）
        self.min_recording_duration = float(os.environ.get("MIN_RECORDING_DURATION", "1.0"))  # 最小录音时长

        # 长对话模式
        self.long_conversation_mode = False

        # 初始化百度云API
        if self.enable_voice_chat and (self.baidu_api_key and self.baidu_secret_key):
            self.get_baidu_access_token()

    def clean_markdown(self, text):
        """移除 Markdown 符号和表情包，适合语音合成"""
        # 移除表情符号 (Unicode 表情符号范围)
        text = re.sub(r'[\U0001F600-\U0001F64F]', '', text)  # 表情符号
        text = re.sub(r'[\U0001F300-\U0001F5FF]', '', text)  # 符号和象形文字
        text = re.sub(r'[\U0001F680-\U0001F6FF]', '', text)  # 交通和地图符号
        text = re.sub(r'[\U0001F1E0-\U0001F1FF]', '', text)  # 国旗
        text = re.sub(r'[\U00002600-\U000027BF]', '', text)  # 杂项符号
        text = re.sub(r'[\U0001F900-\U0001F9FF]', '', text)  # 补充符号
        text = re.sub(r'[\U0001FA70-\U0001FAFF]', '', text)  # 扩展符号

        # 移除常见的文本表情符号
        text = re.sub(r'[:;=]-?[)(\[\]{}|\\\/DPp@$*]', '', text)  # :) :( :D 等
        text = re.sub(r'[oO][_\-]?[oO]', '', text)  # o_o O_O 等
        text = re.sub(r'[xX][_\-]?[xX]', '', text)  # x_x X_X 等
        text = re.sub(r'[><!]+', '', text)  # >>> !!! 等

        # 移除 Markdown 符号
        text = re.sub(r"[#>*_`~\-]+", " ", text)  # 移除常见 Markdown 符号
        text = re.sub(r"\[.*?\]", "", text)        # 移除方括号内容 [链接文本]
        text = re.sub(r"\(.*?\)", "", text)        # 移除圆括号内容 (链接地址)

        # 移除多余的空白字符
        text = re.sub(r"\n\s*\n", "\n", text)     # 合并多余空行
        text = re.sub(r"\s{2,}", " ", text)       # 多空格变一个空格
        text = re.sub(r"^\s+|\s+$", "", text)     # 移除首尾空格

        return text.strip()

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
            # 只保留最近的100条对话记录
            if len(self.conversation_history) > 100:
                self.conversation_history = self.conversation_history[-100:]

            with open(self.conversation_file, 'w', encoding='utf-8') as f:
                json.dump(self.conversation_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存对话历史失败: {e}")

    def add_conversation_record(self, user_input, ai_response, input_type="text"):
        """添加对话记录"""
        record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "user_input": user_input,
            "ai_response": ai_response,
            "input_type": input_type  # "text" 或 "voice"
        }
        self.conversation_history.append(record)
        self.save_conversation_history()

    def get_recent_context(self, max_messages=10):
        """获取最近的对话上下文"""
        if not self.conversation_history:
            return []

        recent_history = self.conversation_history[-max_messages:]
        context = []

        for record in recent_history:
            context.append({"role": "user", "content": record["user_input"]})
            context.append({"role": "assistant", "content": record["ai_response"]})

        return context

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
                print(f"❌ 获取百度云API访问令牌失败: {result}")
                return False
        except Exception as e:
            print(f"❌ 获取百度云API访问令牌异常: {e}")
            return False

    def record_audio(self, auto_detect=False):
        """录制音频"""
        try:
            if auto_detect:
                return self.record_audio_auto_detect()
            else:
                return self.record_audio_manual()
        except Exception as e:
            print(f"❌ 录音异常: {e}")
            return None

    def record_audio_manual(self):
        """手动录音（按Enter停止）"""
        try:
            print("🎤 开始录音，按 Enter 键停止录音...")

            # 初始化PyAudio
            audio = pyaudio.PyAudio()

            # 录音参数
            sample_rate = RECORDING_CONFIG["sample_rate"]
            channels = RECORDING_CONFIG["channels"]
            chunk_size = RECORDING_CONFIG["chunk_size"]
            audio_format = pyaudio.paInt16

            # 开始录音
            stream = audio.open(
                format=audio_format,
                channels=channels,
                rate=sample_rate,
                input=True,
                frames_per_buffer=chunk_size
            )

            self.is_recording = True
            self.audio_data = []

            # 启动录音线程
            def record_thread():
                while self.is_recording:
                    try:
                        data = stream.read(chunk_size, exception_on_overflow=False)
                        self.audio_data.append(data)
                    except Exception as e:
                        print(f"录音错误: {e}")
                        break

            record_thread_obj = threading.Thread(target=record_thread)
            record_thread_obj.start()

            # 等待用户按Enter停止录音
            input()
            self.is_recording = False
            record_thread_obj.join()

            # 停止录音
            stream.stop_stream()
            stream.close()
            audio.terminate()

            if self.audio_data:
                # 保存录音文件
                audio_file_path = os.path.join(self.audio_temp, "recorded_audio.wav")
                with wave.open(audio_file_path, 'wb') as wf:
                    wf.setnchannels(channels)
                    wf.setsampwidth(audio.get_sample_size(audio_format))
                    wf.setframerate(sample_rate)
                    wf.writeframes(b''.join(self.audio_data))

                print("✅ 录音完成")
                return audio_file_path
            else:
                print("❌ 录音失败，没有录制到音频数据")
                return None

        except Exception as e:
            print(f"❌ 手动录音异常: {e}")
            return None

    def record_audio_auto_detect(self):
        """自动检测语音录音（检测到静音自动停止）"""
        try:
            print("🎤 开始自动录音，检测到静音将自动停止...")

            # 初始化PyAudio
            audio = pyaudio.PyAudio()

            # 录音参数
            sample_rate = RECORDING_CONFIG["sample_rate"]
            channels = RECORDING_CONFIG["channels"]
            chunk_size = RECORDING_CONFIG["chunk_size"]
            audio_format = pyaudio.paInt16

            # 开始录音
            stream = audio.open(
                format=audio_format,
                channels=channels,
                rate=sample_rate,
                input=True,
                frames_per_buffer=chunk_size
            )

            self.audio_data = []
            silence_counter = 0
            silence_chunks_needed = int(self.silence_duration * sample_rate / chunk_size)
            min_recording_chunks = int(self.min_recording_duration * sample_rate / chunk_size)
            total_chunks = 0

            print(f"🔊 静音阈值: {self.silence_threshold}, 静音时长: {self.silence_duration}秒")

            while True:
                try:
                    data = stream.read(chunk_size, exception_on_overflow=False)
                    self.audio_data.append(data)
                    total_chunks += 1

                    # 计算音频能量（音量）
                    audio_array = np.frombuffer(data, dtype=np.int16)
                    energy = np.sqrt(np.mean(audio_array**2)) / 32768.0  # 归一化到0-1

                    if energy < self.silence_threshold:
                        silence_counter += 1
                        if total_chunks % 10 == 0:  # 每10个chunk显示一次状态
                            print(f"🔇 检测到静音... ({silence_counter}/{silence_chunks_needed})")
                    else:
                        silence_counter = 0
                        if total_chunks % 10 == 0:
                            print(f"🔊 检测到语音... (能量: {energy:.3f})")

                    # 检查是否满足停止条件
                    if (silence_counter >= silence_chunks_needed and
                        total_chunks >= min_recording_chunks):
                        print("✅ 检测到足够长的静音，自动停止录音")
                        break

                    # 防止录音时间过长
                    if total_chunks > sample_rate * 60 / chunk_size:  # 最大60秒
                        print("⏰ 录音时间过长，自动停止")
                        break

                except Exception as e:
                    print(f"录音错误: {e}")
                    break

            # 停止录音
            stream.stop_stream()
            stream.close()
            audio.terminate()

            if self.audio_data:
                # 保存录音文件
                audio_file_path = os.path.join(self.audio_temp, "recorded_audio.wav")
                with wave.open(audio_file_path, 'wb') as wf:
                    wf.setnchannels(channels)
                    wf.setsampwidth(audio.get_sample_size(audio_format))
                    wf.setframerate(sample_rate)
                    wf.writeframes(b''.join(self.audio_data))

                duration = len(self.audio_data) * chunk_size / sample_rate
                print(f"✅ 自动录音完成，时长: {duration:.1f}秒")
                return audio_file_path
            else:
                print("❌ 录音失败，没有录制到音频数据")
                return None

        except Exception as e:
            print(f"❌ 自动录音异常: {e}")
            return None

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

    def baidu_speech_recognition(self, audio_file_path):
        """使用百度云API进行语音识别"""
        try:
            if not self.baidu_access_token:
                print("❌ 百度云API访问令牌未获取")
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
                "cuid": "voice_assistant",
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
                print(f"🎯 语音识别结果: {recognized_text}")
                return recognized_text
            else:
                print(f"❌ 语音识别失败: {result}")
                return None

        except Exception as e:
            print(f"❌ 语音识别异常: {e}")
            return None

    def baidu_text_to_speech(self, text, output_path):
        """使用百度云API进行语音合成"""
        try:
            if not self.baidu_access_token:
                print("❌ 百度云API访问令牌未获取")
                return False

            # 构建请求参数
            tts_config = BAIDU_SPEECH_CONFIG["tts"]
            params = {
                "tex": text,
                "tok": self.baidu_access_token,
                "cuid": "voice_assistant",
                "ctp": tts_config["ctp"],
                "lan": tts_config["lan"],
                "per": tts_config["per"],
                "spd": tts_config["spd"],
                "pit": tts_config["pit"],
                "vol": tts_config["vol"],
                "aue": tts_config["aue"]
            }

            # 发送请求
            response = requests.post(tts_config["url"], data=params)

            # 检查响应类型
            content_type = response.headers.get('Content-Type', '')

            if content_type.startswith('audio'):
                # 保存音频文件
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                print("✅ 百度云语音合成成功")
                return True
            else:
                # 错误响应
                try:
                    error_result = response.json()
                    print(f"❌ 百度云语音合成失败: {error_result}")
                except:
                    print(f"❌ 百度云语音合成失败: {response.text}")
                return False

        except Exception as e:
            print(f"❌ 百度云语音合成异常: {e}")
            return False

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
            print(f"❌ 句子语音合成失败: {e}")
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
                    print(f"❌ 音频播放失败: {e}")
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
                print(f"❌ 音频播放线程错误: {e}")

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
            print(f"❌ 流式语音处理错误: {e}")
        finally:
            self.is_playing = False

        return full_text

    def call_deepseek_api(self, prompt, retries=3, delay=5, use_context=True):
        """调用 DeepSeek API 获取回复"""
        # 过滤掉非法字符（例如表情符号等）
        prompt = prompt.encode('utf-8', 'ignore').decode('utf-8')

        for attempt in range(retries):
            try:
                print(f"🔄 正在调用 API (尝试 {attempt + 1}/{retries})...")

                # 构建消息列表
                messages = []

                # 如果启用上下文且在长对话模式下，添加历史对话
                if use_context and self.long_conversation_mode:
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
                print(f"❌ 请求 DeepSeek API 失败：{e}")
                if attempt < retries - 1:
                    print(f"重试中... (尝试 {attempt + 1}/{retries})")
                    time.sleep(delay)
                else:
                    return "❌ 请求 DeepSeek API 超过最大重试次数，无法获取回复"

    async def text_to_speech(self, text, output_path, voice=None):
        """文本转语音"""
        try:
            if voice is None:
                voice = self.voice_name
            communicate = Communicate(text, voice)
            await communicate.save(output_path)
        except Exception as e:
            print(f"❌ TTS 合成失败: {e}")

    def play_audio(self, file_path):
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
        except pygame.error as e:
            print(f"❌ 音频播放失败: {e}")
        finally:
            pygame.mixer.quit()

    def change_voice(self):
        """切换语音"""
        print("\n🎤 可用语音选项：")
        for i, (key, voice_name) in enumerate(VOICE_OPTIONS.items(), 1):
            current_mark = " (当前)" if key == self.current_voice else ""
            print(f"   {i}. {key} - {voice_name}{current_mark}")

        try:
            choice = input("\n请输入语音编号或名称：").strip()

            # 如果输入的是数字
            if choice.isdigit():
                choice_num = int(choice)
                if 1 <= choice_num <= len(VOICE_OPTIONS):
                    voice_key = list(VOICE_OPTIONS.keys())[choice_num - 1]
                    self.current_voice = voice_key
                    self.voice_name = VOICE_OPTIONS[voice_key]
                    print(f"✅ 语音已切换为: {voice_key}")
                else:
                    print("❌ 无效的编号")
            # 如果输入的是语音名称
            elif choice in VOICE_OPTIONS:
                self.current_voice = choice
                self.voice_name = VOICE_OPTIONS[choice]
                print(f"✅ 语音已切换为: {choice}")
            else:
                print("❌ 无效的语音选择")
        except ValueError:
            print("❌ 输入格式错误")

    def voice_chat(self):
        """语音对话功能"""
        print("\n🎤 进入语音对话模式")
        print("💡 说话完毕后按 Enter 键停止录音，输入 'exit' 退出语音对话模式")

        while True:
            try:
                user_input = input("\n按 Enter 开始录音，或输入 'exit' 退出语音对话: ").strip()

                if user_input.lower() in ['exit', '退出', 'q']:
                    print("👋 退出语音对话模式")
                    break

                # 录制音频
                audio_file = self.record_audio()
                if not audio_file:
                    print("❌ 录音失败，请重试")
                    continue

                # 语音识别
                print("🔍 正在进行语音识别...")
                recognized_text = self.baidu_speech_recognition(audio_file)
                if not recognized_text:
                    print("❌ 语音识别失败，请重试")
                    continue

                print(f"🎯 识别结果: {recognized_text}")

                # 调用AI获取回复
                print("🤖 正在生成回复...")
                response = self.call_deepseek_api(recognized_text)

                if not response:
                    print("❌ AI回复生成失败")
                    continue

                # 保存对话记录
                self.add_conversation_record(recognized_text, response, "voice")

                # 语音合成和播放
                if self.use_baidu_tts:
                    # 使用百度云TTS
                    print("🎵 正在使用百度云进行语音合成...")
                    cleaned_response = self.clean_markdown(response)
                    cleaned_response = self.remove_emojis_and_symbols(cleaned_response)

                    if len(cleaned_response.strip()) < 2:
                        print("⚠️ 清理后文本过短，跳过语音合成")
                        continue

                    output_path = os.path.join(self.audio_temp, "baidu_tts_reply.mp3")
                    if self.baidu_text_to_speech(cleaned_response, output_path):
                        print("🔊 正在播放语音...")
                        self.play_audio(output_path)
                        print("✅ 语音播放完成")
                    else:
                        print("❌ 百度云语音合成失败")
                else:
                    # 使用原有的edge-tts（如果流式语音已开启则跳过）
                    if not (self.stream and self.enable_streaming_tts):
                        cleaned_response = self.clean_markdown(response)
                        cleaned_response = self.remove_emojis_and_symbols(cleaned_response)

                        if len(cleaned_response.strip()) >= 2:
                            print("🎵 正在生成语音...")
                            output_path = os.path.join(self.audio_temp, "voice_reply.mp3")
                            asyncio.run(self.text_to_speech(cleaned_response, output_path))

                            print("🔊 正在播放语音...")
                            self.play_audio(output_path)
                            print("✅ 播放完成")

                # 清理临时文件
                try:
                    if os.path.exists(audio_file):
                        os.remove(audio_file)
                except:
                    pass

            except KeyboardInterrupt:
                print("\n🛑 语音对话被中断")
                break
            except Exception as e:
                print(f"❌ 语音对话过程中发生错误: {e}")

    def long_voice_chat(self):
        """长对话模式 - 自动语音检测"""
        print("\n🎙️ 进入长对话模式")
        print("💡 自动检测语音，说话完毕后自动停止录音")
        print("🔧 配置信息:")
        print(f"   静音阈值: {self.silence_threshold}")
        print(f"   静音时长: {self.silence_duration}秒")
        print(f"   最小录音时长: {self.min_recording_duration}秒")
        print("📝 输入 'exit' 退出长对话模式")

        self.long_conversation_mode = True
        conversation_count = 0

        while True:
            try:
                conversation_count += 1
                print(f"\n🔄 第 {conversation_count} 轮对话")
                print("-" * 30)

                user_input = input("按 Enter 开始自动录音，或输入 'exit' 退出: ").strip()

                if user_input.lower() in ['exit', '退出', 'q']:
                    print("👋 退出长对话模式")
                    break

                # 自动录制音频
                print("🎤 开始自动录音...")
                audio_file = self.record_audio(auto_detect=True)
                if not audio_file:
                    print("❌ 录音失败，请重试")
                    continue

                # 语音识别
                print("🔍 正在进行语音识别...")
                recognized_text = self.baidu_speech_recognition(audio_file)
                if not recognized_text:
                    print("❌ 语音识别失败，请重试")
                    continue

                print(f"🎯 识别结果: {recognized_text}")

                # 调用AI获取回复（使用上下文）
                print("🤖 正在生成回复...")
                response = self.call_deepseek_api(recognized_text, use_context=True)

                if not response:
                    print("❌ AI回复生成失败")
                    continue

                # 保存对话记录
                self.add_conversation_record(recognized_text, response, "voice")

                # 语音合成和播放
                self.play_ai_response(response)

                # 清理临时文件
                try:
                    if os.path.exists(audio_file):
                        os.remove(audio_file)
                except:
                    pass

                print("✅ 本轮对话完成")

            except KeyboardInterrupt:
                print("\n🛑 长对话被中断")
                break
            except Exception as e:
                print(f"❌ 长对话过程中发生错误: {e}")

        self.long_conversation_mode = False

    def play_ai_response(self, response):
        """播放AI回复"""
        try:
            if self.use_baidu_tts:
                # 使用百度云TTS
                print("🎵 正在使用百度云进行语音合成...")
                cleaned_response = self.clean_markdown(response)
                cleaned_response = self.remove_emojis_and_symbols(cleaned_response)

                if len(cleaned_response.strip()) < 2:
                    print("⚠️ 清理后文本过短，跳过语音合成")
                    return

                output_path = os.path.join(self.audio_temp, "baidu_tts_reply.mp3")
                if self.baidu_text_to_speech(cleaned_response, output_path):
                    print("🔊 正在播放语音...")
                    self.play_audio(output_path)
                    print("✅ 语音播放完成")
                else:
                    print("❌ 百度云语音合成失败，使用Edge-TTS备选")
                    self.play_edge_tts_response(response)
            else:
                # 使用Edge-TTS
                self.play_edge_tts_response(response)
        except Exception as e:
            print(f"❌ 播放AI回复失败: {e}")

    def play_edge_tts_response(self, response):
        """使用Edge-TTS播放回复"""
        try:
            if not (self.stream and self.enable_streaming_tts):
                cleaned_response = self.clean_markdown(response)
                cleaned_response = self.remove_emojis_and_symbols(cleaned_response)

                if len(cleaned_response.strip()) >= 2:
                    print("🎵 正在使用Edge-TTS生成语音...")
                    output_path = os.path.join(self.audio_temp, "voice_reply.mp3")
                    asyncio.run(self.text_to_speech(cleaned_response, output_path))

                    print("🔊 正在播放语音...")
                    self.play_audio(output_path)
                    print("✅ 播放完成")
        except Exception as e:
            print(f"❌ Edge-TTS播放失败: {e}")

    def show_conversation_history(self):
        """显示对话历史"""
        if not self.conversation_history:
            print("📝 暂无对话历史记录")
            return

        print(f"\n📚 对话历史记录 (共 {len(self.conversation_history)} 条)")
        print("=" * 60)

        # 显示最近的10条记录
        recent_history = self.conversation_history[-10:]
        for i, record in enumerate(recent_history, 1):
            timestamp = record["timestamp"]
            input_type = record["input_type"]
            user_input = record["user_input"]
            ai_response = record["ai_response"]

            # 格式化时间戳
            try:
                dt = datetime.datetime.fromisoformat(timestamp)
                time_str = dt.strftime("%m-%d %H:%M")
            except:
                time_str = timestamp[:16]

            print(f"\n{i}. [{time_str}] {'🎤' if input_type == 'voice' else '💬'}")
            print(f"   用户: {user_input}")
            print(f"   AI: {ai_response[:100]}{'...' if len(ai_response) > 100 else ''}")

        if len(self.conversation_history) > 10:
            print(f"\n... 还有 {len(self.conversation_history) - 10} 条更早的记录")

    def clear_conversation_history(self):
        """清空对话历史"""
        try:
            user_input = input("⚠️ 确定要清空所有对话历史吗？(y/N): ").strip().lower()
            if user_input in ['y', 'yes', '是']:
                self.conversation_history = []
                self.save_conversation_history()
                print("✅ 对话历史已清空")
            else:
                print("❌ 操作已取消")
        except Exception as e:
            print(f"❌ 清空对话历史失败: {e}")

    def run(self):
        print("\U0001F7E2 文本语音助手已启动！")
        print(f"📋 配置信息：")
        print(f"   🌐 API 端点: {self.base_url}")
        print(f"   🤖 模型: {self.model}")
        print(f"   🌊 流式响应: {'开启' if self.stream else '关闭'}")
        print(f"   🎯 最大令牌: {self.max_tokens}")
        print(f"   🌡️ 温度: {self.temperature}")
        print(f"   🎤 当前语音: {self.current_voice}")
        print(f"   🎙️ 流式语音: {'开启' if self.enable_streaming_tts else '关闭'}")
        print(f"   🗣️ 语音对话: {'开启' if self.enable_voice_chat else '关闭'}")
        print(f"   🔊 百度云TTS: {'开启' if self.use_baidu_tts else '关闭'}")
        print(f"   🤖 自动语音检测: {'开启' if self.auto_voice_detection else '关闭'}")
        print(f"   📚 对话记录: {len(self.conversation_history)} 条")
        print("\n🎙️ 长对话模式 - 自动语音检测对话")
        print("� 按 Enter 开始对话，系统自动检测语音开始和结束")
        print("❌ 输入 'quit' 或 Ctrl+C 退出")

        while True:
            try:
                prompt = input("\n\U0001F4DD 请输入你的提问内容：").strip()
                if not prompt:
                    print("⚠️ 输入为空，跳过")
                    continue

                if prompt.lower() in ['quit', 'exit', '退出', 'q']:
                    print("👋 再见！")
                    break

                if prompt.lower() in ['voice', '语音', 'v']:
                    self.change_voice()
                    continue

                if prompt.lower() in ['record', '录音', 'r']:
                    if not self.enable_voice_chat:
                        print("❌ 语音对话功能未开启，请在.env文件中设置ENABLE_VOICE_CHAT=true")
                        continue

                    if not self.baidu_access_token:
                        print("❌ 百度云API未配置或访问令牌获取失败")
                        continue

                    # 开始语音对话
                    self.voice_chat()
                    continue

                if prompt.lower() in ['long', '长对话', 'l']:
                    if not self.enable_voice_chat:
                        print("❌ 语音对话功能未开启，请在.env文件中设置ENABLE_VOICE_CHAT=true")
                        continue

                    if not self.baidu_access_token:
                        print("❌ 百度云API未配置或访问令牌获取失败")
                        continue

                    # 开始长对话模式
                    self.long_voice_chat()
                    continue

                if prompt.lower() in ['history', '历史', 'h']:
                    self.show_conversation_history()
                    continue

                if prompt.lower() in ['clear', '清空', 'c']:
                    self.clear_conversation_history()
                    continue

                print(f"\U0001F5E3️ 用户提问：{prompt}")
                response = self.call_deepseek_api(prompt)

                if not self.stream:
                    print(f"\U0001F916 回复（原始）：{response}")

                # 保存对话记录
                if response:
                    self.add_conversation_record(prompt, response, "text")

                # 如果启用了流式语音，则跳过额外的语音合成
                if self.stream and self.enable_streaming_tts:
                    print("✅ 流式语音播放完成")
                else:
                    # 清理 Markdown 符号和表情包后再语音合成
                    cleaned_response = self.clean_markdown(response)
                    # 进一步移除表情符号和特殊符号
                    cleaned_response = self.remove_emojis_and_symbols(cleaned_response)

                    # 检查清理后的文本是否为空或过短
                    if len(cleaned_response.strip()) < 2:
                        print("⚠️ 清理后文本过短，跳过语音合成")
                        continue

                    print(f"🧹 清理后文本：{cleaned_response}")

                    print("🎵 正在生成语音...")
                    output_path = os.path.join(self.audio_temp, "reply.mp3")
                    asyncio.run(self.text_to_speech(cleaned_response, output_path))

                    print("🔊 正在播放语音...")
                    self.play_audio(output_path)
                    print("✅ 播放完成")

            except KeyboardInterrupt:
                print("\n🛑 手动退出")
                break

if __name__ == "__main__":
    assistant = TextVoiceAssistant()
    assistant.run()
