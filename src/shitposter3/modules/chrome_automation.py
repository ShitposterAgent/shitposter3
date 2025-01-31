"""Chrome browser automation using remote debugging protocol."""

import logging
import asyncio
import aiohttp
import json
from typing import Dict, Any, List, Optional
import websockets
from urllib.parse import urljoin
import base64

_logger = logging.getLogger(__name__)

class ChromeRemoteDebugger:
    def __init__(self, debug_url: str = "http://localhost:9222"):
        self.debug_url = debug_url
        self.ws_url = None
        self.ws = None
        self.message_id = 0
        self.callbacks = {}
        self._listening = False
        self.current_tab = None

    async def connect(self) -> bool:
        """Connect to Chrome's remote debugging port."""
        try:
            # Get available tabs
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.debug_url}/json") as response:
                    if response.status != 200:
                        _logger.error("Failed to get Chrome tabs")
                        return False
                    
                    tabs = await response.json()
                    if not tabs:
                        _logger.error("No Chrome tabs found")
                        return False

                    # Use first available tab
                    self.current_tab = next(
                        (tab for tab in tabs if tab["type"] == "page"),
                        None
                    )
                    
                    if not self.current_tab:
                        _logger.error("No valid Chrome tabs found")
                        return False

                    self.ws_url = self.current_tab["webSocketDebuggerUrl"]
                    
            # Connect to WebSocket
            self.ws = await websockets.connect(self.ws_url)
            self._listening = True
            asyncio.create_task(self._listen())
            _logger.info("Connected to Chrome debugger")
            return True

        except Exception as e:
            _logger.error(f"Failed to connect to Chrome: {e}")
            return False

    async def _listen(self):
        """Listen for WebSocket messages."""
        while self._listening and self.ws:
            try:
                message = await self.ws.recv()
                data = json.loads(message)
                
                if "id" in data:
                    callback = self.callbacks.pop(data["id"], None)
                    if callback:
                        await callback(data)
                        
            except websockets.exceptions.ConnectionClosed:
                _logger.warning("WebSocket connection closed")
                break
            except Exception as e:
                _logger.error(f"Error in WebSocket listener: {e}")

    async def send_command(self, method: str, params: Dict = None) -> Dict[str, Any]:
        """Send command to Chrome and wait for response."""
        if not self.ws:
            raise Exception("Not connected to Chrome")

        self.message_id += 1
        message = {
            "id": self.message_id,
            "method": method,
            "params": params or {}
        }

        response_future = asyncio.Future()
        self.callbacks[self.message_id] = response_future.set_result
        
        await self.ws.send(json.dumps(message))
        response = await response_future
        return response

    async def navigate(self, url: str) -> bool:
        """Navigate to a URL."""
        response = await self.send_command("Page.navigate", {"url": url})
        return "error" not in response

    async def get_document(self) -> Dict[str, Any]:
        """Get the DOM document."""
        response = await self.send_command("DOM.getDocument")
        return response.get("result", {}).get("root", {})

    async def query_selector(self, selector: str) -> Optional[int]:
        """Find element by CSS selector."""
        response = await self.send_command(
            "DOM.querySelector",
            {
                "nodeId": (await self.get_document()).get("nodeId"),
                "selector": selector
            }
        )
        return response.get("result", {}).get("nodeId")

    async def set_input_value(self, selector: str, value: str) -> bool:
        """Set value of an input element."""
        node_id = await self.query_selector(selector)
        if not node_id:
            return False

        # Focus the element
        await self.send_command("DOM.focus", {"nodeId": node_id})
        
        # Input the text
        await self.send_command(
            "Input.insertText",
            {"text": value}
        )
        return True

    async def click_element(self, selector: str) -> bool:
        """Click an element using CSS selector."""
        # Find element
        node_id = await self.query_selector(selector)
        if not node_id:
            return False

        # Get element box model
        box_model = await self.send_command(
            "DOM.getBoxModel",
            {"nodeId": node_id}
        )
        
        if "result" not in box_model:
            return False

        # Calculate center point
        content = box_model["result"]["model"]["content"]
        x = (content[0] + content[2]) / 2
        y = (content[1] + content[5]) / 2

        # Simulate mouse click
        await self.send_command(
            "Input.dispatchMouseEvent",
            {
                "type": "mousePressed",
                "x": x,
                "y": y,
                "button": "left",
                "clickCount": 1
            }
        )
        
        await self.send_command(
            "Input.dispatchMouseEvent",
            {
                "type": "mouseReleased",
                "x": x,
                "y": y,
                "button": "left",
                "clickCount": 1
            }
        )
        return True

    async def wait_for_selector(self, selector: str, timeout: int = 5000) -> bool:
        """Wait for an element to appear."""
        try:
            deadline = asyncio.get_event_loop().time() + (timeout / 1000)
            while asyncio.get_event_loop().time() < deadline:
                if await self.query_selector(selector):
                    return True
                await asyncio.sleep(0.1)
            return False
        except Exception as e:
            _logger.error(f"Error waiting for selector: {e}")
            return False

    async def get_text_content(self, selector: str) -> Optional[str]:
        """Get text content of an element."""
        node_id = await self.query_selector(selector)
        if not node_id:
            return None

        response = await self.send_command(
            "DOM.getOuterHTML",
            {"nodeId": node_id}
        )
        return response.get("result", {}).get("outerHTML")

    async def execute_script(self, script: str) -> Any:
        """Execute JavaScript in the page."""
        response = await self.send_command(
            "Runtime.evaluate",
            {
                "expression": script,
                "returnByValue": True
            }
        )
        return response.get("result", {}).get("value")

    async def screenshot(self, selector: Optional[str] = None) -> Optional[bytes]:
        """Take a screenshot of the page or element."""
        if selector:
            node_id = await self.query_selector(selector)
            if not node_id:
                return None
                
            # Get element box model
            box_model = await self.send_command(
                "DOM.getBoxModel",
                {"nodeId": node_id}
            )
            
            if "result" not in box_model:
                return None
                
            content = box_model["result"]["model"]["content"]
            clip = {
                "x": content[0],
                "y": content[1],
                "width": content[2] - content[0],
                "height": content[5] - content[1],
                "scale": 1
            }
        else:
            clip = None

        response = await self.send_command(
            "Page.captureScreenshot",
            {"clip": clip} if clip else {}
        )
        
        if "result" in response:
            return base64.b64decode(response["result"]["data"])
        return None

    async def close(self):
        """Close the connection."""
        self._listening = False
        if self.ws:
            await self.ws.close()
            self.ws = None