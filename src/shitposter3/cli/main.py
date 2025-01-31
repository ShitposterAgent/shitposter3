"""Command-line interface for the shitposter automation framework."""

import click
import asyncio
import logging
import psutil
import time
import os
import json
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
    # Load config at CLI startup
    config = None
    try:
        with open(os.path.expanduser("~/shitposter.json"), 'r') as f:
            config = json.load(f)
    except Exception as e:
        _logger.warning(f"Failed to load config: {e}, using defaults")

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
    async def run_analysis():
        engine = AutomationEngine()
        try:
            # Take new screenshot with specific timestamp filename
            screenshot_path = engine.take_new_screenshot()
            if not screenshot_path:
                click.echo("Failed to capture screenshot")
                return

            # Run complete analysis
            result = await engine.analyze_screenshot(screenshot_path)
            if "error" in result:
                click.echo(f"Analysis failed: {result['error']}")
                return

            # Display results in user-friendly format
            click.echo("\nScreen Analysis Results")
            click.echo("=====================")
            click.echo(f"\nScreenshot saved as: {os.path.basename(screenshot_path)}")
            click.echo("\nExtracted Text:")
            click.echo("--------------")
            click.echo(result["extracted_text"])
            click.echo("\nInterpretation:")
            click.echo("--------------")
            click.echo(result["interpretation"])

        except Exception as e:
            _logger.error(f"Analysis failed: {e}")
            click.echo(f"Analysis failed: {str(e)}")

    asyncio.run(run_analysis())

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

@cli.command()
@click.argument('platform')
@click.option('--text', help='Text content to post')
@click.option('--title', help='Title for the post (required for Reddit)')
@click.option('--media', multiple=True, help='Path to media files to attach')
@click.option('--subreddit', help='Subreddit to post to (for Reddit)')
@click.option('--type', 'post_type', help='Post type (for Reddit: text/link)', default='text')
async def post(platform, text, title, media, subreddit, post_type):
    """Post content to social media platforms.
    
    Example: shitposter post twitter --text "Hello world" --media image1.jpg image2.jpg
    """
    engine = AutomationEngine()
    
    try:
        # Initialize social media manager
        if not await engine.social_media.connect():
            click.echo("Failed to connect to Chrome. Make sure Chrome is running with remote debugging enabled.")
            return

        content = {
            'text': text,
            'title': title,
            'media': list(media) if media else None,
            'subreddit': subreddit,
            'type': post_type
        }

        if await engine.social_media.post_content(platform, content):
            click.echo(f"Successfully posted to {platform}")
        else:
            click.echo(f"Failed to post to {platform}")

    except Exception as e:
        click.echo(f"Error posting content: {e}")
    finally:
        await engine.social_media.close()

if __name__ == '__main__':
    cli()