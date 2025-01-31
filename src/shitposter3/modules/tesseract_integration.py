"""Tesseract OCR integration for text extraction from screenshots."""

import pytesseract
from PIL import Image
import logging
from typing import Dict, Optional, Any, List

_logger = logging.getLogger(__name__)

class ScreenOCR:
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('tesseract', {})
        self.lang = self.config.get('lang', 'eng')
        self.psm = self.config.get('psm', 11)
        self._last_screenshot_path = None
    
    def extract_text_from_file(self, image_path: str) -> Optional[str]:
        """Extract text from a specific image file."""
        try:
            image = Image.open(image_path)
            config = f'--psm {self.psm} -l {self.lang}'
            text = pytesseract.image_to_string(image, config=config)
            
            if text.strip():
                self._last_screenshot_path = image_path
                _logger.debug(f"Successfully extracted text from {image_path}")
                return text.strip()
            _logger.warning(f"No text found in image: {image_path}")
            return None
                
        except Exception as e:
            _logger.error(f"Failed to extract text from image: {e}")
            return None

    def get_last_screenshot_path(self) -> Optional[str]:
        """Get the path of the last processed screenshot."""
        return self._last_screenshot_path