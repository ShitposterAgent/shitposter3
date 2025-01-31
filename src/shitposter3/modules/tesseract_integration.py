"""Tesseract integration for text extraction from screenshots."""

import subprocess
import logging
from typing import Dict, Optional, Any, List
import os
from pathlib import Path

_logger = logging.getLogger(__name__)

class ScreenOCR:
    def __init__(self, config: Dict[str, Any]):
        """Initialize OCR with configuration."""
        self.config = config.get('tesseract', {})
        self.lang = self.config.get('lang', 'eng')
        self.psm = self.config.get('psm', 11)
        self._last_screenshot_path = None
        self.temp_output_dir = os.path.expanduser("~/shitposter_data/tesseract")
        Path(self.temp_output_dir).mkdir(parents=True, exist_ok=True)
    
    def extract_text_from_file(self, image_path: str) -> Optional[str]:
        """Extract text from a specific image file using tesseract subprocess."""
        try:
            if not os.path.exists(image_path):
                _logger.error(f"Image file not found: {image_path}")
                return None

            output_file = os.path.join(self.temp_output_dir, "output.txt")
            
            # Run tesseract subprocess
            cmd = [
                'tesseract',
                image_path,
                os.path.join(self.temp_output_dir, "output"),  # Output file prefix
                f'-l', self.lang,
                f'--psm', str(self.psm)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                _logger.error(f"Tesseract failed: {result.stderr}")
                return None
                
            # Read the output file
            try:
                with open(output_file, 'r') as f:
                    text = f.read().strip()
            except Exception as e:
                _logger.error(f"Failed to read tesseract output: {e}")
                return None
            finally:
                # Clean up temporary file
                try:
                    os.remove(output_file)
                except Exception as e:
                    _logger.warning(f"Failed to remove temporary file: {e}")
            
            if text:
                self._last_screenshot_path = image_path
                _logger.debug(f"Successfully extracted text from {image_path}")
                return text
            
            _logger.warning(f"No text found in image: {image_path}")
            return None
                
        except Exception as e:
            _logger.error(f"Failed to extract text from image: {e}")
            return None

    def get_last_screenshot_path(self) -> Optional[str]:
        """Get the path of the last processed screenshot."""
        return self._last_screenshot_path