"""Command-line interface for the shitposter automation framework."""

import click
import asyncio
import logging
import psutil
from ..core.engine import AutomationEngine
from ..services.http_server import run_server

_logger = logging.getLogger(__name__)

@click.group()
@click.option('--debug/--no-debug', default=False, help="Enable debug logging")
def cli(debug):
    """Shitposter - AI-powered desktop automation framework."""
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=log_level)

@cli.command()
@click.option('--headless/--no-headless', default=False, help="Run in headless mode")
def run(headless):
    """Run the automation engine."""
    engine = AutomationEngine()
    try:
        asyncio.run(engine.start())
    except KeyboardInterrupt:
        asyncio.run(engine.stop())
        _logger.info("Automation engine stopped")

@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind the server to')
@click.option('--port', default=8000, help='Port to run the server on')
def serve(host, port):
    """Start the HTTP API server."""
    _logger.info(f"Starting HTTP server on {host}:{port}")
    run_server(host, port)

@cli.command()
def analyze():
    """Analyze current screen content."""
    engine = AutomationEngine()
    try:
        image = engine.ocr.capture_screen()
        text = engine.ocr.extract_text(image)
        click.echo(f"Screen content:\n{text}")
    except Exception as e:
        _logger.error(f"Analysis failed: {e}")

@cli.command()
def status():
    """Print detailed status of the Shitposter processes."""
    try:
        while True:
            click.clear()
            click.echo("Shitposter Status:")
            click.echo("=================")
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status']):
                click.echo(f"PID: {proc.info['pid']}")
                click.echo(f"Name: {proc.info['name']}")
                click.echo(f"CPU: {proc.info['cpu_percent']}%")
                click.echo(f"Memory: {proc.info['memory_info'].rss / 1024 ** 2:.2f} MB")
                click.echo(f"Status: {proc.info['status']}")
                click.echo("-----------------")
            asyncio.sleep(1)
    except KeyboardInterrupt:
        click.echo("Status monitoring stopped.")

if __name__ == '__main__':
    cli()