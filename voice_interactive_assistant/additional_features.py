#!/usr/bin/env python3
"""
附加功能模块 - 包含其他非核心功能
"""

import os
import json
import datetime
from long_conversation_assistant import LongConversationAssistant

class AdditionalFeatures:
    def __init__(self, assistant: LongConversationAssistant):
        self.assistant = assistant

    def show_conversation_history(self, limit=10):
        """显示对话历史"""
        if not self.assistant.conversation_history:
            print("📝 暂无对话历史记录")
            return

        print(f"\n📚 对话历史记录 (共 {len(self.assistant.conversation_history)} 条)")
        print("=" * 60)

        # 显示最近的记录
        recent_history = self.assistant.conversation_history[-limit:]
        for i, record in enumerate(recent_history, 1):
            timestamp = record["timestamp"]
            user_input = record["user_input"]
            ai_response = record["ai_response"]

            # 格式化时间戳
            try:
                dt = datetime.datetime.fromisoformat(timestamp)
                time_str = dt.strftime("%m-%d %H:%M")
            except:
                time_str = timestamp[:16]

            print(f"\n{i}. [{time_str}] 🎤")
            print(f"   用户: {user_input}")
            print(f"   AI: {ai_response[:100]}{'...' if len(ai_response) > 100 else ''}")

        if len(self.assistant.conversation_history) > limit:
            print(f"\n... 还有 {len(self.assistant.conversation_history) - limit} 条更早的记录")

    def clear_conversation_history(self):
        """清空对话历史"""
        try:
            user_input = input("⚠️ 确定要清空所有对话历史吗？(y/N): ").strip().lower()
            if user_input in ['y', 'yes', '是']:
                self.assistant.conversation_history = []
                self.assistant.save_conversation_history()
                print("✅ 对话历史已清空")
            else:
                print("❌ 操作已取消")
        except Exception as e:
            print(f"❌ 清空对话历史失败: {e}")

    def export_conversation_history(self, format='txt'):
        """导出对话历史"""
        try:
            if not self.assistant.conversation_history:
                print("📝 暂无对话历史可导出")
                return

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if format.lower() == 'txt':
                filename = f"conversation_export_{timestamp}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("对话历史导出\n")
                    f.write("=" * 50 + "\n\n")
                    
                    for i, record in enumerate(self.assistant.conversation_history, 1):
                        dt = datetime.datetime.fromisoformat(record["timestamp"])
                        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                        
                        f.write(f"对话 {i} - {time_str}\n")
                        f.write("-" * 30 + "\n")
                        f.write(f"用户: {record['user_input']}\n")
                        f.write(f"AI: {record['ai_response']}\n\n")
                
                print(f"✅ 对话历史已导出到: {filename}")
            
            elif format.lower() == 'json':
                filename = f"conversation_export_{timestamp}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.assistant.conversation_history, f, 
                             ensure_ascii=False, indent=2)
                
                print(f"✅ 对话历史已导出到: {filename}")
            
            else:
                print("❌ 不支持的导出格式，请选择 'txt' 或 'json'")
                
        except Exception as e:
            print(f"❌ 导出对话历史失败: {e}")

    def analyze_conversation_stats(self):
        """分析对话统计信息"""
        if not self.assistant.conversation_history:
            print("📝 暂无对话数据可分析")
            return

        print("\n📊 对话统计分析")
        print("=" * 40)
        
        total_conversations = len(self.assistant.conversation_history)
        print(f"总对话数: {total_conversations}")
        
        # 计算平均长度
        user_lengths = [len(r['user_input']) for r in self.assistant.conversation_history]
        ai_lengths = [len(r['ai_response']) for r in self.assistant.conversation_history]
        
        avg_user_length = sum(user_lengths) / len(user_lengths)
        avg_ai_length = sum(ai_lengths) / len(ai_lengths)
        
        print(f"用户输入平均长度: {avg_user_length:.1f} 字符")
        print(f"AI回复平均长度: {avg_ai_length:.1f} 字符")
        
        # 时间分析
        if total_conversations >= 2:
            first_time = datetime.datetime.fromisoformat(self.assistant.conversation_history[0]['timestamp'])
            last_time = datetime.datetime.fromisoformat(self.assistant.conversation_history[-1]['timestamp'])
            duration = last_time - first_time
            
            print(f"对话时间跨度: {duration}")
            
            if duration.total_seconds() > 0:
                conversations_per_hour = total_conversations / (duration.total_seconds() / 3600)
                print(f"平均对话频率: {conversations_per_hour:.1f} 次/小时")

    def voice_settings_menu(self):
        """语音设置菜单"""
        from config import VOICE_OPTIONS
        
        print("\n🎵 语音设置")
        print("=" * 30)
        print("可用语音:")
        
        voices = list(VOICE_OPTIONS.keys())
        for i, voice_key in enumerate(voices, 1):
            voice_name = VOICE_OPTIONS[voice_key]
            current = "✅" if voice_key == self.assistant.current_voice else "  "
            print(f"{current} {i}. {voice_key} - {voice_name}")
        
        try:
            choice = input(f"\n请选择语音 (1-{len(voices)}) 或按 Enter 取消: ").strip()
            if choice:
                index = int(choice) - 1
                if 0 <= index < len(voices):
                    new_voice = voices[index]
                    self.assistant.current_voice = VOICE_OPTIONS[new_voice]
                    print(f"✅ 语音已切换为: {new_voice}")
                else:
                    print("❌ 无效的选择")
        except ValueError:
            print("❌ 输入格式错误")

    def system_info(self):
        """显示系统信息"""
        print("\n🔧 系统信息")
        print("=" * 30)
        print(f"DeepSeek API: {'✅ 已配置' if self.assistant.api_key else '❌ 未配置'}")
        print(f"百度云API: {'✅ 已配置' if self.assistant.baidu_access_token else '❌ 未配置'}")
        print(f"当前语音: {self.assistant.current_voice}")
        print(f"流式响应: {'开启' if self.assistant.stream else '关闭'}")
        print(f"最大令牌: {self.assistant.max_tokens}")
        print(f"温度: {self.assistant.temperature}")
        print(f"对话记录: {len(self.assistant.conversation_history)} 条")
        
        print("\n🎤 语音检测参数:")
        print(f"语音开始阈值: {self.assistant.voice_start_threshold}")
        print(f"静音检测阈值: {self.assistant.silence_threshold}")
        print(f"静音持续时间: {self.assistant.silence_duration}秒")
        print(f"最小录音时长: {self.assistant.min_recording_duration}秒")

    def help_menu(self):
        """帮助菜单"""
        print("\n❓ 帮助信息")
        print("=" * 40)
        print("🎙️ 长对话模式:")
        print("  - 自动检测语音开始和结束")
        print("  - 保持对话上下文记忆")
        print("  - 自动保存对话历史")
        print()
        print("🔧 语音检测原理:")
        print("  1. 监听环境音频")
        print("  2. 检测到语音能量超过阈值时开始录音")
        print("  3. 检测到持续静音时自动停止")
        print("  4. 进行语音识别和AI对话")
        print()
        print("⚙️ 参数调优建议:")
        print("  - 安静环境: 降低静音阈值")
        print("  - 嘈杂环境: 提高静音阈值")
        print("  - 快速对话: 缩短静音时长")
        print("  - 慢速对话: 延长静音时长")

