"""OCR integration module using Tesseract for screen text recognition."""

import logging
import mss
import numpy as np
import cv2
import subprocess
import tempfile
import json

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
            with tempfile.NamedTemporaryFile(suffix='.png') as tmp:
                cv2.imwrite(tmp.name, processed_image)
                result = subprocess.run(
                    ['tesseract', tmp.name, 'stdout', '-l', lang, '--psm', '11', 'tsv'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                if result.returncode != 0:
                    _logger.error(f"Tesseract OCR failed: {result.stderr}")
                    return None
                
                # Parse TSV output
                lines = result.stdout.strip().split('\n')
                if len(lines) < 2:  # Need at least header and one data row
                    return []
                
                headers = lines[0].split('\t')
                results = []
                
                for line in lines[1:]:
                    parts = line.split('\t')
                    if len(parts) != len(headers):
                        continue
                        
                    data = dict(zip(headers, parts))
                    if data.get('text', '').strip():
                        try:
                            results.append({
                                'text': data['text'],
                                'conf': float(data['conf']),
                                'bbox': (
                                    int(data['left']),
                                    int(data['top']),
                                    int(data['width']),
                                    int(data['height'])
                                )
                            })
                        except (ValueError, KeyError) as e:
                            _logger.warning(f"Failed to parse line data: {e}")
                            continue
                
                return results
                
        except Exception as e:
            _logger.error(f"OCR extraction with positions failed: {e}")
            return None