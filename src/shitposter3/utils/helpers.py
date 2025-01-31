"""Helper utilities for the shitposter framework."""

import os
import subprocess
from datetime import datetime
from pathlib import Path
import logging

_logger = logging.getLogger(__name__)

def take_screenshot() -> str:
    """Take a screenshot using gnome-screenshot and save with datetime filename.
    
    Returns:
        str: Path to the saved screenshot file, or None if failed
    """
    try:
        # Create screenshots directory if it doesn't exist
        screenshots_dir = os.path.expanduser("~/shitposter_data/screenshots")
        Path(screenshots_dir).mkdir(parents=True, exist_ok=True)
        
        # Generate filename with current datetime (only digits)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filepath = os.path.join(screenshots_dir, f"{timestamp}.png")
        
        # Take screenshot using gnome-screenshot
        result = subprocess.run([
            'gnome-screenshot',
            '-f', filepath  # Save to specific file
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(filepath):
            _logger.debug(f"Screenshot saved successfully to {filepath}")
            return filepath
        else:
            _logger.error(f"Screenshot failed: {result.stderr}")
            return None
            
    except Exception as e:
        _logger.error(f"Failed to take screenshot: {e}")
        return None

def get_latest_screenshot() -> str:
    """Get the path of the most recent screenshot.
    
    Returns:
        str: Path to the most recent screenshot file, or None if none found
    """
    screenshots_dir = os.path.expanduser("~/shitposter_data/screenshots")
    try:
        files = sorted(
            [f for f in os.listdir(screenshots_dir) if f.endswith('.png')],
            key=lambda x: os.path.getmtime(os.path.join(screenshots_dir, x)),
            reverse=True
        )
        return os.path.join(screenshots_dir, files[0]) if files else None
    except Exception as e:
        _logger.error(f"Failed to get latest screenshot: {e}")
        return None