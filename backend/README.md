# Backend - Video Downloader API

Backend API sử dụng FastAPI để tải video từ YouTube, Facebook, TikTok.

## Cài đặt

1. Tạo virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Trên Windows: venv\Scripts\activate
```

2. Cài đặt dependencies:
```bash
pip install -r requirements.txt
```

## Chạy ứng dụng

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API sẽ chạy tại: http://localhost:8000

## API Endpoints

### `GET /`
Health check endpoint

### `POST /api/download`
Bắt đầu tải video

**Request body:**
```json
{
  "url": "https://youtube.com/watch?v=...",
  "format_id": "optional",
  "output_format": "mp4",
  "quality": "1080p",
  "audio_only": false
}
```

**Response:**
```json
{
  "task_id": "uuid",
  "message": "Đã bắt đầu tải video",
  "video_info": {...}
}
```

### `GET /api/info?url=...`
Lấy thông tin video mà không tải

### `GET /api/status/{task_id}`
Kiểm tra trạng thái tải

### `GET /api/download/{task_id}`
Tải file video đã hoàn thành

### `WebSocket /ws/{task_id}`
Kết nối WebSocket để nhận cập nhật tiến trình real-time

### `DELETE /api/task/{task_id}`
Xóa task và file đã tải

## Lưu ý

- Cần cài đặt FFmpeg để convert video/audio
- Files được lưu tạm trong thư mục `downloads/`
- Hỗ trợ YouTube, Facebook, TikTok

