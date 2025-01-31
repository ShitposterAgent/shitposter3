"""Core engine coordinating all components of the shitposter automation framework."""

import logging
import asyncio
import psutil
from typing import Dict, Any, List, Optional
from ..modules.tesseract_integration import ScreenOCR
from ..modules.ollama_integration import OllamaAI
from pynput import mouse, keyboard
import json
import os
import time
from pathlib import Path
from datetime import datetime

_logger = logging.getLogger(__name__)

class AutomationEngine:
    def __init__(self):
        self.config = self._load_config()
        self.ocr = ScreenOCR(self.config)
        self.ai = OllamaAI(
            base_url=self.config['ollama']['base_url'],
            model=self.config['ollama']['model']
        )
        self.social_media = SocialMediaManager(self.config)
        self.running = False
        self.learned_patterns = []
        self.mouse_listener = None
        self.keyboard_listener = None
        self.last_screen_content = None
        self.action_queue = asyncio.Queue()
        self.running_commands = {}
        self.daily_analysis = []
        self._setup_directories()

    def _load_config(self) -> dict:
        """Load configuration from user's home directory or fall back to sample."""
        home_config = os.path.expanduser("~/shitposter.json")
        sample_config = os.path.join(os.path.dirname(__file__), "../../../shitposter-sample.json")
        
        try:
            if os.path.exists(home_config):
                with open(home_config, 'r') as f:
                    return json.load(f)
            with open(sample_config, 'r') as f:
                return json.load(f)
        except Exception as e:
            _logger.error(f"Failed to load config: {e}")
            return {
                "screenshot": {"interval": 5},
                "ollama": {"model": "llama2", "base_url": "http://localhost:11434"},
                "monitoring": {"update_interval": 2}
            }

    def _setup_directories(self):
        """Set up necessary directories for storing data."""
        paths = [
            os.path.expanduser(self.config["screenshot"].get("save_path", "~/shitposter_data/screenshots")),
            os.path.expanduser(self.config["monitoring"].get("analysis_dir", "~/shitposter_data/analysis"))
        ]
        for path in paths:
            Path(path).mkdir(parents=True, exist_ok=True)

    def register_command(self, command_name: str, pid: int):
        """Register a running shitposter command."""
        self.running_commands[command_name] = {
            'pid': pid,
            'start_time': time.time(),
            'stats': {'cpu': 0, 'memory': 0}
        }

    def get_command_stats(self) -> Dict[str, Any]:
        """Get statistics about running shitposter commands."""
        current_stats = {}
        for cmd_name, info in self.running_commands.items():
            try:
                proc = psutil.Process(info['pid'])
                current_stats[cmd_name] = {
                    'pid': info['pid'],
                    'runtime': time.time() - info['start_time'],
                    'cpu': proc.cpu_percent(),
                    'memory': proc.memory_info().rss / (1024 * 1024),  # MB
                    'status': proc.status()
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                current_stats[cmd_name] = {'status': 'terminated'}
        return current_stats

    async def start(self):
        """Start the automation engine."""
        self.running = True
        self.mouse_listener = mouse.Listener(
            on_click=self._on_click,
            on_scroll=self._on_scroll
        )
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        
        self.mouse_listener.start()
        self.keyboard_listener.start()
        
        # Start screen analysis task
        asyncio.create_task(self._screen_analysis_loop())
        await self._main_loop()

    async def stop(self):
        """Stop the automation engine."""
        self.running = False
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()

    async def _main_loop(self):
        """Main processing loop."""
        while self.running:
            try:
                # Capture and analyze screen
                screen_image = self.ocr.capture_screen()
                if screen_image:
                    text_content = self.ocr.extract_text(screen_image)
                    if text_content:
                        analysis = await self.ai.analyze_screen_content(text_content)
                        await self._process_analysis(analysis)
                        self.last_screen_content = text_content

                # Process any queued actions
                while not self.action_queue.empty():
                    action = await self.action_queue.get()
                    await self._execute_action(action)

                await asyncio.sleep(0.1)  # Prevent CPU overload

            except Exception as e:
                _logger.error(f"Error in main loop: {e}")

    async def _screen_analysis_loop(self):
        """Continuous screen analysis loop."""
        interval = self.config['screenshot'].get('interval', 5)
        while self.running:
            try:
                screen_image = self.ocr.capture_screen()
                if screen_image:
                    text_content = self.ocr.extract_text(screen_image)
                    if text_content:
                        # Run AI analysis with custom prompt if configured
                        ai_prompt = self.config.get('ollama', {}).get('prompt')
                        analysis = await self.ai.analyze_screen_content(
                            text_content, 
                            system_prompt=ai_prompt
                        )
                        
                        # Save analysis with timestamp and screenshot path
                        self.daily_analysis.append({
                            'timestamp': datetime.now().isoformat(),
                            'screenshot_path': self.ocr.get_last_screenshot_path(),
                            'content': text_content,
                            'analysis': analysis
                        })
                        
                        # Save analysis if configured
                        if self.config['monitoring'].get('save_analysis', True):
                            self._save_daily_analysis()
                            
                        # Print to CLI if debug logging is enabled
                        _logger.debug(f"Screen Analysis:\n{json.dumps(analysis, indent=2)}")
                    else:
                        _logger.warning("No text extracted from screen image.")
                else:
                    _logger.warning("Screen capture returned None.")
                
                await asyncio.sleep(interval)
            except Exception as e:
                _logger.error(f"Screen analysis error: {e}")
                await asyncio.sleep(5)  # Wait before retrying

    def _save_daily_analysis(self):
        """Save the accumulated daily analysis to a file."""
        if not self.daily_analysis:
            return
            
        analysis_dir = os.path.expanduser(self.config['monitoring']['analysis_dir'])
        date_str = datetime.now().strftime('%Y-%m-%d')
        file_path = os.path.join(analysis_dir, f'analysis_{date_str}.json')
        
        try:
            with open(file_path, 'w') as f:
                json.dump(self.daily_analysis, f, indent=2)
        except Exception as e:
            _logger.error(f"Failed to save daily analysis: {e}")

    def get_daily_summary(self) -> Dict[str, Any]:
        """Generate a summary of the day's screen activity."""
        if not self.daily_analysis:
            return {"error": "No analysis data available"}
            
        try:
            # Aggregate confidence scores and patterns
            total_confidence = 0
            patterns = {}
            for entry in self.daily_analysis:
                analysis = entry['analysis']
                total_confidence += analysis.get('confidence', 0)
                for element in analysis.get('key_elements', []):
                    patterns[element] = patterns.get(element, 0) + 1
            
            # Sort patterns by frequency
            sorted_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)
            
            return {
                "total_observations": len(self.daily_analysis),
                "average_confidence": total_confidence / len(self.daily_analysis) if self.daily_analysis else 0,
                "common_patterns": [{"pattern": p[0], "frequency": p[1]} for p in sorted_patterns[:5]],
                "start_time": self.daily_analysis[0]['timestamp'] if self.daily_analysis else None,
                "end_time": self.daily_analysis[-1]['timestamp'] if self.daily_analysis else None
            }
        except Exception as e:
            _logger.error(f"Failed to generate daily summary: {e}")
            return {"error": f"Failed to generate summary: {str(e)}"}

    async def _process_analysis(self, analysis: Dict[str, Any]):
        """Process AI analysis of screen content."""
        if analysis.get('confidence', 0) > 0.7:  # Confidence threshold
            for action in analysis.get('suggested_actions', []):
                await self.action_queue.put(action)

    async def _execute_action(self, action: Dict[str, Any]):
        """Execute an automation action."""
        try:
            action_type = action.get('type')
            if action_type == 'click':
                # Simulate mouse click
                pass
            elif action_type == 'type':
                # Simulate keyboard input
                pass
            elif action_type == 'scroll':
                # Simulate scrolling
                pass
            
            # After action execution, capture and analyze the result
            if self.last_screen_content:
                new_content = self.ocr.extract_text()
                await self.ai.learn_from_interaction(
                    self.last_screen_content,
                    json.dumps(action),
                    new_content
                )
        
        except Exception as e:
            _logger.error(f"Failed to execute action: {e}")

    def _on_click(self, x, y, button, pressed):
        """Mouse click event handler."""
        if pressed:
            asyncio.create_task(self._learn_from_click(x, y))

    async def _learn_from_click(self, x: int, y: int):
        """Learn from user's mouse clicks."""
        if self.last_screen_content:
            elements = self.ocr.extract_text_with_positions()
            clicked_element = self._find_element_at_position(elements, x, y)
            if clicked_element:
                await self.ai.learn_from_interaction(
                    self.last_screen_content,
                    f"clicked: {clicked_element['text']}",
                    self.ocr.extract_text()
                )

    def _find_element_at_position(self, elements: List[Dict], x: int, y: int) -> Optional[Dict]:
        """Find text element at given coordinates."""
        for element in elements:
            bbox = element['bbox']
            if (bbox[0] <= x <= bbox[0] + bbox[2] and 
                bbox[1] <= y <= bbox[1] + bbox[3]):
                return element
        return None

    def _on_scroll(self, x, y, dx, dy):
        """Mouse scroll event handler."""
        asyncio.create_task(self._learn_from_scroll(x, y, dx, dy))

    def _on_key_press(self, key):
        """Keyboard press event handler."""
        asyncio.create_task(self._learn_from_key(key, True))

    def _on_key_release(self, key):
        """Keyboard release event handler."""
        asyncio.create_task(self._learn_from_key(key, False))

    async def _learn_from_scroll(self, x: int, y: int, dx: int, dy: int):
        """Learn from user's scrolling behavior."""
        if self.last_screen_content:
            await self.ai.learn_from_interaction(
                self.last_screen_content,
                f"scroll: dx={dx}, dy={dy}",
                self.ocr.extract_text()
            )

    async def _learn_from_key(self, key, pressed: bool):
        """Learn from user's keyboard input."""
        if self.last_screen_content:
            await self.ai.learn_from_interaction(
                self.last_screen_content,
                f"key {'pressed' if pressed else 'released'}: {key}",
                self.ocr.extract_text()
            )

    def take_new_screenshot(self) -> Optional[str]:
        """Take a new screenshot and return its path."""
        from ..utils.helpers import take_screenshot
        return take_screenshot()

    async def analyze_screenshot(self, screenshot_path: str) -> Dict[str, Any]:
        """Analyze a screenshot file with OCR and AI interpretation."""
        text = self.ocr.extract_text_from_file(screenshot_path)
        if not text:
            return {"error": "No text extracted from screenshot"}
            
        interpretation = await self.ai.interpret_screen(
            text, 
            self.config['ollama'].get('interpretation_prompt')
        )
        
        return {
            "screenshot_path": screenshot_path,
            "extracted_text": text,
            "interpretation": interpretation
        }

    async def post_to_social(self, platform: str, content: Dict[str, Any]) -> bool:
        """Post content to social media platform."""
        if not self.social_media:
            _logger.error("Social media manager not initialized")
            return False
            
        try:
            # Connect to Chrome if not already connected
            if not await self.social_media.connect():
                _logger.error("Failed to connect to Chrome")
                return False
                
            # Add AI-generated hashtags if enabled
            if (platform == "twitter" and 
                self.config["social_media"]["twitter"].get("auto_hashtags")):
                hashtags = await self.ai.generate_hashtags(content["text"])
                content["text"] += f"\n\n{' '.join(hashtags)}"
                
            return await self.social_media.post_content(platform, content)
            
        except Exception as e:
            _logger.error(f"Failed to post to {platform}: {e}")
            return False