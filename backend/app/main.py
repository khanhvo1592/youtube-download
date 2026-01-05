from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import uuid
from typing import Dict, Optional
from pathlib import Path
import json

from .models import (
    DownloadRequest,
    DownloadResponse,
    TaskStatus,
    DownloadStatus,
    VideoInfo,
    OutputFormat
)
from .downloader import VideoDownloader

app = FastAPI(title="Video Downloader API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong production nên giới hạn domain cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo downloader
downloader = VideoDownloader(download_dir="downloads")

# Lưu trữ trạng thái các task
tasks: Dict[str, TaskStatus] = {}

# WebSocket connections
active_connections: Dict[str, WebSocket] = {}


def progress_hook_factory(task_id: str, loop: asyncio.AbstractEventLoop):
    """Tạo progress hook cho một task"""
    def hook(d: dict):
        status = tasks.get(task_id)
        if not status:
            return
        
        if d['status'] == 'downloading':
            if 'total_bytes' in d:
                percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
            elif 'total_bytes_estimate' in d:
                percent = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
            else:
                percent = 0
            
            status.progress = min(percent, 99.0)
            status.status = DownloadStatus.DOWNLOADING
            status.message = f"Đang tải: {d.get('_percent_str', '0%')}"
        elif d['status'] == 'finished':
            status.progress = 100.0
            status.status = DownloadStatus.PROCESSING
            status.message = "Đang xử lý..."
        
        # Gửi update qua WebSocket nếu có connection (từ thread khác)
        if loop and not loop.is_closed():
            try:
                asyncio.run_coroutine_threadsafe(
                    send_progress_update(task_id, status),
                    loop
                )
            except Exception as e:
                print(f"Lỗi schedule progress update: {e}")
    
    return hook


async def send_progress_update(task_id: str, status: TaskStatus):
    """Gửi cập nhật tiến trình qua WebSocket"""
    if task_id not in active_connections:
        return
    
    websocket = active_connections[task_id]
    
    try:
        await websocket.send_json(status.dict())
    except (WebSocketDisconnect, RuntimeError, ConnectionError) as e:
        # WebSocket đã đóng hoặc bị ngắt kết nối
        # Xóa connection khỏi danh sách để tránh lỗi tiếp theo
        if task_id in active_connections:
            del active_connections[task_id]
    except Exception:
        # Các lỗi khác - bỏ qua để tránh spam log
        pass


async def download_task(
    task_id: str,
    url: str,
    format_id: Optional[str],
    output_format: OutputFormat,
    audio_only: bool
):
    """Background task để tải video"""
    try:
        status = tasks[task_id]
        status.status = DownloadStatus.DOWNLOADING
        status.message = "Đang bắt đầu tải..."
        
        # Lấy event loop hiện tại để dùng trong progress hook
        loop = asyncio.get_event_loop()
        
        # Tạo progress hook với event loop
        hook = progress_hook_factory(task_id, loop)
        
        # Tải video
        result = await downloader.download_video(
            url=url,
            task_id=task_id,
            format_id=format_id,
            output_format=output_format,
            audio_only=audio_only,
            progress_hook=hook
        )
        
        # Cập nhật trạng thái thành công
        status.status = DownloadStatus.COMPLETED
        status.progress = 100.0
        status.message = "Tải thành công!"
        status.file_path = result['file_path']
        status.file_name = result['file_name']
        status.file_size = result['file_size']
        
    except Exception as e:
        status.status = DownloadStatus.FAILED
        status.message = "Tải thất bại"
        status.error = str(e)
        print(f"Lỗi tải video: {e}")
    finally:
        # Gửi update cuối cùng
        await send_progress_update(task_id, status)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Video Downloader API", "status": "running"}


@app.post("/api/download", response_model=DownloadResponse)
async def start_download(request: DownloadRequest, background_tasks: BackgroundTasks):
    """Bắt đầu tải video"""
    try:
        # Lấy thông tin video trước
        video_info = await downloader.get_video_info(request.url)
        
        # Tạo task mới
        task_id = str(uuid.uuid4())
        task_status = TaskStatus(
            task_id=task_id,
            status=DownloadStatus.PENDING,
            progress=0.0,
            message="Đang khởi tạo..."
        )
        tasks[task_id] = task_status
        
        # Bắt đầu tải trong background
        background_tasks.add_task(
            download_task,
            task_id=task_id,
            url=request.url,
            format_id=request.format_id,
            output_format=request.output_format,
            audio_only=request.audio_only
        )
        
        return DownloadResponse(
            task_id=task_id,
            message="Đã bắt đầu tải video",
            video_info=video_info
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")


@app.get("/api/info")
async def get_video_info(url: str):
    """Lấy thông tin video mà không tải"""
    try:
        video_info = await downloader.get_video_info(url)
        return video_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")


@app.get("/api/status/{task_id}", response_model=TaskStatus)
async def get_status(task_id: str):
    """Kiểm tra trạng thái tải"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task không tồn tại")
    
    return tasks[task_id]


@app.get("/api/download/{task_id}")
async def download_file(task_id: str):
    """Tải file video đã hoàn thành"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task không tồn tại")
    
    task = tasks[task_id]
    
    if task.status != DownloadStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="File chưa sẵn sàng")
    
    if not task.file_path or not Path(task.file_path).exists():
        raise HTTPException(status_code=404, detail="File không tồn tại")
    
    return FileResponse(
        task.file_path,
        filename=task.file_name,
        media_type='application/octet-stream'
    )


@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket endpoint để nhận cập nhật tiến trình"""
    await websocket.accept()
    active_connections[task_id] = websocket
    
    try:
        # Gửi trạng thái hiện tại ngay lập tức
        if task_id in tasks:
            await websocket.send_json(tasks[task_id].dict())
        
        # Giữ connection mở và gửi updates
        while True:
            # Kiểm tra nếu task đã hoàn thành hoặc thất bại
            if task_id in tasks:
                status = tasks[task_id]
                if status.status in [DownloadStatus.COMPLETED, DownloadStatus.FAILED]:
                    await websocket.send_json(status.dict())
                    await asyncio.sleep(1)
                    break
            
            await asyncio.sleep(0.5)
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Lỗi WebSocket: {e}")
    finally:
        if task_id in active_connections:
            del active_connections[task_id]


@app.delete("/api/task/{task_id}")
async def delete_task(task_id: str):
    """Xóa task và file đã tải (nếu có)"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task không tồn tại")
    
    task = tasks[task_id]
    
    # Xóa file nếu có
    if task.file_path and Path(task.file_path).exists():
        try:
            Path(task.file_path).unlink()
        except Exception as e:
            print(f"Lỗi xóa file: {e}")
    
    # Xóa task
    del tasks[task_id]
    
    return {"message": "Task đã được xóa"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

