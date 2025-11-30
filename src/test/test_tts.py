# test_tts.py
import asyncio
import edge_tts

async def main():
    communicate = edge_tts.Communicate("你好，这是一次测试。", "zh-CN-XiaoxiaoNeural")
    await communicate.save("test.mp3")
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())