"""Command-line interface for the shitposter automation framework."""

import click
import asyncio
import logging
import psutil
import time
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
    def get_process_info():
        total_cpu = 0
        total_memory = 0
        process_count = 0
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            try:
                if 'python' in proc.info['name'].lower() and 'shitposter' in ' '.join(proc.cmdline()).lower():
                    total_cpu += proc.info['cpu_percent']
                    total_memory += proc.info['memory_info'].rss
                    process_count += 1
                    processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        return {
            'processes': processes,
            'total_cpu': total_cpu,
            'total_memory': total_memory / (1024 * 1024),  # Convert to MB
            'process_count': process_count
        }

    try:
        while True:
            click.clear()
            stats = get_process_info()
            
            click.echo("Shitposter Status")
            click.echo("================")
            click.echo(f"Active Processes: {stats['process_count']}")
            click.echo(f"Total CPU Usage: {stats['total_cpu']:.1f}%")
            click.echo(f"Total Memory: {stats['total_memory']:.1f} MB")
            click.echo()
            
            time.sleep(2)  # Update every 2 seconds
            
    except KeyboardInterrupt:
        click.echo("\nStatus monitoring stopped.")

if __name__ == '__main__':
    cli()