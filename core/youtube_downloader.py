"""
YouTube Audio Downloader

下载 YouTube 视频的音频流，支持 Apple Silicon 优化
"""

import os
import re
import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple
import yt_dlp


class YouTubeDownloader:
    """
    YouTube 音频下载器

    使用 yt-dlp 下载 YouTube 视频的音频流
    支持 Apple Silicon 优化 (自动使用内置优化)
    """

    def __init__(self, output_dir: str | Path = "storage/youtube"):
        """
        初始化下载器

        Args:
            output_dir: 下载文件的保存目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def sanitize_filename(self, filename: str) -> str:
        """
        清理文件名，移除非法字符

        Args:
            filename: 原始文件名

        Returns:
            清理后的文件名
        """
        # 移除或替换非法字符
        invalid_chars = r'[<>:"/\\|?*]'
        cleaned = re.sub(invalid_chars, '_', filename)
        # 移除开头/结尾的点和空格
        cleaned = cleaned.strip('. ')
        # 确保不是空字符串
        if not cleaned:
            cleaned = "audio"
        return cleaned

    def download_audio(
        self,
        url: str,
        output_name: Optional[str] = None,
        audio_format: str = "best"
    ) -> Dict[str, any]:
        """
        从 YouTube 下载音频

        Args:
            url: YouTube 视频 URL
            output_name: 输出文件名 (不含扩展名)，None 时使用视频标题
            audio_format: 音频格式 (best = 最佳可用质量)

        Returns:
            包含以下键的字典:
            - file_path: 下载的文件路径
            - duration: 音频时长 (秒)
            - title: 视频标题
            - original_url: 原始 URL
            - thumbnail: 封面图片 URL (可选)

        Raises:
            ValueError: URL 无效或下载失败
            Exception: yt-dlp 相关错误
        """
        # 验证 URL
        if not url or not self._is_valid_youtube_url(url):
            raise ValueError(f"无效的 YouTube URL: {url}")

        # 创建时间戳目录
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = self.output_dir / timestamp
        temp_dir.mkdir(parents=True, exist_ok=True)

        # yt-dlp 配置
        ydl_opts = {
            # 音频提取配置
            'format': 'bestaudio/best',
            'extractaudio': True,
            'audioformat': 'm4a',  # 使用 m4a 格式 (兼容性好)
            # 播放列表处理 - 如果是播放列表，只处理第一个视频
            'playlistend': 1,
            'extract_flat': 'in_playlist',  # 提取播放列表中的单个视频
            # 输出配置
            'outtmpl': str(temp_dir / '%(title)s.%(ext)s'),
            # 保存信息到文件
            'writethumbnail': False,
            'writeinfojson': True,  # 保存元数据
            'writesubtitles': False,
            'writeautomaticsub': False,
            # 进度回调
            'progress_hooks': [self._progress_hook],
            # 错误处理
            'ignoreerrors': False,
            'quiet': False,
            'no_warnings': False,
            # 禁用聚合器/处理器
            'extractor_args': {},
        }

        try:
            print(f"🎵 开始下载: {url}")
            print(f"💾 保存目录: {temp_dir}")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                # 获取下载的文件信息
                if not info:
                    raise Exception("无法获取视频信息")

                # 查找下载的文件
                title = info.get('title', 'unknown')
                duration = info.get('duration', 0)
                original_url = info.get('webpage_url', url)
                thumbnail = info.get('thumbnail')

                # 构建输出文件名
                if output_name:
                    output_name = self.sanitize_filename(output_name)
                else:
                    output_name = self.sanitize_filename(title)

                # 查找实际下载的文件
                downloaded_files = list(temp_dir.glob(f"{title}.*"))
                if not downloaded_files:
                    # 可能是文件名被截断，尝试其他方式查找
                    downloaded_files = list(temp_dir.glob("*"))

                if not downloaded_files:
                    raise Exception("下载成功但未找到文件")

                downloaded_file = downloaded_files[0]

                # 重命名文件为规范名称
                final_path = temp_dir / f"{output_name}{downloaded_file.suffix}"
                if final_path != downloaded_file:
                    downloaded_file.rename(final_path)
                else:
                    final_path = downloaded_file

                result = {
                    "file_path": str(final_path),
                    "duration": duration,
                    "title": title,
                    "original_url": original_url,
                    "timestamp": timestamp,
                }

                if thumbnail:
                    result["thumbnail"] = thumbnail

                # 保存 info.json
                try:
                    import json
                    info_file = temp_dir / "info.json"
                    with open(info_file, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    print(f"💾 信息已保存到: {info_file}")
                except Exception as e:
                    print(f"⚠️ 无法保存 info.json: {e}")

                print(f"✅ 下载完成: {final_path.name}")
                print(f"   时长: {duration} 秒")
                print(f"   标题: {title}")

                return result

        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            if "age" in error_msg.lower() or "restricted" in error_msg.lower():
                raise ValueError(f"视频受限 (年龄限制或地区限制): {error_msg}")
            elif "private" in error_msg.lower():
                raise ValueError(f"视频是私有的: {error_msg}")
            elif "unavailable" in error_msg.lower():
                raise ValueError(f"视频不可用: {error_msg}")
            else:
                raise ValueError(f"下载失败: {error_msg}")
        except Exception as e:
            raise Exception(f"YouTube 下载错误: {str(e)}")

    def _progress_hook(self, d: Dict[str, any]):
        """yt-dlp 进度回调"""
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', 'N/A')
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            filename = d.get('filename', 'unknown')
            print(f"   下载中... {percent} | {speed} | ETA: {eta}")
        elif d['status'] == 'finished':
            print(f"   下载完成，正在处理...")

    def _is_valid_youtube_url(self, url: str) -> bool:
        """验证是否为有效的 YouTube URL (排除播放列表)"""
        # 检查是否为播放列表URL - 拒绝播放列表
        if 'youtube.com/playlist' in url.lower() or 'list=' in url:
            return False

        patterns = [
            r'^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/).+$',
            r'^(https?://)?(www\.)?youtube\.com/watch\?.*v=[a-zA-Z0-9_-]+',
        ]
        for pattern in patterns:
            if re.match(pattern, url, re.IGNORECASE):
                return True
        return False

    def get_download_info(self, timestamp: str) -> Optional[Dict[str, any]]:
        """
        获取指定时间戳的下载信息

        Args:
            timestamp: 下载时间戳 (YYYYMMDD_HHMMSS)

        Returns:
            下载信息字典，如果不存在返回 None
        """
        download_dir = self.output_dir / timestamp
        if not download_dir.exists():
            return None

        info_file = download_dir / "info.json"
        if info_file.exists():
            import json
            with open(info_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        return None

    def list_downloads(self) -> list[Dict[str, any]]:
        """
        列出所有下载记录

        Returns:
            下载记录列表
        """
        downloads = []

        for item in self.output_dir.iterdir():
            if item.is_dir():
                info = self.get_download_info(item.name)
                if info:
                    downloads.append(info)
                else:
                    # 检查是否有音频文件
                    audio_files = list(item.glob("*.m4a"))
                    audio_files.extend(item.glob("*.mp3"))
                    audio_files.extend(item.glob("*.wav"))
                    if audio_files:
                        downloads.append({
                            "timestamp": item.name,
                            "file_count": len(audio_files),
                        })

        # 按时间倒序排序
        downloads.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return downloads


def download_audio_from_youtube(
    url: str,
    output_dir: str | Path = "storage/youtube",
    output_name: Optional[str] = None
) -> Dict[str, any]:
    """
    便捷函数：从 YouTube 下载音频

    Args:
        url: YouTube 视频 URL
        output_dir: 输出目录
        output_name: 输出文件名 (不含扩展名)

    Returns:
        下载信息字典
    """
    downloader = YouTubeDownloader(output_dir)
    return downloader.download_audio(url, output_name)


if __name__ == "__main__":
    # 测试
    import sys

    if len(sys.argv) < 2:
        print("用法: python youtube_downloader.py <youtube_url> [output_name]")
        sys.exit(1)

    url = sys.argv[1]
    output_name = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        result = download_audio_from_youtube(url, output_name=output_name)
        print(f"\n下载结果: {result}")
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
