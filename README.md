# Video Downloader - Ứng dụng tải video từ YouTube, Facebook, TikTok

Ứng dụng web full-stack để tải video từ các nền tảng YouTube, Facebook và TikTok với giao diện hiện đại và theo dõi tiến trình real-time.

## Tính năng

- ✅ Tải video từ YouTube, Facebook, TikTok
- ✅ Chọn định dạng (MP4, MP3, WEBM, M4A)
- ✅ Chọn chất lượng video (1080p, 720p, 480p, 360p)
- ✅ Tải nhiều video cùng lúc
- ✅ Theo dõi tiến trình tải real-time qua WebSocket
- ✅ Giao diện hiện đại, responsive
- ✅ Hỗ trợ tải audio (MP3, M4A)

## Cấu trúc dự án

```
youtube-download/
├── backend/              # Backend API (FastAPI)
│   ├── app/
│   │   ├── main.py      # FastAPI application
│   │   ├── downloader.py # Video downloader logic
│   │   └── models.py    # Data models
│   ├── requirements.txt
│   └── README.md
├── frontend/            # Frontend (HTML/CSS/JS)
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── README.md
```

## Yêu cầu hệ thống

- Python 3.8+
- FFmpeg (để convert video/audio)
- Node.js (không bắt buộc, chỉ cần trình duyệt web)

## Cài đặt

### 1. Cài đặt FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
Tải từ [FFmpeg website](https://ffmpeg.org/download.html) và thêm vào PATH

### 2. Cài đặt Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Trên Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Frontend

Frontend không cần cài đặt, chỉ cần mở file `index.html` trong trình duyệt hoặc serve qua web server.

## Chạy ứng dụng

### 1. Khởi động Backend

```bash
cd backend
source venv/bin/activate  # Trên Windows: venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend sẽ chạy tại: http://localhost:8000

### 2. Mở Frontend

Có 2 cách:

**Cách 1: Mở trực tiếp file**
- Mở file `frontend/index.html` trong trình duyệt
- Lưu ý: Cần chỉnh sửa `API_BASE_URL` trong `app.js` nếu backend chạy ở port khác

**Cách 2: Serve qua web server (khuyến nghị)**

Sử dụng Python:
```bash
cd frontend
python -m http.server 8080
```

Hoặc Node.js:
```bash
cd frontend
npx http-server -p 8080
```

Sau đó mở: http://localhost:8080

## Sử dụng

1. Mở ứng dụng trong trình duyệt
2. Nhập URL video (có thể nhập nhiều URL, mỗi URL một dòng)
3. Chọn định dạng và chất lượng
4. Click "Bắt đầu tải"
5. Theo dõi tiến trình tải real-time
6. Click "Tải xuống" khi hoàn thành

## API Documentation

Khi backend đang chạy, truy cập:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Các endpoints chính:

- `POST /api/download` - Bắt đầu tải video
- `GET /api/info?url=...` - Lấy thông tin video
- `GET /api/status/{task_id}` - Kiểm tra trạng thái
- `GET /api/download/{task_id}` - Tải file đã hoàn thành
- `WebSocket /ws/{task_id}` - Stream tiến trình
- `DELETE /api/task/{task_id}` - Xóa task

## Lưu ý

- Files được lưu tạm trong thư mục `backend/downloads/`
- Cần có kết nối internet để tải video
- Một số video có thể có giới hạn về chất lượng tùy theo nguồn
- Facebook và TikTok có thể yêu cầu đăng nhập cho một số video

## Troubleshooting

### Lỗi "FFmpeg not found"
- Đảm bảo FFmpeg đã được cài đặt và có trong PATH
- Kiểm tra bằng lệnh: `ffmpeg -version`

### Lỗi CORS
- Backend đã cấu hình CORS cho phép tất cả origins
- Nếu vẫn lỗi, kiểm tra lại URL trong `app.js`

### Video không tải được
- Kiểm tra URL có hợp lệ không
- Một số video có thể bị giới hạn bởi nền tảng
- Xem logs của backend để biết chi tiết lỗi

## License

MIT License

## Đóng góp

Mọi đóng góp đều được chào đón! Vui lòng tạo issue hoặc pull request.

