# Form Extraction API

A FastAPI application for extracting information from forms using Google Document AI and storing results in Google Cloud Firestore.

## 🚀 Features


## 🛠️ Technologies Used


## 📋 System Requirements


## 🔧 Installation

### 1. Clone repository

```bash
git clone <repository-url>
cd be-form-extraction
```

### 2. Install dependencies

```bash
conda create -n be-form-extraction python=3.12
conda activate be-form-extraction
```

```bash
pip install -r requirements.txt
```

### 3. Environment configuration

Create a `.env` file in the root directory:

```env
# OpenAI Configuration
OPENAI_KEY=your_openai_api_key
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TEMPERATURE=0.7

# Google Cloud Configuration
PROJECT_ID=your_google_cloud_project_id
LOCATION=us
PROCESSOR_ID=your_document_ai_processor_id
PROCESSOR_VERSION_ID=your_processor_version_id
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json

# Queue / Redis
# Optional: change if not using default localhost
REDIS_URL=redis://localhost:6379/0
```

### 4. Google Cloud Setup

1. Create a service account and download JSON credentials
2. Place credentials file in `database/` or `properties/` directory
3. Configure Document AI processor
4. Create a bucket in Google Cloud Storage

## 🚀 Running the Application

### 0. Start Redis

```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

### 1. Start API (development)

```bash
uvicorn main:app --reload --port 8000
```

### 2. Start Celery worker

Python 3.13 có thể gặp lỗi với pool mặc định. Dùng script tự động chọn pool:

```bash
python scripts/run_worker.py
```

Ép luôn solo:
```bash
# PowerShell
$env:CELERY_FORCE_SOLO=1
python scripts/run_worker.py
```

Dùng lại prefork (khuyến nghị khi ở Python 3.12):
```bash
$env:CELERY_FORCE_SOLO=0
$env:CELERY_POOL=prefork
python scripts/run_worker.py

#### 🔧 Tăng concurrency để thấy nhiều task chạy đồng thời

Mặc định Python 3.13 sẽ bị ép sang solo (1 task một lúc). Để Flower hiển thị nhiều task cùng Processing:

1. (Khuyến nghị) Dùng Python 3.12 và prefork:
```powershell
$env:CELERY_FORCE_SOLO=0
$env:CELERY_POOL='prefork'
$env:CELERY_CONCURRENCY=6   # số tiến trình worker muốn
python scripts/run_worker.py
```

2. Nếu vẫn ở Python 3.13 nhưng muốn thử prefork (có thể lỗi tùy phiên bản Celery/billiard):
```powershell
$env:CELERY_FORCE_SOLO=0
$env:CELERY_POOL='prefork'
$env:CELERY_CONCURRENCY=4
python scripts/run_worker.py
```

3. Hoặc chạy nhiều worker solo song song (mỗi terminal một process):
```powershell
# Terminal 1
python scripts/run_worker.py
# Terminal 2
python scripts/run_worker.py
# ... mỗi process xử lý 1 task, tổng số task chạy đồng thời = số process
```

4. I/O-bound (gọi API) có thể thử eventlet/gevent (không bắt buộc):
```powershell
pip install eventlet
$env:CELERY_POOL='eventlet'
$env:CELERY_CONCURRENCY=50
python scripts/run_worker.py
```
Lưu ý: Kiểm soát rate limit OpenAI / Google API, tránh vượt quota.

Nếu thấy chỉ 1 task Active trong Flower: kiểm tra pool (solo) hoặc concurrency chưa đặt >1.
```

### 3. (Optional) Start Flower dashboard

```bash
celery -A celery_app.celery_app flower --port=5555
```

Application: `http://localhost:8000`  | Flower: `http://localhost:5555`

> Bạn vẫn có thể dùng các endpoint đồng bộ cũ (`/upload-image/`, `/ExtractForm`), nhưng nên chuyển sang **queue endpoints** để tránh nghẽn khi xử lý nhiều ảnh.

## ⚙️ Async Queue Endpoints

| Purpose | Sync Endpoint | Queue Endpoint | Notes |
|---------|---------------|----------------|-------|
| Upload image | `POST /upload-image/` | `POST /queue/upload-image` | Queue trả về `task_id` |
| Extract form | `POST /ExtractForm` | `POST /queue/extract-form` | Phải có metadata ảnh trước |
| Task status  | N/A | `GET /tasks/{task_id}` | Poll tới khi `state=SUCCESS` |

### Upload (Queued)
```bash
curl -X POST http://localhost:8000/queue/upload-image \
  -F "file=@sample.jpg" \
  -F "status=Uploaded" \
  -F "folderPath=2025/aug"
```
Response:
```json
{"task_id": "<uuid>", "status": "queued"}
```

### Extract (Queued)
```bash
curl -X POST http://localhost:8000/queue/extract-form \
  -H "Content-Type: application/json" \
  -d '{
    "ImageName": "20250810_101112_123456.jpg",
    "ImagePath": "https://storage.googleapis.com/display-form-extract/2025/aug/20250810_101112_123456.jpg",
    "Status": "Uploaded",
    "CreatedAt": "20250810_101112_123456",
    "FolderPath": "2025/aug",
    "Size": 1.25
  }'
```
Response:
```json
{"task_id": "<uuid>", "status": "queued"}
```

### Poll Task
```bash
curl http://localhost:8000/tasks/<uuid>
```
Possible states: `PENDING`, `STARTED`, `SUCCESS`, `FAILURE`, `RETRY`.

On success:
```json
{
  "task_id": "<uuid>",
  "state": "SUCCESS",
  "result": {"image_name": "...", "analysis_result": {"...": "..."}}
}
```

Front-end đã được cập nhật để tự động poll khi gọi analyze hoặc bulk analyze, không cần thay đổi thêm.

