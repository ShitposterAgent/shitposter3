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
        self.last_analysis_time = None

    async def interpret_screen(self, text_content: str, prompt_template: Optional[str] = None) -> str:
        """Interpret screen content using the configured prompt.
        
        Args:
            text_content: The extracted text from the screen
            prompt_template: Optional custom prompt template from config
            
        Returns:
            str: AI interpretation of the screen content
        """
        if not prompt_template:
            prompt_template = "in a few words, what is this image about?"
            
        prompt = f"{prompt_template}\n\nScreen content:\n{text_content}"
        
        result = await self.generate(prompt)
        return result.get('response', 'Failed to interpret screen content')

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
        system_prompt = """You are an AI assistant analyzing screen content to understand user activities.
        Analyze the following screen content and provide insights.
        Format your response as JSON with the following structure:
        {
            "understanding": "detailed description of what's happening on screen",
            "detected_activities": ["list of specific activities detected"],
            "key_elements": ["important UI elements or text found"],
            "user_intent": "likely user intention based on content",
            "context_category": "category of the activity (e.g., browsing, coding, document editing)",
            "confidence": "confidence score between 0.0 and 1.0",
            "suggested_automations": ["potential automation opportunities"]
        }"""
        
        result = await self.generate(text_content, system_prompt)
        try:
            if isinstance(result.get('response'), str):
                analysis = json.loads(result['response'])
                analysis['timestamp'] = self.last_analysis_time
                return analysis
        except json.JSONDecodeError:
            _logger.error("Failed to parse JSON response from Ollama")
        
        return {
            "understanding": "Failed to analyze content",
            "detected_activities": [],
            "key_elements": [],
            "user_intent": "unknown",
            "context_category": "unknown",
            "confidence": 0.0,
            "suggested_automations": []
        }

    async def learn_from_interaction(self, screen_before: str, user_action: str, screen_after: str) -> Dict[str, Any]:
        """Learn from user interactions by analyzing before/after states."""
        learning_prompt = f"""Analyze this interaction sequence for automation potential:
        Before Screen: {screen_before}
        User Action: {user_action}
        After Screen: {screen_after}
        
        Format response as JSON:
        {{
            "pattern_detected": "description of the interaction pattern",
            "trigger_conditions": ["conditions that led to the action"],
            "action_impact": "what changed after the action",
            "automation_potential": "score between 0.0 and 1.0",
            "suggested_rule": "how this could be automated"
        }}"""
        
        result = await self.generate(learning_prompt)
        try:
            if isinstance(result.get('response'), str):
                return json.loads(result['response'])
        except json.JSONDecodeError:
            _logger.error("Failed to parse learning response")
        
        return {
            "pattern_detected": "Failed to analyze interaction",
            "trigger_conditions": [],
            "action_impact": "unknown",
            "automation_potential": 0.0,
            "suggested_rule": ""
        }