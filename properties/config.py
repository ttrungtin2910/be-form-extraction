import os
from dotenv import load_dotenv

load_dotenv()


class Configuration:
    """Configuration class for managing environment variables and application settings."""

    # OpenAI Configuration
    OPENAI_KEY = os.getenv("OPENAI_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))

    # Google Cloud Configuration
    PROJECT_ID = os.getenv("PROJECT_ID")
    LOCATION = os.getenv("LOCATION", "us")
    PROCESSOR_ID = os.getenv("PROCESSOR_ID")
    PROCESSOR_VERSION_ID = os.getenv("PROCESSOR_VERSION_ID")
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    FIRESTORE_DATABASE = os.getenv("FIRESTORE_DATABASE", "imageinformation")

    # Application Configuration
    BUCKET_NAME = os.getenv("BUCKET_NAME", "display-form-extract")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "temp_uploads")

    # Security Configuration
    ALLOWED_ORIGINS = os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:3000,https://localhost:3000"
    ).split(",")
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB default
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    API_SECRET_KEY = os.getenv("API_SECRET_KEY")

    # Redis/Celery Configuration
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_TIMEZONE = os.getenv("CELERY_TIMEZONE", "UTC")
    CELERY_WORKER_CONCURRENCY = int(os.getenv("CELERY_WORKER_CONCURRENCY", "2"))

    # Collection Names
    COLLECTION_NAME_IMAGE_DETAIL = "imagedetail"
    COLLECTION_NAME_FORM_EXTRACT = "forminformation"

    @classmethod
    def validate_required_config(cls):
        """Validate that all required configuration values are present."""
        required_vars = [
            ("OPENAI_KEY", cls.OPENAI_KEY),
            ("PROJECT_ID", cls.PROJECT_ID),
            ("PROCESSOR_ID", cls.PROCESSOR_ID),
            ("PROCESSOR_VERSION_ID", cls.PROCESSOR_VERSION_ID),
            ("GOOGLE_APPLICATION_CREDENTIALS", cls.GOOGLE_APPLICATION_CREDENTIALS),
        ]

        missing_vars = [
            var_name for var_name, var_value in required_vars if not var_value
        ]

        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

        # Validate credentials file exists
        if cls.GOOGLE_APPLICATION_CREDENTIALS and not os.path.exists(
            cls.GOOGLE_APPLICATION_CREDENTIALS
        ):
            raise ValueError(
                f"Credentials file not found: {cls.GOOGLE_APPLICATION_CREDENTIALS}"
            )

        return True
