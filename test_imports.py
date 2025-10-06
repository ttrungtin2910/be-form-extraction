#!/usr/bin/env python3
"""
Test script to verify all imports and basic functionality work correctly.
"""


def test_imports():
    """Test all critical imports."""
    print("Testing imports...")

    try:
        # Test configuration
        from properties.config import Configuration

        config = Configuration()
        print("✅ Configuration import successful")

        # Test file validation
        from utils.file_validation import validate_upload_file, FileValidationError

        print("✅ File validation import successful")

        # Test services
        from services.form_extraction_service import FormExtractionService
        from services.image_processor import ImageProcessor
        from services.extraction_service import ExtractionService

        print("✅ Services import successful")

        # Test main app
        from main import app

        print("✅ Main app import successful")

        # Test Celery tasks
        from tasks import upload_image_task, extract_form_task

        print("✅ Celery tasks import successful")

        print("\n🎉 All imports successful! The application is ready to run.")
        return True

    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_configuration():
    """Test configuration validation."""
    print("\nTesting configuration...")

    try:
        from properties.config import Configuration

        config = Configuration()
        config.validate_required_config()
        print("✅ Configuration validation successful")

        # Test some config values
        print(f"  - Upload folder: {config.UPLOAD_FOLDER}")
        print(f"  - Bucket name: {config.BUCKET_NAME}")
        print(f"  - Allowed origins: {config.ALLOWED_ORIGINS}")
        print(f"  - Max file size: {config.MAX_FILE_SIZE} bytes")

        return True

    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Starting application tests...\n")

    success = True
    success &= test_imports()
    success &= test_configuration()

    if success:
        print(
            "\n✅ All tests passed! You can now run 'python main.py' to start the server."
        )
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
