import asyncio
from dotenv import load_dotenv
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import openai, deepgram, siliconflow
import os
# 假设你封装了 SiliconFlow 的 STT/TTS 插件，或者使用 OpenAI 兼容插件
# 这里演示标准架构

load_dotenv()


async def entrypoint(ctx: JobContext):
    # 1. 初始化上下文
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # 2. 配置 AI 组件
    # ASR: 语音转文字 (使用 Deepgram 或 SiliconFlow)
    stt = deepgram.STT()

    # LLM: 大脑 (DeepSeek - 通过 OpenAI 兼容插件)
    # 需要配置 base_url 指向 SiliconFlow
    llm_model = openai.LLM(
        model="deepseek-ai/DeepSeek-V3",
        base_url="https://api.siliconflow.cn/v1",
        api_key=os.getenv("AUDIO_API_KEY"),
    )

    # TTS: 语音合成 (OpenAI / EdgeTTS)
    tts = openai.TTS(model="tts-1", voice="alloy")

    # 3. 创建语音助手
    agent = VoiceAssistant(
        vad=silero.VAD.load(),  # 语音活动检测 (本地运行，极快)
        stt=stt,
        llm=llm_model,
        tts=tts,
        system_prompt="你是一名严厉的面试官。请简短追问候选人。",
    )

    # 4. 启动助手
    agent.start(ctx.room)

    # 5. 监听用户说话 (用于打断)
    # VoiceAssistant 内部会自动处理：
    # 当 VAD 检测到用户说话 -> agent.interrupt() -> 停止 TTS -> 清空队列 -> 听用户说

    await asyncio.sleep(1)
    await agent.say("你好，我是面试官。请做一下自我介绍。", allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
