"""OCR integration module using Tesseract for screen text recognition."""

import logging
import numpy as np
import cv2
import subprocess
import tempfile
import time
import os
import mss
from pathlib import Path
from ..utils.helpers import find_latest_screenshot

_logger = logging.getLogger(__name__)

class ScreenOCR:
    def __init__(self, config=None):
        self.last_screenshot_path = None
        self.config = config or {}
        _logger.debug("ScreenOCR initialized with config: %s", self.config)
        self.setup_directories()
        try:
            self.sct = mss.mss()
            self.mss_instance = mss.mss()
            # Initialize monitor configuration
            self.monitor = self._get_monitor_config()
            _logger.debug("MSS initialized successfully")
        except Exception as e:
            _logger.error("Failed to initialize MSS: %s", e)
        
    def _get_monitor_config(self):
        """Get monitor configuration based on settings or default to primary monitor."""
        try:
            monitor_number = self.config.get('screenshot', {}).get('monitor', 1)
            if monitor_number == 'primary':
                return self.mss_instance.monitors[1]  # Primary monitor is usually index 1
            elif isinstance(monitor_number, int) and 0 <= monitor_number < len(self.mss_instance.monitors):
                return self.mss_instance.monitors[monitor_number]
            else:
                _logger.warning(f"Invalid monitor number {monitor_number}, defaulting to primary")
                return self.mss_instance.monitors[1]
        except Exception as e:
            _logger.error(f"Error getting monitor config: {e}")
            # Return full screen bounds as fallback
            return {"top": 0, "left": 0, "width": 1920, "height": 1080}

    def setup_directories(self):
        """Set up screenshot directory."""
        screenshot_dir = os.path.expanduser(
            self.config.get('screenshot', {}).get('save_path', '~/shitposter_data/screenshots')
        )
        Path(screenshot_dir).mkdir(parents=True, exist_ok=True)
        _logger.debug("Screenshot directory set up at: %s", screenshot_dir)
        
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

    def capture_screen(self):
        """Capture the screen using MSS instance and save with timestamped filename."""
        try:
            # Use existing MSS instance
            screenshot = self.sct.grab(self.monitor)
            
            # Convert to BGR format for OpenCV
            img = np.array(screenshot)
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
            # Save the screenshot
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = os.path.expanduser(
                os.path.join(
                    self.config.get('screenshot', {}).get('save_path', '~/shitposter_data/screenshots'),
                    f"screenshot_{timestamp}.png"
                )
            )
            
            cv2.imwrite(filename, img)
            _logger.debug(f"Screenshot saved to: {filename}")
            self.last_screenshot_path = filename
            return img
            
        except Exception as e:
            _logger.error(f"Failed to capture screenshot using MSS: {e}")
            return None

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