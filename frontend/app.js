// API Base URL
const API_BASE_URL = 'http://localhost:8000';
const WS_BASE_URL = 'ws://localhost:8000';

// State management
const tasks = new Map();

// DOM Elements
const urlInput = document.getElementById('url-input');
const formatSelect = document.getElementById('format-select');
const qualitySelect = document.getElementById('quality-select');
const downloadBtn = document.getElementById('download-btn');
const tasksList = document.getElementById('tasks-list');
const emptyState = document.getElementById('empty-state');
const toastContainer = document.getElementById('toast-container');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    downloadBtn.addEventListener('click', handleDownload);
    updateEmptyState();
});

// Xử lý tải video
async function handleDownload() {
    const urls = urlInput.value.trim().split('\n').filter(url => url.trim());
    
    if (urls.length === 0) {
        showToast('Vui lòng nhập ít nhất một URL', 'error');
        return;
    }
    
    // Validate URLs
    const invalidUrls = urls.filter(url => !isValidUrl(url));
    if (invalidUrls.length > 0) {
        showToast('Một số URL không hợp lệ', 'error');
        return;
    }
    
    // Disable button
    downloadBtn.disabled = true;
    downloadBtn.querySelector('.btn-text').textContent = 'Đang xử lý...';
    downloadBtn.querySelector('.btn-loader').style.display = 'inline';
    
    try {
        // Tải từng URL
        for (const url of urls) {
            await startDownload(url.trim());
        }
        
        // Clear input
        urlInput.value = '';
        showToast(`Đã thêm ${urls.length} video vào danh sách tải`, 'success');
    } catch (error) {
        console.error('Lỗi tải video:', error);
        showToast('Có lỗi xảy ra khi bắt đầu tải', 'error');
    } finally {
        // Enable button
        downloadBtn.disabled = false;
        downloadBtn.querySelector('.btn-text').textContent = 'Bắt đầu tải';
        downloadBtn.querySelector('.btn-loader').style.display = 'none';
    }
}

// Bắt đầu tải một video
async function startDownload(url) {
    try {
        const format = formatSelect.value;
        const audioOnly = format === 'mp3' || format === 'm4a';
        
        const response = await fetch(`${API_BASE_URL}/api/download`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: url,
                output_format: format,
                audio_only: audioOnly,
            }),
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Lỗi không xác định');
        }
        
        const data = await response.json();
        const taskId = data.task_id;
        
        // Tạo task item
        createTaskItem(taskId, data.video_info?.title || url, url);
        
        // Kết nối WebSocket để nhận progress
        connectWebSocket(taskId);
        
    } catch (error) {
        console.error('Lỗi bắt đầu tải:', error);
        showToast(`Lỗi: ${error.message}`, 'error');
    }
}

// Tạo task item trong UI
function createTaskItem(taskId, title, url) {
    const taskItem = document.createElement('div');
    taskItem.className = 'task-item';
    taskItem.id = `task-${taskId}`;
    
    taskItem.innerHTML = `
        <div class="task-header">
            <div class="task-title" title="${title}">${title}</div>
            <div class="task-status pending" id="status-${taskId}">Đang chờ</div>
        </div>
        <div class="progress-container">
            <div class="progress-bar">
                <div class="progress-fill" id="progress-${taskId}" style="width: 0%"></div>
            </div>
            <div class="progress-text">
                <span id="progress-text-${taskId}">0%</span>
                <span id="message-${taskId}">Đang khởi tạo...</span>
            </div>
        </div>
        <div class="task-actions" id="actions-${taskId}">
            <button class="btn-secondary btn-danger" onclick="deleteTask('${taskId}')">Xóa</button>
        </div>
    `;
    
    tasksList.appendChild(taskItem);
    tasks.set(taskId, { status: 'pending', progress: 0 });
    updateEmptyState();
}

// Kết nối WebSocket để nhận progress
function connectWebSocket(taskId) {
    const ws = new WebSocket(`${WS_BASE_URL}/ws/${taskId}`);
    
    ws.onopen = () => {
        console.log(`WebSocket connected for task ${taskId}`);
    };
    
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            updateTaskStatus(taskId, data);
        } catch (error) {
            console.error('Lỗi parse WebSocket message:', error);
        }
    };
    
    ws.onerror = (error) => {
        console.error(`WebSocket error for task ${taskId}:`, error);
    };
    
    ws.onclose = () => {
        console.log(`WebSocket closed for task ${taskId}`);
        // Thử kết nối lại nếu task chưa hoàn thành
        const task = tasks.get(taskId);
        if (task && !['completed', 'failed'].includes(task.status)) {
            setTimeout(() => {
                checkTaskStatus(taskId);
            }, 2000);
        }
    };
}

