"""
YouTube Audio Downloader

下载 YouTube 视频的音频流，支持 Apple Silicon 优化
"""

import os
import re
from pathlib import Path
from typing import Dict, Optional, Tuple
import yt_dlp


class YouTubeDownloader:
    """
    YouTube 音频下载器

    使用 yt-dlp 下载 YouTube 视频的音频流
    支持 Apple Silicon 优化 (自动使用内置优化)
    """

    def __init__(self, output_dir: str | Path | None = None):
        """
        初始化下载器

        Args:
            output_dir: 下载文件的保存目录
        """
        if output_dir is None:
            from api.config import get_storage_dir
            output_dir = get_storage_dir() / "youtube"
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

    def normalize_url(self, url: str) -> str:
        """
        标准化 YouTube URL - 提取视频 ID 并生成干净的 URL

        这会去除播放列表、推荐等额外参数，只保留视频 ID

        Args:
            url: 原始 YouTube URL

        Returns:
            标准化的 URL (格式: https://www.youtube.com/watch?v=VIDEO_ID)

        Raises:
            ValueError: 无法从 URL 提取视频 ID
        """
        video_id = self.extract_video_id(url)
        if not video_id:
            raise ValueError(f"无法从 URL 提取视频 ID: {url}")

        # 返回标准的 YouTube URL 格式
        return f"https://www.youtube.com/watch?v={video_id}"

    def download_audio(
        self,
        url: str,
        output_name: Optional[str] = None,
        audio_format: str = "best",
        normalize: bool = True
    ) -> Dict[str, any]:
        """
        从 YouTube 下载音频

        Args:
            url: YouTube 视频 URL (支持多种格式)
            output_name: 输出文件名 (不含扩展名)，None 时使用视频标题
            audio_format: 音频格式 (best = 最佳可用质量)
            normalize: 是否自动标准化 URL (提取视频 ID，去除播放列表参数)

        Returns:
            包含以下键的字典:
            - file_path: 下载的文件路径
            - duration: 音频时长 (秒)
            - title: 视频标题
            - original_url: 原始 URL
            - normalized_url: 标准化后的 URL (如果 normalize=True)
            - thumbnail: 封面图片 URL (可选)

        Raises:
            ValueError: URL 无效或下载失败
            Exception: yt-dlp 相关错误
        """
        # 验证 URL
        if not url or not self._is_valid_youtube_url(url):
            raise ValueError(f"无效的 YouTube URL: {url}")

        # 标准化 URL - 提取视频 ID，去除播放列表等额外参数
        original_url = url
        if normalize:
            url = self.normalize_url(url)
            print(f"🔗 标准化 URL: {original_url}")
            print(f"   ↓ 使用: {url}")

        # yt-dlp 配置 - 下载到 output_dir 根目录，不创建子文件夹
        ydl_opts = {
            # 音频提取配置 - 使用 M4A (AAC) 格式以获得最佳兼容性
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
                'preferredquality': '192',
            }],
            # 播放列表处理 - 如果是播放列表，只处理第一个视频
            'playlistend': 1,
            'extract_flat': 'in_playlist',  # 提取播放列表中的单个视频
            # 输出配置 - 直接输出到 output_dir 根目录
            'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
            # 保存信息到文件
            'writethumbnail': False,
            'writeinfojson': False,  # 不保存 info.json
            'writesubtitles': False,
            'writeautomaticsub': False,
            # 进度回调
            'progress_hooks': [self._progress_hook],
            # 错误处理
            'ignoreerrors': False,
            'quiet': False,
            'no_warnings': False,
            # 尝试绕过 403 的配置 - 使用 Android 客户端
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                }
            },
        }

        try:
            print(f"🎵 开始下载: {url}")
            print(f"💾 保存目录: {self.output_dir}")

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

                # 查找实际下载的文件 (在 output_dir 根目录)
                downloaded_files = list(self.output_dir.glob(f"{title}.*"))
                if not downloaded_files:
                    # 可能是文件名被截断，尝试其他方式查找
                    downloaded_files = list(self.output_dir.glob("*"))
                    # 过滤出最近修改的文件
                    downloaded_files = [f for f in downloaded_files if f.is_file()]
                    if downloaded_files:
                        downloaded_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

                if not downloaded_files:
                    raise Exception("下载成功但未找到文件")

                downloaded_file = downloaded_files[0]

                # 重命名文件为规范名称
                final_path = self.output_dir / f"{output_name}{downloaded_file.suffix}"
                if final_path != downloaded_file:
                    downloaded_file.rename(final_path)
                else:
                    final_path = downloaded_file

                result = {
                    "file_path": str(final_path),
                    "duration": duration,
                    "title": title,
                    "original_url": original_url,
                    "timestamp": "direct",
                }

                # 如果 URL 被标准化了，返回标准化后的 URL
                if normalize and url != original_url:
                    result["normalized_url"] = url

                if thumbnail:
                    result["thumbnail"] = thumbnail

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

    def extract_video_id(self, url: str) -> Optional[str]:
        """
        从 YouTube URL 中提取视频 ID

        支持的格式:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID&start_radio=1&pp=...
        - https://youtu.be/VIDEO_ID
        - https://youtu.be/VIDEO_ID?list=PLAYLIST_ID

        Args:
            url: YouTube URL

        Returns:
            视频 ID (如: _BCtgSCulIU)，如果无法提取则返回 None
        """
        if not url:
            return None

        url = url.strip()

        # 模式 1: youtu.be/VIDEO_ID (可能有查询参数)
        youtu_be_match = re.search(r'youtu\.be/([a-zA-Z0-9_-]+)', url, re.IGNORECASE)
        if youtu_be_match:
            return youtu_be_match.group(1)

        # 模式 2: youtube.com/watch?v=VIDEO_ID (可能有其他查询参数)
        watch_match = re.search(r'youtube\.com/watch.*[?&]v=([a-zA-Z0-9_-]+)', url, re.IGNORECASE)
        if watch_match:
            return watch_match.group(1)

        # 模式 3: youtube.com/embed/VIDEO_ID
        embed_match = re.search(r'youtube\.com/embed/([a-zA-Z0-9_-]+)', url, re.IGNORECASE)
        if embed_match:
            return embed_match.group(1)

        # 模式 4: youtube.com/shorts/VIDEO_ID
        shorts_match = re.search(r'youtube\.com/shorts/([a-zA-Z0-9_-]+)', url, re.IGNORECASE)
        if shorts_match:
            return shorts_match.group(1)

        # 模式 5: youtube.com/live/VIDEO_ID
        live_match = re.search(r'youtube\.com/live/([a-zA-Z0-9_-]+)', url, re.IGNORECASE)
        if live_match:
            return live_match.group(1)

        # 模式 6: 只有视频 ID 本身
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
            return url

        return None

    def _is_valid_youtube_url(self, url: str) -> bool:
        """
        验证是否为有效的 YouTube URL

        支持的格式:
        - 带有额外参数的 URL: https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID&start_radio=1&pp=...
        - 短 URL: https://youtu.be/VIDEO_ID
        - 纯视频 ID: VIDEO_ID
        """
        # 检查是否为纯播放列表 URL (拒绝整个播放列表页面)
        if 'youtube.com/playlist' in url.lower():
            return False

        # 提取视频 ID 并验证
        video_id = self.extract_video_id(url)
        if not video_id:
            return False

        # 检查视频 ID 长度 (YouTube 视频 ID 通常是 11 个字符)
        if len(video_id) < 6 or len(video_id) > 20:
            return False

        return True


def download_audio_from_youtube(
    url: str,
    output_dir: str | Path | None = None,
    output_name: Optional[str] = None,
    normalize: bool = True
) -> Dict[str, any]:
    """
    便捷函数：从 YouTube 下载音频

    支持的 URL 格式:
    - 标准 URL: https://www.youtube.com/watch?v=VIDEO_ID
    - 复杂 URL: https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID&start_radio=1&pp=...
    - 短 URL: https://youtu.be/VIDEO_ID
    - 嵌入 URL: https://www.youtube.com/embed/VIDEO_ID
    - 纯视频 ID: VIDEO_ID

    Args:
        url: YouTube 视频 URL (支持多种格式)
        output_dir: 输出目录
        output_name: 输出文件名 (不含扩展名)
        normalize: 是否自动标准化 URL (提取视频 ID，去除播放列表参数)

    Returns:
        下载信息字典 (包含 file_path, duration, title, original_url 等)
    """
    downloader = YouTubeDownloader(output_dir)
    return downloader.download_audio(url, output_name, normalize=normalize)


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
