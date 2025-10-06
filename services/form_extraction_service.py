"""
Main form extraction service that orchestrates the entire process.
"""
import logging
from typing import Dict, Any
from fastapi import HTTPException
from .image_processor import ImageProcessor
from .extraction_service import ExtractionService
from properties.config import Configuration
from chain.completions import TicketChatBot

logger = logging.getLogger(__name__)


class FormExtractionService:
    """Main service for orchestrating form extraction process."""
    
    def __init__(self, config: Configuration):
        self.config = config
        self.image_processor = ImageProcessor(config)
        self.extraction_service = ExtractionService(config, TicketChatBot(config))
    
    async def process_form_extraction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main orchestration method for form extraction.
        
        Args:
            data: Form extraction request data
            
        Returns:
            Dict[str, Any]: Processing result with analysis data
            
        Raises:
            HTTPException: If processing fails
        """
        logger.info(f"Starting form extraction for {data['ImageName']}")
        
        local_path = None
        try:
            # Prepare image data
            image_data = self.extraction_service.prepare_image_data(data)
            
            # Download image
            local_path = await self.image_processor.download_image(
                data["ImagePath"], 
                data["ImageName"]
            )
            
            # Validate downloaded file
            self.image_processor.validate_and_cleanup_file(local_path)
            
            # Extract information using AI
            analysis_result = await self.extraction_service.extract_form_data(local_path)
            
            # Save results
            await self.extraction_service.save_extraction_result(image_data, analysis_result)
            
            logger.info(f"Form extraction completed successfully for {data['ImageName']}")
            
            return {
                "message": "Image processed successfully",
                "analysis_result": analysis_result,
                "received": data,
            }
            
        except Exception as e:
            logger.error(f"Form extraction failed for {data['ImageName']}: {str(e)}")
            
            # Cleanup temporary file on error
            if local_path:
                self.image_processor.cleanup_temp_file(local_path)
            
            # Convert to HTTPException for proper error handling
            if isinstance(e, HTTPException):
                raise
            else:
                raise HTTPException(status_code=500, detail=str(e))
        
        finally:
            # Always cleanup temporary file
            if local_path:
                self.image_processor.cleanup_temp_file(local_path)
    
    async def process_upload_and_extract(self, file_data: Dict[str, Any], folder_path: str = "") -> Dict[str, Any]:
        """
        Process file upload and immediate extraction.
        
        Args:
            file_data: Uploaded file data
            folder_path: Optional folder path
            
        Returns:
            Dict[str, Any]: Processing result
        """
        logger.info(f"Processing upload and extraction for {file_data.get('filename', 'unknown')}")
        
        try:
            # This method could be extended to handle direct upload processing
            # For now, it's a placeholder for future functionality
            raise NotImplementedError("Direct upload and extract not yet implemented")
            
        except Exception as e:
            logger.error(f"Upload and extract failed: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
