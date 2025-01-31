"""OCR integration module using Tesseract for screen text recognition."""

import logging
import numpy as np
import cv2
import subprocess
import tempfile
import json
import time
import os
from pathlib import Path
from ..utils.helpers import simulate_screenshot_shortcut, find_latest_screenshot

_logger = logging.getLogger(__name__)

class ScreenOCR:
    def __init__(self, config=None):
        self.last_screenshot_path = None
        self.config = config or {}
        self.setup_directories()
        
    def setup_directories(self):
        """Set up screenshot and analysis directories."""
        screenshot_dir = os.path.expanduser(
            self.config.get('screenshot', {}).get('save_path', '~/shitposter_data/screenshots')
        )
        Path(screenshot_dir).mkdir(parents=True, exist_ok=True)
        
    def cleanup_old_screenshots(self):
        """Clean up old screenshots based on max_stored setting."""
        max_stored = self.config.get('screenshot', {}).get('max_stored', 1000)
        screenshot_dir = os.path.expanduser(
            self.config.get('screenshot', {}).get('save_path', '~/shitposter_data/screenshots')
        )
        
        files = []
        for f in Path(screenshot_dir).glob('*.png'):
            files.append((f.stat().st_mtime, f))
            
        # Sort by modification time and remove oldest files if exceeding max_stored
        files.sort(reverse=True)
        for _, file_path in files[max_stored:]:
            try:
                file_path.unlink()
            except Exception as e:
                _logger.error(f"Failed to remove old screenshot {file_path}: {e}")

    def capture_screen(self, monitor_number=1):
        """Capture screen content using system screenshot functionality."""
        try:
            # Simulate the screenshot shortcut
            simulate_screenshot_shortcut()
            
            # Give the system a moment to save the screenshot
            interval = self.config.get('screenshot', {}).get('interval', 5)
            time.sleep(min(interval * 0.1, 0.5))  # Wait up to 0.5s or 10% of interval
            
            # Find the newly created screenshot
            screenshot_path = find_latest_screenshot(max_age_seconds=5)
            
            if not screenshot_path:
                _logger.error("No recent screenshot found after simulating shortcut")
                return None
                
            self.last_screenshot_path = screenshot_path
            # Read the image using OpenCV
            image = cv2.imread(screenshot_path)
            
            if image is None:
                _logger.error(f"Failed to read screenshot from {screenshot_path}")
                return None

            # Clean up old screenshots after successful capture
            self.cleanup_old_screenshots()
                
            return image
            
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

    def extract_text(self, image=None, lang=None):
        """Extract text from image using Tesseract OCR via subprocess."""
        try:
            if image is None:
                image = self.capture_screen()
            
            if image is None:
                _logger.error("No image captured to extract text.")
                return None

            # Use lang from config if not specified
            if lang is None:
                lang = self.config.get('tesseract', {}).get('lang', 'eng')
                
            processed_image = self.process_image(image)
            with tempfile.NamedTemporaryFile(suffix='.png') as tmp:
                cv2.imwrite(tmp.name, processed_image)
                psm = self.config.get('tesseract', {}).get('psm', 11)
                result = subprocess.run(
                    ['tesseract', tmp.name, 'stdout', '-l', lang, '--psm', str(psm)],
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

    def get_last_screenshot_path(self):
        """Get the path of the last captured screenshot."""
        return self.last_screenshot_path

    def extract_text_with_positions(self, image=None, lang=None):
        """Extract text with position data using Tesseract OCR."""
        try:
            if image is None:
                image = self.capture_screen()
            
            if image is None:
                return None

            # Use lang from config if not specified
            if lang is None:
                lang = self.config.get('tesseract', {}).get('lang', 'eng')
                
            processed_image = self.process_image(image)
            with tempfile.NamedTemporaryFile(suffix='.png') as tmp:
                cv2.imwrite(tmp.name, processed_image)
                psm = self.config.get('tesseract', {}).get('psm', 11)
                result = subprocess.run(
                    ['tesseract', tmp.name, 'stdout', '-l', lang, '--psm', str(psm), 'tsv'],
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