def additional_features_menu():
    """附加功能菜单"""
    from long_conversation_assistant import LongConversationAssistant
    
    assistant = LongConversationAssistant()
    features = AdditionalFeatures(assistant)
    
    print("🔧 附加功能菜单")
    print("=" * 30)
    
    while True:
        print("\n请选择功能:")
        print("1. 📚 查看对话历史")
        print("2. 🗑️ 清空对话历史")
        print("3. 📤 导出对话历史")
        print("4. 📊 对话统计分析")
        print("5. 🎵 语音设置")
        print("6. 🔧 系统信息")
        print("7. ❓ 帮助信息")
        print("8. 🚀 启动长对话模式")
        print("9. ❌ 退出")
        
        choice = input("\n请输入选择 (1-9): ").strip()
        
        if choice == '1':
            features.show_conversation_history()
        elif choice == '2':
            features.clear_conversation_history()
        elif choice == '3':
            format_choice = input("选择导出格式 (txt/json): ").strip()
            features.export_conversation_history(format_choice)
        elif choice == '4':
            features.analyze_conversation_stats()
        elif choice == '5':
            features.voice_settings_menu()
        elif choice == '6':
            features.system_info()
        elif choice == '7':
            features.help_menu()
        elif choice == '8':
            assistant.run()
            break
        elif choice == '9':
            print("👋 再见！")
            break
        else:
            print("❌ 无效选择，请重试")

if __name__ == "__main__":
    additional_features_menu()
