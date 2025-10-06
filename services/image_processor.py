"""
Image processing service for handling file operations.
"""
import os
import logging
from typing import Optional
from utils.file_processing import download_image_from_url
from utils.file_validation import validate_upload_file, FileValidationError
from properties.config import Configuration

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Service for handling image processing operations."""
    
    def __init__(self, config: Configuration):
        self.config = config
        self.upload_folder = config.UPLOAD_FOLDER
        
        # Ensure upload directory exists
        os.makedirs(self.upload_folder, exist_ok=True)
    
    async def download_image(self, image_url: str, filename: str) -> str:
        """
        Download image from URL to local storage.
        
        Args:
            image_url: URL of the image to download
            filename: Local filename to save as
            
        Returns:
            str: Path to the downloaded file
            
        Raises:
            Exception: If download fails
        """
        local_path = os.path.join(self.upload_folder, filename)
        logger.info(f"Downloading image from {image_url} to {local_path}")
        
        try:
            await download_image_from_url(image_url, local_path)
            logger.info(f"Download successful: {filename}")
            return local_path
        except Exception as e:
            logger.error(f"Download failed for {filename}: {str(e)}")
            raise
    
    def validate_and_cleanup_file(self, file_path: str) -> bool:
        """
        Validate uploaded file and cleanup on error.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            bool: True if validation passes
            
        Raises:
            FileValidationError: If validation fails
        """
        try:
            validate_upload_file(
                file_path,
                self.config.MAX_FILE_SIZE,
                self.config.ALLOWED_EXTENSIONS
            )
            logger.info(f"File validation successful: {file_path}")
            return True
        except FileValidationError as e:
            logger.error(f"File validation failed: {str(e)}")
            self.cleanup_temp_file(file_path)
            raise
        except Exception as e:
            logger.error(f"Unexpected validation error: {str(e)}")
            self.cleanup_temp_file(file_path)
            raise FileValidationError(f"Validation error: {str(e)}")
    
    def cleanup_temp_file(self, file_path: str) -> None:
        """
        Safely remove temporary file.
        
        Args:
            file_path: Path to the file to remove
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up temporary file: {file_path}")
        except OSError as e:
            logger.warning(f"Could not remove temporary file {file_path}: {e}")
    
    def get_file_size_mb(self, file_path: str) -> float:
        """
        Get file size in megabytes.
        
        Args:
            file_path: Path to the file
            
        Returns:
            float: File size in MB
        """
        try:
            size_bytes = os.path.getsize(file_path)
            return round(size_bytes / (1024 * 1024), 2)
        except OSError as e:
            logger.warning(f"Could not get file size for {file_path}: {e}")
            return 0.0
