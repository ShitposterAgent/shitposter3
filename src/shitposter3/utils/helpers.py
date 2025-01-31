"""Helper utilities for the shitposter framework."""

import os
import glob
from datetime import datetime
from pathlib import Path
import time
from pynput.keyboard import Key, Controller

keyboard = Controller()

def simulate_screenshot_shortcut():
    """Simulate pressing Shift+PrtScr."""
    keyboard.press(Key.shift)
    keyboard.press(Key.print_screen)
    time.sleep(0.1)  # Small delay to ensure key press is registered
    keyboard.release(Key.print_screen)
    keyboard.release(Key.shift)

def get_screenshots_directory():
    """Get the system's screenshots directory."""
    # Common screenshot directories
    possible_dirs = [
        os.path.expanduser("~/Pictures/Screenshots"),  # GNOME default
        os.path.expanduser("~/Pictures"),  # Generic Pictures folder
        os.path.expanduser("~/Desktop")  # Fallback
    ]
    
    for dir_path in possible_dirs:
        if os.path.exists(dir_path):
            return dir_path
    
    return None

def find_latest_screenshot(max_age_seconds=5):
    """Find the most recent screenshot in the screenshots directory.
    
    Args:
        max_age_seconds (int): Maximum age in seconds to consider a screenshot as recent
        
    Returns:
        str: Path to the most recent screenshot file, or None if no recent screenshot found
    """
    screenshots_dir = get_screenshots_directory()
    if not screenshots_dir:
        return None
        
    # Look for common screenshot file patterns
    patterns = [
        "Screenshot*.png",  # GNOME pattern
        "screen*.png",      # Alternative pattern
        "*.png"            # Any PNG file
    ]
    
    newest_file = None
    newest_time = 0
    
    for pattern in patterns:
        search_path = os.path.join(screenshots_dir, pattern)
        for file_path in glob.glob(search_path):
            file_time = os.path.getmtime(file_path)
            age = time.time() - file_time
            
            if age <= max_age_seconds and file_time > newest_time:
                newest_file = file_path
                newest_time = file_time
    
    return newest_file