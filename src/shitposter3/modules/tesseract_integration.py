"""OCR integration module using Tesseract for screen text recognition."""

import logging
import pytesseract
import mss
import numpy as np
import cv2
import subprocess
import tempfile

_logger = logging.getLogger(__name__)

class ScreenOCR:
    def __init__(self):
        self.sct = mss.mss()
        
    def capture_screen(self, monitor_number=1):
        """Capture screen content from specified monitor."""
        try:
            monitor = self.sct.monitors[monitor_number]
            screenshot = self.sct.grab(monitor)
            img = np.array(screenshot)
            return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        except Exception as e:
            _logger.error(f"Failed to capture screen: {e}")
            return None

    def process_image(self, image):
        """Process image for better OCR results."""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Apply thresholding to preprocess the image
        threshold = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        return threshold

    def extract_text(self, image=None, lang='eng'):
        """Extract text from image using Tesseract OCR via subprocess."""
        try:
            if image is None:
                image = self.capture_screen()
            
            if image is None:
                return None
                
            processed_image = self.process_image(image)
            with tempfile.NamedTemporaryFile(suffix='.png') as tmp:
                cv2.imwrite(tmp.name, processed_image)
                result = subprocess.run(
                    ['tesseract', tmp.name, 'stdout', '-l', lang],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if result.returncode == 0:
                    return result.stdout.strip()
                else:
                    _logger.error(f"Tesseract OCR failed: {result.stderr}")
                    return None
        except Exception as e:
            _logger.error(f"OCR extraction failed: {e}")
            return None

    def extract_text_with_positions(self, image=None, lang='eng'):
        """Extract text with position data using Tesseract OCR."""
        try:
            if image is None:
                image = self.capture_screen()
            
            if image is None:
                return None
                
            processed_image = self.process_image(image)
            data = pytesseract.image_to_data(processed_image, lang=lang, output_type=pytesseract.Output.DICT)
            
            results = []
            for i in range(len(data['text'])):
                if data['text'][i].strip():
                    results.append({
                        'text': data['text'][i],
                        'conf': data['conf'][i],
                        'bbox': (
                            data['left'][i],
                            data['top'][i],
                            data['width'][i],
                            data['height'][i]
                        )
                    })
            return results
        except Exception as e:
            _logger.error(f"OCR extraction with positions failed: {e}")
            return None