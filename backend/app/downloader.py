import yt_dlp
import os
import asyncio
from typing import Optional, Dict, Any, Callable
from pathlib import Path
import re

from .models import VideoInfo, VideoFormat, OutputFormat


class VideoDownloader:
    """Class để tải video từ YouTube, Facebook, TikTok sử dụng yt-dlp"""
    
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
    def _is_valid_url(self, url: str) -> bool:
        """Kiểm tra URL có hợp lệ và hỗ trợ không"""
        patterns = [
            r'(?:youtube\.com|youtu\.be)',
            r'facebook\.com',
            r'fb\.watch',
            r'tiktok\.com',
            r'instagram\.com',
        ]
        return any(re.search(pattern, url, re.IGNORECASE) for pattern in patterns)
    
    async def get_video_info(self, url: str) -> VideoInfo:
        """Lấy thông tin video (formats, title, duration)"""
        if not self._is_valid_url(url):
            raise ValueError("URL không được hỗ trợ. Chỉ hỗ trợ YouTube, Facebook, TikTok")
        
        def extract_info():
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        
        # Chạy trong thread pool để không block event loop
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, extract_info)
        
        # Parse formats
        formats = []
        if 'formats' in info:
            for fmt in info['formats']:
                if fmt.get('vcodec') != 'none' or fmt.get('acodec') != 'none':
                    formats.append(VideoFormat(
                        format_id=fmt.get('format_id', ''),
                        ext=fmt.get('ext', ''),
                        resolution=fmt.get('resolution'),
                        filesize=fmt.get('filesize'),
                        filesize_approx=fmt.get('filesize_approx'),
                        vcodec=fmt.get('vcodec'),
                        acodec=fmt.get('acodec'),
                        fps=fmt.get('fps'),
                        tbr=fmt.get('tbr'),
                        vbr=fmt.get('vbr'),
                        abr=fmt.get('abr'),
                    ))
        
        return VideoInfo(
            id=info.get('id', ''),
            title=info.get('title', 'Unknown'),
            duration=info.get('duration'),
            thumbnail=info.get('thumbnail'),
            uploader=info.get('uploader'),
            formats=formats,
            webpage_url=info.get('webpage_url', url)
        )
    
    async def download_video(
        self,
        url: str,
        task_id: str,
        format_id: Optional[str] = None,
        output_format: OutputFormat = OutputFormat.MP4,
        audio_only: bool = False,
        progress_hook: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """Tải video với format và chất lượng được chỉ định"""
        if not self._is_valid_url(url):
            raise ValueError("URL không được hỗ trợ")
        
        # Sử dụng task_id được cung cấp
        output_template = str(self.download_dir / f"{task_id}.%(ext)s")
        
        def download():
            ydl_opts = {
                'outtmpl': output_template,
                'quiet': False,
                'no_warnings': True,
                'progress_hooks': [progress_hook] if progress_hook else [],
            }
            
            if audio_only:
                # Chỉ tải audio
                if output_format == OutputFormat.MP3:
                    ydl_opts['format'] = 'bestaudio/best'
                    ydl_opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }]
                elif output_format == OutputFormat.M4A:
                    ydl_opts['format'] = 'bestaudio/best'
                    ydl_opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'm4a',
                    }]
            else:
                # Tải video
                if format_id:
                    ydl_opts['format'] = format_id
                else:
                    # Chọn format tốt nhất
                    if output_format == OutputFormat.MP4:
                        ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                    elif output_format == OutputFormat.WEBM:
                        ydl_opts['format'] = 'bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]/best'
                    else:
                        ydl_opts['format'] = 'best'
                
                # Convert sang format mong muốn nếu cần
                if output_format == OutputFormat.MP4:
                    ydl_opts['postprocessors'] = [{
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    }]
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return info
        
        # Chạy trong thread pool
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, download)
        
        # Tìm file đã tải
        downloaded_file = None
        for ext in ['mp4', 'webm', 'mp3', 'm4a', 'mkv']:
            file_path = self.download_dir / f"{task_id}.{ext}"
            if file_path.exists():
                downloaded_file = file_path
                break
        
        if not downloaded_file:
            raise FileNotFoundError("Không tìm thấy file đã tải")
        
        return {
            'task_id': task_id,
            'file_path': str(downloaded_file),
            'file_name': downloaded_file.name,
            'file_size': downloaded_file.stat().st_size,
            'title': info.get('title', 'Unknown'),
        }

