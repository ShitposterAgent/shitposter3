"""HTTP server providing REST API for controlling the automation engine."""

import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
import asyncio
from ..core.engine import AutomationEngine

_logger = logging.getLogger(__name__)
app = FastAPI(title="Shitposter API", version="1.0.0")
engine: Optional[AutomationEngine] = None

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def start_engine():
    """Start the automation engine in the background."""
    global engine
    if engine is None:
        engine = AutomationEngine()
        await engine.start()

@app.on_event("startup")
async def startup_event():
    """Initialize the automation engine when the server starts."""
    background_tasks = BackgroundTasks()
    background_tasks.add_task(start_engine)

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources when the server shuts down."""
    global engine
    if engine:
        await engine.stop()

@app.get("/status")
async def get_status() -> Dict[str, Any]:
    """Get the current status of the automation engine."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    return {
        "status": "running" if engine.running else "stopped",
        "learned_patterns": len(engine.learned_patterns)
    }

@app.post("/analyze")
async def analyze_screen() -> Dict[str, Any]:
    """Analyze current screen content."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    screen_image = engine.ocr.capture_screen()
    if not screen_image:
        raise HTTPException(status_code=500, detail="Failed to capture screen")
    
    text_content = engine.ocr.extract_text(screen_image)
    analysis = await engine.ai.analyze_screen_content(text_content)
    
    return {
        "text_content": text_content,
        "analysis": analysis
    }

@app.post("/action")
async def queue_action(action: Dict[str, Any]) -> Dict[str, str]:
    """Queue an automation action."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    await engine.action_queue.put(action)
    return {"status": "queued"}

@app.post("/start")
async def start() -> Dict[str, str]:
    """Start the automation engine."""
    global engine
    if engine and engine.running:
        return {"status": "already running"}
    
    await start_engine()
    return {"status": "started"}

@app.post("/stop")
async def stop() -> Dict[str, str]:
    """Stop the automation engine."""
    global engine
    if engine:
        await engine.stop()
        return {"status": "stopped"}
    return {"status": "not running"}

def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the HTTP server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)