## 📚 API Endpoints (Summary)

### 1. Upload Image (Sync)

**POST** `/upload-image/`

Upload form image to Google Cloud Storage and save metadata to Firestore.

```bash
curl -X POST "http://localhost:8000/upload-image/" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@form_image.jpg" \
  -F "status=pending"
```

### 2. Extract Form (Sync)

**POST** `/ExtractForm`

Extract information from form image using Google Document AI.

```bash
curl -X POST "http://localhost:8000/ExtractForm" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "form_20241201_001",
    "size": "1024x768",
    "image": "https://storage.googleapis.com/bucket/image.jpg",
    "status": "processing",
    "createAt": "2024-12-01T10:00:00Z"
  }'
```

### 3. Get Extraction Information

**POST** `/GetFormExtractInformation`

Retrieve extracted information from Firestore.

```bash
curl -X POST "http://localhost:8000/GetFormExtractInformation" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "title=form_20241201_001"
```

### 4. Image Management

### 5. Queue Variants (Async)
See "Async Queue Endpoints" section above.


## 📁 Project Structure

```
be-form-extraction/
├── chain/                    # AI processing logic
│   ├── completions.py       # OpenAI integration
│   └── doc_ai.py           # Google Document AI client
├── database/                # Database operations
│   ├── firestore.py        # Firestore operations
│   └── ggc_storage.py      # Google Cloud Storage operations
├── properties/              # Configuration
│   ├── config.py           # Environment configuration
│   └── prompts.py          # AI prompts
├── utils/                   # Utility functions
│   ├── common.py           # Common utilities
│   ├── constant.py         # Constants
│   ├── document_ai_helpers.py  # Document AI helpers
│   └── file_processing.py  # File processing utilities
├── temp_uploads/           # Temporary file storage
├── main.py                 # FastAPI application & queue endpoints
├── celery_app.py           # Celery factory (Redis broker/backend)
├── tasks.py                # Celery tasks (upload + extract)
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## 🔒 Security


## 🧪 Testing

### Test API endpoints

```bash
# Test health check
curl http://localhost:8000/

# Test upload endpoint
curl -X POST "http://localhost:8000/upload-image/" \
  -F "file=@test_image.jpg" \
  -F "status=test"
```

## 📝 Logs

The application uses Python logging with INFO level. Logs are written to console and can be configured to write to files.

## 🚀 Deployment

### Google Cloud Run

```bash
# Build Docker image
docker build -t form-extraction-api .

# Deploy to Cloud Run
gcloud run deploy form-extraction-api \
  --image gcr.io/PROJECT_ID/form-extraction-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Docker

```bash
# Build image
docker build -t form-extraction-api .

# Run container
docker run -p 8000:8000 form-extraction-api
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is distributed under the MIT License. See the `LICENSE` file for more details.

## 📞 Support

If you encounter any issues or have questions, please create an issue in the repository or contact the development team.

## � Redis Monitoring (RedisInsight)

Bạn có thể dùng RedisInsight để quan sát queue Celery (keys, performance) song song với Flower.

### Cách 1: Docker nhanh (khuyến nghị)

```powershell
docker run -d --name redisinsight -p 5540:5540 redis/redisinsight:latest
```

Mở: http://localhost:5540

Add database:
```
Host: host.docker.internal   (hoặc 127.0.0.1 nếu Docker Desktop cho phép)
Port: 6379
Password: (để trống nếu Redis chưa đặt mật khẩu)
```

Persist dữ liệu (giữ cấu hình sau khi xoá container):
```powershell
docker run -d --name redisinsight -p 5540:5540 -v redisinsight-data:/data redis/redisinsight:latest
```

### Cách 2: Docker Compose (Redis + RedisInsight)

Tạo `docker-compose.yml` (nếu chưa có):
```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  redisinsight:
    image: redis/redisinsight:latest
    ports:
      - "5540:5540"
    depends_on:
      - redis
    volumes:
      - redisinsight-data:/data
volumes:
  redisinsight-data:
```

Chạy:
```powershell
docker compose up -d
```

### Cách 3: Cài native app
Tải bản Windows từ: https://redis.io/insight/ → Install → Add database như trên.

### Xem dữ liệu Celery
  - `celery-task-meta-<task_id>`: trạng thái & kết quả task
  - `unacked`, `celery`, v.v. (tùy broker config)

### So sánh nhanh
| Tool | Mục đích chính | Ưu điểm | Nhược |
|------|----------------|---------|-------|
| Flower | Giám sát task (state, runtime) | UI chuyên cho Celery | Không xem raw key | 
| RedisInsight | Quan sát Redis cấp thấp | Xem key, TTL, perf, search | Không chuyên biệt Celery |

Kết hợp cả hai giúp vừa thấy tiến trình task (Flower) vừa xem nội dung lưu trong Redis (RedisInsight).

### Dọn dẹp
```powershell
docker rm -f redisinsight
docker volume rm redisinsight-data   # nếu muốn xoá luôn dữ liệu
```

### Troubleshooting
| Vấn đề | Cách xử lý |
|--------|------------|
| Không connect được bằng 127.0.0.1 | Dùng `host.docker.internal` |
| Không thấy key celery-task-meta-* | Task chưa chạy xong hoặc dùng DB index khác |
| Chỉ 1 task chạy một lúc | Kiểm tra pool (solo) & biến `CELERY_CONCURRENCY` |
| Timeout khi connect | Đảm bảo container Redis đang chạy (docker ps) |

Muốn bảo mật production: bật password trong Redis (requirepass) rồi cấu hình trong REDIS_URL (`redis://:password@host:6379/0`).

## �🔄 Changelog

### Version 1.0.0
