"""
Form extraction service for handling AI analysis and data storage.
"""
import logging
from typing import Dict, Any, Optional
from database.firestore import ImageData, upsert_image, get_image
from chain.completions import TicketChatBot
from properties.config import Configuration

logger = logging.getLogger(__name__)


class ExtractionService:
    """Service for handling form extraction operations."""
    
    def __init__(self, config: Configuration, bot: TicketChatBot):
        self.config = config
        self.bot = bot
        self.image_detail_collection = config.COLLECTION_NAME_IMAGE_DETAIL
        self.form_extract_collection = config.COLLECTION_NAME_FORM_EXTRACT
    
    async def extract_form_data(self, image_path: str) -> Dict[str, Any]:
        """
        Extract form data from image using AI analysis.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dict[str, Any]: Extracted form data
            
        Raises:
            Exception: If analysis fails
        """
        logger.info(f"Starting AI analysis for {image_path}")
        
        try:
            result = await self.bot.analyze_ticket(image_path, "")
            
            # Ensure result is a dictionary
            if not isinstance(result, dict):
                logger.error(f"Analysis result is not a dictionary: {type(result)}")
                result = {"error": "Invalid analysis result", "raw_result": str(result)}
            
            logger.info(f"AI analysis completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"AI analysis failed: {str(e)}")
            raise
    
    async def save_extraction_result(self, image_data: Dict[str, Any], analysis_result: Dict[str, Any]) -> None:
        """
        Save extraction results to Firestore.
        
        Args:
            image_data: Image metadata
            analysis_result: AI analysis results
        """
        try:
            # Save to form extraction collection
            form_data = {
                "Status": "Completed",
                "ImageName": image_data["ImageName"],
                "ImagePath": image_data["ImagePath"],
                "CreatedAt": image_data["CreatedAt"],
                "FolderPath": image_data["FolderPath"],
                "Size": image_data["Size"],
                "analysis_result": analysis_result,
            }
            
            upsert_image(form_data, self.form_extract_collection, image_data["ImageName"])
            logger.info(f"Saved form extraction result: {image_data['ImageName']}")
            
            # Update image status in image detail collection
            image_metadata = ImageData(
                Status="Completed",
                ImageName=image_data["ImageName"],
                ImagePath=image_data["ImagePath"],
                CreatedAt=image_data["CreatedAt"],
                FolderPath=image_data["FolderPath"],
                Size=image_data["Size"],
            )
            
            upsert_image(image_metadata, self.image_detail_collection, image_data["ImageName"])
            logger.info(f"Updated image status to Completed: {image_data['ImageName']}")
            
        except Exception as e:
            logger.error(f"Failed to save extraction results: {str(e)}")
            raise
    
    def get_image_size_fallback(self, image_name: str, provided_size: float) -> float:
        """
        Get image size with fallback to existing metadata.
        
        Args:
            image_name: Name of the image
            provided_size: Size provided in request
            
        Returns:
            float: Image size in MB
        """
        if provided_size > 0.0:
            return provided_size
        
        try:
            existing_meta = get_image(image_name, self.image_detail_collection) or {}
            return existing_meta.get("Size", 0.0)
        except Exception as e:
            logger.warning(f"Could not get fallback size for {image_name}: {e}")
            return 0.0
    
    def prepare_image_data(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare image data for processing.
        
        Args:
            request_data: Data from the request
            
        Returns:
            Dict[str, Any]: Prepared image data
        """
        # Use the size from the request data, fallback to existing metadata if needed
        size_val = self.get_image_size_fallback(request_data["ImageName"], request_data.get("Size", 0.0))
        
        return {
            "ImageName": request_data["ImageName"],
            "ImagePath": request_data["ImagePath"],
            "CreatedAt": request_data["CreatedAt"],
            "FolderPath": request_data["FolderPath"],
            "Size": size_val,
        }
