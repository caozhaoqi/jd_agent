import os
import sys
import tempfile
import unittest
from pathlib import Path

# 添加src目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.utils.video_utils import extract_audio_from_video, list_video_files


class TestVideoUtils(unittest.TestCase):

    def setUp(self):
        # 创建临时目录
        self.test_dir = tempfile.mkdtemp()

        # 创建一个简单的视频文件（使用ffmpeg创建）
        self.test_video_path = os.path.join(self.test_dir, "test_video.mp4")

        try:
            import ffmpeg

            # 创建一个10秒的空白视频
            (
                ffmpeg.input("anullsrc", format="lavfi", t=10)
                .input("color=black:640x480:r=25", format="lavfi", t=10)
                .output(
                    self.test_video_path, vcodec="libx264", acodec="aac", shortest=None
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )

            self.video_exists = True
        except Exception as e:
            print(f"创建测试视频失败: {e}")
            self.video_exists = False

    def tearDown(self):
        # 清理临时文件
        if os.path.exists(self.test_video_path):
            os.remove(self.test_video_path)
        os.rmdir(self.test_dir)

    def test_list_video_files(self):
        """测试列出目录中的视频文件"""
        # 创建一些测试文件
        test_files = [
            ("video1.mp4", True),
            ("video2.avi", True),
            ("audio.mp3", False),
            ("document.txt", False),
            ("image.jpg", False),
        ]

        for filename, is_video in test_files:
            file_path = os.path.join(self.test_dir, filename)
            with open(file_path, "w") as f:
                f.write("test content")

        # 测试list_video_files函数
        video_files = list_video_files(self.test_dir)

        # 检查结果
        expected_videos = [
            os.path.join(self.test_dir, "video1.mp4"),
            os.path.join(self.test_dir, "video2.avi"),
        ]
        self.assertEqual(len(video_files), 2)
        for expected in expected_videos:
            self.assertIn(expected, video_files)

        # 清理测试文件
        for filename, _ in test_files:
            file_path = os.path.join(self.test_dir, filename)
            os.remove(file_path)

    def test_extract_audio_from_video(self):
        """测试从视频中提取音频"""
        if not self.video_exists:
            self.skipTest("无法创建测试视频，跳过测试")

        # 测试音频提取功能
        try:
            audio_path = extract_audio_from_video(self.test_video_path)

            # 检查音频文件是否存在
            self.assertTrue(os.path.exists(audio_path))

            # 检查音频文件大小（应该大于0）
            self.assertGreater(os.path.getsize(audio_path), 0)

            # 清理提取的音频文件
            if os.path.exists(audio_path):
                os.remove(audio_path)

        except Exception as e:
            self.fail(f"音频提取失败: {e}")

    def test_extract_audio_from_nonexistent_video(self):
        """测试从不存在的视频文件中提取音频"""
        nonexistent_path = os.path.join(self.test_dir, "nonexistent.mp4")

        with self.assertRaises(FileNotFoundError):
            extract_audio_from_video(nonexistent_path)


if __name__ == "__main__":
    unittest.main()
