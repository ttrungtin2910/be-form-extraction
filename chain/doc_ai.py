from google.api_core.client_options import ClientOptions
from google.cloud import documentai

from pathlib import Path
from typing import Optional

from properties.config import Configuration
from utils.document_ai_helpers import post_process


class DocumentAIClient:
    def __init__(self, config: Configuration):
        # Validate required configuration values
        if not config.PROJECT_ID:
            raise ValueError("PROJECT_ID is required")
        if not config.LOCATION:
            raise ValueError("LOCATION is required")
        if not config.PROCESSOR_ID:
            raise ValueError("PROCESSOR_ID is required")
            
        self.project_id = config.PROJECT_ID
        self.location = config.LOCATION
        self.processor_id = config.PROCESSOR_ID
        self.processor_version_id = config.PROCESSOR_VERSION_ID

        # Create client
        client_options = ClientOptions(
            api_endpoint=f"{self.location}-documentai.googleapis.com"
        )
        self.client = documentai.DocumentProcessorServiceClient(client_options=client_options)

        # Build full resource name for the processor or processor version
        if self.processor_version_id:
            self.name_processor = self.client.processor_version_path(
                self.project_id, self.location, self.processor_id, self.processor_version_id
            )
        else:
            self.name_processor = self.client.processor_path(
                self.project_id, self.location, self.processor_id
            )

    def extract_document(
        self,
        file_path: Path,
        field_mask: Optional[str] = None,
        pages: Optional["list[int]"] = [1]
    ) -> dict:
        """
        Process a PDF using Google Document AI.

        :param file_path: Path to the PDF file
        :param field_mask: Optional field mask
        :param pages: Pages to process (default: [1])
        :return: Parsed Document object
        """

        # Read file contents
        with open(file_path, "rb") as f:
            image_content = f.read()

        mime_type = self.get_mime_type(file_path)

        raw_document = documentai.RawDocument(
            content=image_content,
            mime_type=mime_type
        )

        # Optionally process specific pages
        process_options = documentai.ProcessOptions(
            individual_page_selector=documentai.ProcessOptions.IndividualPageSelector(
                pages=pages
            )
        )

        request = documentai.ProcessRequest(
            name=self.name_processor,
            raw_document=raw_document,
            field_mask=field_mask,
            process_options=process_options
        )
        
        # Get result
        result = self.client.process_document(request=request)
        
        # Post processing
        post_result = post_process(result.document)
        
        return post_result
    
    @staticmethod
    def get_mime_type(file_path: Path) -> str:
        ext = file_path.suffix.lower()
        if ext == ".jpg" or ext == ".jpeg":
            return "image/jpeg"
        elif ext == ".png":
            return "image/png"
        elif ext == ".pdf":
            return "application/pdf"
        else:
            raise ValueError(f"Unsupported file type: {file_path}")