// Cập nhật trạng thái task
function updateTaskStatus(taskId, data) {
    const taskItem = document.getElementById(`task-${taskId}`);
    if (!taskItem) return;
    
    const statusEl = document.getElementById(`status-${taskId}`);
    const progressEl = document.getElementById(`progress-${taskId}`);
    const progressTextEl = document.getElementById(`progress-text-${taskId}`);
    const messageEl = document.getElementById(`message-${taskId}`);
    const actionsEl = document.getElementById(`actions-${taskId}`);
    
    // Cập nhật status
    statusEl.className = `task-status ${data.status}`;
    statusEl.textContent = getStatusText(data.status);
    
    // Cập nhật progress
    const progress = data.progress || 0;
    progressEl.style.width = `${progress}%`;
    progressTextEl.textContent = `${Math.round(progress)}%`;
    
    // Cập nhật message
    if (data.message) {
        messageEl.textContent = data.message;
    }
    
    // Cập nhật actions
    if (data.status === 'completed') {
        actionsEl.innerHTML = `
            <a href="${API_BASE_URL}/api/download/${taskId}" class="btn-secondary btn-success" download>
                ⬇️ Tải xuống
            </a>
            <button class="btn-secondary btn-danger" onclick="deleteTask('${taskId}')">Xóa</button>
        `;
        showToast('Tải video thành công!', 'success');
    } else if (data.status === 'failed') {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'task-error';
        errorDiv.textContent = `Lỗi: ${data.error || 'Không xác định'}`;
        taskItem.appendChild(errorDiv);
        showToast('Tải video thất bại', 'error');
    }
    
    // Lưu state
    tasks.set(taskId, {
        status: data.status,
        progress: progress,
        file_path: data.file_path,
        file_name: data.file_name,
    });
}

// Kiểm tra trạng thái task (fallback nếu WebSocket fail)
async function checkTaskStatus(taskId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/status/${taskId}`);
        if (response.ok) {
            const data = await response.json();
            updateTaskStatus(taskId, data);
            
            // Nếu chưa hoàn thành, tiếp tục kiểm tra
            if (!['completed', 'failed'].includes(data.status)) {
                setTimeout(() => checkTaskStatus(taskId), 2000);
            }
        }
    } catch (error) {
        console.error('Lỗi kiểm tra status:', error);
    }
}

// Xóa task
async function deleteTask(taskId) {
    if (!confirm('Bạn có chắc muốn xóa task này?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/task/${taskId}`, {
            method: 'DELETE',
        });
        
        if (response.ok) {
            const taskItem = document.getElementById(`task-${taskId}`);
            if (taskItem) {
                taskItem.remove();
            }
            tasks.delete(taskId);
            updateEmptyState();
            showToast('Đã xóa task', 'success');
        }
    } catch (error) {
        console.error('Lỗi xóa task:', error);
        showToast('Lỗi khi xóa task', 'error');
    }
}

// Cập nhật empty state
function updateEmptyState() {
    if (tasks.size === 0) {
        emptyState.style.display = 'block';
        tasksList.style.display = 'none';
    } else {
        emptyState.style.display = 'none';
        tasksList.style.display = 'block';
    }
}

// Hiển thị toast notification
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    toastContainer.appendChild(toast);
    
    // Auto remove sau 3 giây
    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3000);
}

// Validate URL
function isValidUrl(string) {
    try {
        const url = new URL(string);
        return url.protocol === 'http:' || url.protocol === 'https:';
    } catch (_) {
        return false;
    }
}

// Lấy text cho status
function getStatusText(status) {
    const statusMap = {
        'pending': 'Đang chờ',
        'downloading': 'Đang tải',
        'processing': 'Đang xử lý',
        'completed': 'Hoàn thành',
        'failed': 'Thất bại',
    };
    return statusMap[status] || status;
}

// Export functions for onclick handlers
window.deleteTask = deleteTask;

