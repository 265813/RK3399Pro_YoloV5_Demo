"""
语音助手配置文件
"""

# 可用的中文语音选项
VOICE_OPTIONS = {
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",      # 女声，温柔
    "xiaoyi": "zh-CN-XiaoyiNeural",          # 女声，甜美
    "yunjian": "zh-CN-YunjianNeural",        # 男声，成熟
    "yunxi": "zh-CN-YunxiNeural",            # 男声，年轻
    "yunyang": "zh-CN-YunyangNeural",        # 男声，稳重
    "xiaobei": "zh-CN-XiaobeiNeural",        # 女声，活泼
    "xiaomo": "zh-CN-XiaomoNeural",          # 女声，温暖
    "xiaoxuan": "zh-CN-XiaoxuanNeural",      # 女声，清晰
    "xiaorui": "zh-CN-XiaoruiNeural",        # 女声，柔和
    "xiaoshuang": "zh-CN-XiaoshuangNeural",  # 女声，双语
}

# 默认语音
DEFAULT_VOICE = "yunyang"

# API 默认配置
DEFAULT_CONFIG = {
    "base_url": "https://api.ppinfra.com/v3/openai",
    "model": "deepseek/deepseek-v3/community",
    "stream": True,
    "max_tokens": 1000,
    "temperature": 0.7,
}

# 语音合成配置
TTS_CONFIG = {
    "voice": DEFAULT_VOICE,
    "rate": "+0%",      # 语速调整
    "volume": "+0%",    # 音量调整
    "pitch": "+0Hz",    # 音调调整
}

# 百度云语音配置
BAIDU_SPEECH_CONFIG = {
    # 语音识别配置
    "asr": {
        "url": "http://vop.baidu.com/server_api",
        "format": "wav",
        "rate": 16000,
        "channel": 1,
        "dev_pid": 1537,  # 普通话模型
    },
    # 语音合成配置
    "tts": {
        "url": "https://tsn.baidu.com/text2audio",
        "lan": "zh",
        "ctp": "1",
        "per": 1,  # 度小宇=1，度小美=0，度逍遥（基础）=3，度丫丫=4
        "spd": 5,  # 语速 0-15
        "pit": 5,  # 音调 0-15
        "vol": 5,  # 音量 0-9
        "aue": 3,  # 音频格式 3=mp3
    }
}

# 录音配置
RECORDING_CONFIG = {
    "sample_rate": 16000,
    "channels": 1,
    "chunk_size": 1024,
    "format": "int16",
    "max_duration": 60,  # 最大录音时长（秒）
}
