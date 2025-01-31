"""Command-line interface for the shitposter automation framework."""

import click
import asyncio
import logging
import psutil
import time
import os
from datetime import datetime
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
    # Register the run command
    engine.register_command('run', os.getpid())
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
    engine = AutomationEngine()
    # Register the serve command
    engine.register_command('serve', os.getpid())
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
    """Monitor Shitposter status, processes, and screen analysis."""
    engine = AutomationEngine()
    
    try:
        while True:
            click.clear()
            
            # Get process stats
            stats = engine.get_command_stats()
            
            # Header
            click.echo("Shitposter Status Monitor")
            click.echo("=======================")
            click.echo(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            # Running Commands
            click.echo("Active Commands:")
            click.echo("--------------")
            if stats:
                for cmd_name, info in stats.items():
                    if info.get('status') != 'terminated':
                        click.echo(f"Command: {cmd_name}")
                        click.echo(f"  PID: {info.get('pid', 'N/A')}")
                        click.echo(f"  Runtime: {info.get('runtime', 0):.1f}s")
                        click.echo(f"  CPU: {info.get('cpu', 0):.1f}%")
                        click.echo(f"  Memory: {info.get('memory', 0):.1f}MB")
                        click.echo(f"  Status: {info.get('status', 'unknown')}")
                        click.echo()
            else:
                click.echo("No active commands\n")
            
            # Daily Analysis Summary
            summary = engine.get_daily_summary()
            if not summary.get('error'):
                click.echo("Screen Analysis Summary:")
                click.echo("----------------------")
                click.echo(f"Observations: {summary.get('total_observations', 0)}")
                click.echo(f"Confidence: {summary.get('average_confidence', 0):.1f}%")
                
                if summary.get('common_patterns'):
                    click.echo("\nCommon Screen Patterns:")
                    for pattern in summary.get('common_patterns', []):
                        click.echo(f"  • {pattern['pattern']} ({pattern['frequency']} times)")
            
            time.sleep(2)  # Update interval
            
    except KeyboardInterrupt:
        click.echo("\nStatus monitoring stopped.")

@cli.command()
def daily_report():
    """Generate a report of today's screen activity and resource usage."""
    engine = AutomationEngine()
    summary = engine.get_daily_summary()
    
    if summary.get('error'):
        click.echo(f"Error generating report: {summary['error']}")
        return
    
    click.echo("\nShitposter Daily Report")
    click.echo("=====================")
    click.echo(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    click.echo(f"\nAnalysis Period: {summary.get('start_time')} to {summary.get('end_time')}")
    click.echo(f"Total Observations: {summary.get('total_observations')}")
    click.echo(f"Average Confidence: {summary.get('average_confidence'):.1f}%")
    
    if summary.get('common_patterns'):
        click.echo("\nMost Common Screen Activities:")
        for pattern in summary.get('common_patterns'):
            click.echo(f"  • {pattern['pattern']}")
            click.echo(f"    Frequency: {pattern['frequency']} observations")

@cli.command()
def init():
    """Initialize shitposter configuration in user's home directory."""
    home_config = os.path.expanduser("~/shitposter.json")
    sample_config = os.path.join(os.path.dirname(__file__), "../../../shitposter-sample.json")
    
    if os.path.exists(home_config):
        click.echo("Configuration file already exists at ~/shitposter.json")
        if click.confirm("Do you want to overwrite it?", default=False):
            try:
                with open(sample_config, 'r') as src, open(home_config, 'w') as dst:
                    dst.write(src.read())
                click.echo("Configuration file has been reset to default settings")
            except Exception as e:
                click.echo(f"Error resetting configuration: {e}")
    else:
        try:
            with open(sample_config, 'r') as src, open(home_config, 'w') as dst:
                dst.write(src.read())
            click.echo("Configuration file created at ~/shitposter.json")
        except Exception as e:
            click.echo(f"Error creating configuration: {e}")

if __name__ == '__main__':
    cli()