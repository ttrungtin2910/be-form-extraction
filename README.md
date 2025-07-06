# Form Extraction API

A FastAPI application for extracting information from forms using Google Document AI and storing results in Google Cloud Firestore.

## 🚀 Features

- **Image Upload**: Upload form images to Google Cloud Storage
- **Data Extraction**: Use Google Document AI to extract information from forms
- **Data Storage**: Store metadata and extraction results in Firestore
- **RESTful API**: Provide endpoints for managing images and form data

## 🛠️ Technologies Used

- **FastAPI**: Modern web framework for Python
- **Google Document AI**: Document information extraction
- **Google Cloud Firestore**: NoSQL database
- **Google Cloud Storage**: File storage
- **OpenAI**: Natural language processing (if needed)

## 📋 System Requirements

- Python 3.8+
- Google Cloud Platform account
- Configured Google Document AI processor

## 🔧 Installation

### 1. Clone repository

```bash
git clone <repository-url>
cd be-form-extraction
```

### 2. Install dependencies

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
```

### 4. Google Cloud Setup

1. Create a service account and download JSON credentials
2. Place credentials file in `database/` or `properties/` directory
3. Configure Document AI processor
4. Create a bucket in Google Cloud Storage

## 🚀 Running the Application

### Development environment

```bash
python main.py
```

The application will run at `http://localhost:8000`

### Using uvicorn

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 📚 API Endpoints

### 1. Upload Image

**POST** `/upload-image/`

Upload form image to Google Cloud Storage and save metadata to Firestore.

```bash
curl -X POST "http://localhost:8000/upload-image/" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@form_image.jpg" \
  -F "status=pending"
```

### 2. Extract Form

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

- **GET** `/images/` - Get all images list
- **GET** `/images/{image_name}` - Get specific image information
- **POST** `/images/` - Create or update image information
- **DELETE** `/images/{image_name}` - Delete image

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
├── main.py                 # FastAPI application
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## 🔒 Security

- **Credentials**: Do not commit Google Cloud credentials files to repository
- **Environment variables**: Use `.env` file to store sensitive information
- **CORS**: Configure CORS appropriately for production

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

## 🔄 Changelog

### Version 1.0.0
- Initial release
- Basic form extraction functionality
- Google Cloud integration
- FastAPI REST API 