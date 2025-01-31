"""Ollama AI model integration for intelligent processing and response generation."""

import logging
import json
import aiohttp
import asyncio
from typing import Dict, Any, Optional

_logger = logging.getLogger(__name__)

class OllamaAI:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        self.base_url = base_url
        self.model = model
        self.context = []
        self.max_context_length = 10

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Generate a response using the Ollama model."""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
                
                if system_prompt:
                    payload["system"] = system_prompt

                async with session.post(f"{self.base_url}/api/generate", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        self._update_context(prompt, result.get('response', ''))
                        return result
                    else:
                        error_text = await response.text()
                        _logger.error(f"Ollama API error: {error_text}")
                        return {"error": error_text}

        except Exception as e:
            _logger.error(f"Failed to generate response: {e}")
            return {"error": str(e)}

    def _update_context(self, prompt: str, response: str):
        """Update conversation context, maintaining a sliding window."""
        self.context.append({"prompt": prompt, "response": response})
        if len(self.context) > self.max_context_length:
            self.context.pop(0)

    async def analyze_screen_content(self, text_content: str) -> Dict[str, Any]:
        """Analyze screen content and provide understanding/actions."""
        system_prompt = """You are an AI assistant analyzing screen content. 
        Identify key elements, important information, and potential actions. 
        Format your response as JSON with the following structure:
        {
            "understanding": "brief description of what you see",
            "key_elements": ["list of important elements"],
            "suggested_actions": ["list of possible actions"],
            "confidence": 0.0 to 1.0
        }"""
        
        result = await self.generate(text_content, system_prompt)
        try:
            if isinstance(result.get('response'), str):
                return json.loads(result['response'])
        except json.JSONDecodeError:
            _logger.error("Failed to parse JSON response")
        
        return {
            "understanding": "Failed to analyze content",
            "key_elements": [],
            "suggested_actions": [],
            "confidence": 0.0
        }

    async def learn_from_interaction(self, screen_before: str, user_action: str, screen_after: str) -> Dict[str, Any]:
        """Learn from user interactions by analyzing before/after states."""
        learning_prompt = f"""Analyze the following interaction sequence:
        Before: {screen_before}
        User Action: {user_action}
        After: {screen_after}
        
        What can be learned from this interaction? Format response as JSON:
        {{
            "pattern": "identified pattern",
            "trigger_conditions": ["list of conditions"],
            "expected_outcome": "what should happen",
            "confidence": 0.0 to 1.0
        }}"""
        
        result = await self.generate(learning_prompt)
        try:
            if isinstance(result.get('response'), str):
                return json.loads(result['response'])
        except json.JSONDecodeError:
            _logger.error("Failed to parse learning response")
        
        return {
            "pattern": "Failed to learn from interaction",
            "trigger_conditions": [],
            "expected_outcome": "",
            "confidence": 0.0
        }