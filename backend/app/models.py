from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class OutputFormat(str, Enum):
    """Định dạng đầu ra"""
    MP4 = "mp4"
    MP3 = "mp3"
    WEBM = "webm"
    M4A = "m4a"


class DownloadRequest(BaseModel):
    """Request model cho việc tải video"""
    url: str = Field(..., description="URL của video cần tải")
    format_id: Optional[str] = Field(None, description="ID format cụ thể (từ yt-dlp)")
    output_format: OutputFormat = Field(OutputFormat.MP4, description="Định dạng đầu ra")
    quality: Optional[str] = Field(None, description="Chất lượng video (720p, 1080p, etc.)")
    audio_only: bool = Field(False, description="Chỉ tải audio")


class VideoFormat(BaseModel):
    """Thông tin về một format video"""
    format_id: str
    ext: str
    resolution: Optional[str] = None
    filesize: Optional[int] = None
    filesize_approx: Optional[int] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    fps: Optional[float] = None
    tbr: Optional[float] = None
    vbr: Optional[float] = None
    abr: Optional[float] = None


class VideoInfo(BaseModel):
    """Thông tin về video"""
    id: str
    title: str
    duration: Optional[int] = None
    thumbnail: Optional[str] = None
    uploader: Optional[str] = None
    formats: List[VideoFormat] = []
    webpage_url: str


class DownloadStatus(str, Enum):
    """Trạng thái tải"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStatus(BaseModel):
    """Trạng thái của task tải"""
    task_id: str
    status: DownloadStatus
    progress: float = Field(0.0, ge=0.0, le=100.0, description="Tiến trình từ 0-100%")
    message: Optional[str] = None
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    error: Optional[str] = None


class DownloadResponse(BaseModel):
    """Response khi bắt đầu tải"""
    task_id: str
    message: str
    video_info: Optional[VideoInfo] = None

