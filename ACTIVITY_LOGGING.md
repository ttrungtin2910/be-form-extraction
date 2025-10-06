# 📊 User Activity Logging System

Hệ thống logging hoạt động người dùng để tracking và monitoring các tính năng trên web.

## 🚀 Tính năng chính

### Backend Features
- **Automatic Logging**: Tự động log tất cả API calls thông qua middleware
- **Manual Logging**: Hỗ trợ log thủ công cho các hoạt động đặc biệt
- **Filtering & Pagination**: Lọc và phân trang logs theo nhiều tiêu chí
- **Activity Summary**: Thống kê hoạt động theo user và thời gian
- **Cleanup**: Tự động dọn dẹp logs cũ

### Frontend Features
- **Activity Dashboard**: Giao diện xem logs với bộ lọc mạnh mẽ
- **Real-time Tracking**: Theo dõi hoạt động real-time
- **User-friendly Interface**: Giao diện thân thiện với người dùng

## 📋 Các loại Activity được track

| Activity Type | Mô tả | Ví dụ |
|---------------|-------|-------|
| `login` | Đăng nhập | User đăng nhập thành công |
| `logout` | Đăng xuất | User đăng xuất |
| `upload_image` | Upload ảnh | Upload file ảnh lên server |
| `view_image` | Xem ảnh | Xem chi tiết ảnh |
| `delete_image` | Xóa ảnh | Xóa ảnh khỏi hệ thống |
| `extract_data` | Trích xuất dữ liệu | Chạy AI extraction |
| `view_folder` | Xem thư mục | Xem danh sách ảnh trong folder |
| `create_folder` | Tạo thư mục | Tạo folder mới |
| `delete_folder` | Xóa thư mục | Xóa folder |
| `api_call` | API call | Các API calls khác |
| `error` | Lỗi | Các lỗi xảy ra trong hệ thống |

## 🔧 Cấu hình

### Backend Configuration

1. **Environment Variables** (`.env`):
```ini
# Activity Logging
ACTIVITY_LOG_COLLECTION=activity_logs
ACTIVITY_LOG_RETENTION_DAYS=90
```

2. **Firestore Collection**: `activity_logs`

### Frontend Configuration

1. **Activity Logger Provider** đã được tích hợp vào `App.jsx`
2. **API Endpoints** đã được thêm vào `api.js`

## 📡 API Endpoints

### 1. Get Activity Logs (Admin only)
```http
GET /activity-logs?user_id=xxx&username=xxx&activity_type=login&page=1&limit=50
```

**Query Parameters:**
- `user_id`: Filter theo user ID
- `username`: Filter theo username
- `activity_type`: Filter theo loại hoạt động
- `start_date`: Ngày bắt đầu (ISO format)
- `end_date`: Ngày kết thúc (ISO format)
- `page`: Trang (default: 1)
- `limit`: Số items per page (default: 50, max: 1000)

### 2. Get My Activity Logs
```http
GET /activity-logs/my-activity?page=1&limit=50
```

### 3. Get Activity Summary
```http
GET /activity-logs/summary?user_id=xxx&days=7
```

### 4. Cleanup Old Logs (Admin only)
```http
POST /activity-logs/cleanup
Content-Type: application/json

{
  "days_to_keep": 90
}
```

## 🎯 Sử dụng trong Frontend

### 1. Activity Logger Hook
```javascript
import { useActivityLogger } from '../components/ActivityLogger';

function MyComponent() {
  const { logPageView, logUserAction, logError } = useActivityLogger();

  useEffect(() => {
    logPageView('My Page');
  }, []);

  const handleClick = () => {
    logUserAction('button_click', { button: 'submit' });
  };

  const handleError = (error) => {
    logError(error, { context: 'form_submission' });
  };
}
```

### 2. Activity Logs Dashboard
Truy cập `/admin/activity-logs` để xem dashboard logs.

## 📊 Cấu trúc dữ liệu

### ActivityLog Model
```python
{
  "id": "uuid",
  "user_id": "user123",
  "username": "tin.trantrung",
  "activity_type": "login",
  "description": "User logged in successfully",
  "endpoint": "/auth/login",
  "method": "POST",
  "status_code": 200,
  "ip_address": "127.0.0.1",
  "user_agent": "Mozilla/5.0...",
  "metadata": {
    "request_id": "req123",
    "response_size": 1024,
    "query_params": {}
  },
  "timestamp": "2025-10-07T02:48:27.391Z",
  "duration_ms": 150.5
}
```

## 🔒 Bảo mật

- **Admin Only**: Một số endpoints chỉ admin mới truy cập được
- **User Isolation**: Users chỉ xem được logs của chính họ
- **Rate Limiting**: Tất cả endpoints đều có rate limiting
- **Data Sanitization**: Dữ liệu được sanitize trước khi lưu

## 🧹 Maintenance

### Cleanup Old Logs
```bash
# Cleanup logs older than 90 days
curl -X POST "http://localhost:8000/activity-logs/cleanup" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"days_to_keep": 90}'
```

### Monitor Log Size
```python
# Check collection size
from google.cloud import firestore
db = firestore.Client()
collection = db.collection('activity_logs')
docs = collection.stream()
count = sum(1 for _ in docs)
print(f"Total logs: {count}")
```

## 📈 Performance

- **Indexing**: Firestore indexes được tối ưu cho queries
- **Pagination**: Hỗ trợ pagination để tránh timeout
- **Async Processing**: Logging không block main request
- **Batch Operations**: Cleanup sử dụng batch operations

## 🐛 Troubleshooting

### Common Issues

1. **Logs không hiển thị**
   - Kiểm tra Firestore permissions
   - Kiểm tra collection name
   - Kiểm tra user authentication

2. **Performance chậm**
   - Tăng pagination limit
   - Thêm Firestore indexes
   - Cleanup logs cũ

3. **Memory issues**
   - Giảm batch size trong cleanup
   - Tăng cleanup frequency

## 🔄 Future Enhancements

- [ ] Real-time notifications
- [ ] Export logs to CSV/Excel
- [ ] Advanced analytics dashboard
- [ ] Alert system for suspicious activities
- [ ] Integration with external monitoring tools
