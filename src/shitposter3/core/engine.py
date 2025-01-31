"""Core engine coordinating all components of the shitposter automation framework."""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from ..modules.tesseract_integration import ScreenOCR
from ..modules.ollama_integration import OllamaAI
from pynput import mouse, keyboard
import json

_logger = logging.getLogger(__name__)

class AutomationEngine:
    def __init__(self):
        self.ocr = ScreenOCR()
        self.ai = OllamaAI()
        self.running = False
        self.learned_patterns = []
        self.mouse_listener = None
        self.keyboard_listener = None
        self.last_screen_content = None
        self.action_queue = asyncio.Queue()

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