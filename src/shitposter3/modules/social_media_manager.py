"""Social Media automation manager using Chrome remote debugging."""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from .chrome_automation import ChromeRemoteDebugger
import json
import os
from pathlib import Path

_logger = logging.getLogger(__name__)

class SocialMediaManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('social_media', {})
        self.chrome = ChromeRemoteDebugger(
            debug_url=self.config.get('chrome_debug_url', 'http://localhost:9222')
        )
        self.supported_platforms = {
            'twitter': self._post_to_twitter,
            'reddit': self._post_to_reddit,
            'linkedin': self._post_to_linkedin,
            'facebook': self._post_to_facebook
        }

    async def connect(self) -> bool:
        """Connect to Chrome instance."""
        return await self.chrome.connect()

    async def post_content(self, platform: str, content: Dict[str, Any]) -> bool:
        """Post content to specified social media platform.
        
        Args:
            platform: Name of the platform (twitter, reddit, etc.)
            content: Dictionary containing post content and options
        """
        if platform not in self.supported_platforms:
            _logger.error(f"Unsupported platform: {platform}")
            return False

        try:
            return await self.supported_platforms[platform](content)
        except Exception as e:
            _logger.error(f"Failed to post to {platform}: {e}")
            return False

    async def _post_to_twitter(self, content: Dict[str, Any]) -> bool:
        """Post content to Twitter."""
        try:
            # Navigate to Twitter compose
            await self.chrome.navigate('https://twitter.com/compose/tweet')
            
            # Wait for tweet composer
            if not await self.chrome.wait_for_selector('div[data-testid="tweetTextarea_0"]'):
                return False

            # Input text
            await self.chrome.set_input_value(
                'div[data-testid="tweetTextarea_0"]', 
                content['text']
            )

            # Handle media if present
            if content.get('media'):
                await self._handle_twitter_media(content['media'])

            # Click tweet button
            await self.chrome.click_element('div[data-testid="tweetButton"]')
            return True

        except Exception as e:
            _logger.error(f"Twitter posting error: {e}")
            return False

    async def _post_to_reddit(self, content: Dict[str, Any]) -> bool:
        """Post content to Reddit."""
        try:
            subreddit = content.get('subreddit', '')
            await self.chrome.navigate(f'https://www.reddit.com/r/{subreddit}/submit')
            
            # Wait for post type selection
            if not await self.chrome.wait_for_selector('div[data-test-id="post-content"]'):
                return False

            # Select post type (text/link/image)
            post_type = content.get('type', 'text')
            if post_type == 'text':
                await self.chrome.click_element('button[role="tab"][aria-label="Post"]')
            elif post_type == 'link':
                await self.chrome.click_element('button[role="tab"][aria-label="Link"]')

            # Input title
            await self.chrome.set_input_value(
                'textarea[placeholder="Title"]',
                content['title']
            )

            # Input content
            if post_type == 'text':
                await self.chrome.set_input_value(
                    'div[data-test-id="post-content"]',
                    content['text']
                )
            elif post_type == 'link':
                await self.chrome.set_input_value(
                    'input[placeholder="Url"]',
                    content['url']
                )

            # Submit post
            await self.chrome.click_element('button[data-test-id="post-submit-button"]')
            return True

        except Exception as e:
            _logger.error(f"Reddit posting error: {e}")
            return False

    async def _post_to_linkedin(self, content: Dict[str, Any]) -> bool:
        """Post content to LinkedIn."""
        try:
            await self.chrome.navigate('https://www.linkedin.com/feed/')
            
            # Click post button
            await self.chrome.click_element('button[data-control-name="create_post"]')
            
            # Wait for post modal
            if not await self.chrome.wait_for_selector('div[data-placeholder="What do you want to talk about?"]'):
                return False

            # Input content
            await self.chrome.set_input_value(
                'div[data-placeholder="What do you want to talk about?"]',
                content['text']
            )

            # Handle media if present
            if content.get('media'):
                await self._handle_linkedin_media(content['media'])

            # Post
            await self.chrome.click_element('button[data-control-name="share.post"]')
            return True

        except Exception as e:
            _logger.error(f"LinkedIn posting error: {e}")
            return False

    async def _post_to_facebook(self, content: Dict[str, Any]) -> bool:
        """Post content to Facebook."""
        try:
            await self.chrome.navigate('https://www.facebook.com')
            
            # Click create post
            await self.chrome.click_element('div[aria-label="Create"]')
            
            # Wait for post composer
            if not await self.chrome.wait_for_selector('div[role="textbox"][contenteditable="true"]'):
                return False

            # Input content
            await self.chrome.set_input_value(
                'div[role="textbox"][contenteditable="true"]',
                content['text']
            )

            # Handle media if present
            if content.get('media'):
                await self._handle_facebook_media(content['media'])

            # Post
            await self.chrome.click_element('div[aria-label="Post"]')
            return True

        except Exception as e:
            _logger.error(f"Facebook posting error: {e}")
            return False

    async def _handle_twitter_media(self, media_paths: List[str]):
        """Handle media upload for Twitter."""
        for media_path in media_paths[:4]:  # Twitter allows up to 4 media items
            if os.path.exists(media_path):
                await self.chrome.execute_script(f'''
                    const input = document.createElement('input');
                    input.type = 'file';
                    input.style.display = 'none';
                    document.body.appendChild(input);
                    input.click();
                ''')
                # Handle file selection dialog
                await self.chrome.wait_for_selector('input[type="file"]')
                await self.chrome.execute_script(f'document.querySelector(\'input[type="file"]\').value = "{media_path}"')

    async def _handle_linkedin_media(self, media_paths: List[str]):
        """Handle media upload for LinkedIn."""
        await self.chrome.click_element('button[aria-label="Add media"]')
        # Similar implementation to Twitter's media handling

    async def _handle_facebook_media(self, media_paths: List[str]):
        """Handle media upload for Facebook."""
        await self.chrome.click_element('div[aria-label="Photo/Video"]')
        # Similar implementation to Twitter's media handling

    async def close(self):
        """Close Chrome automation connection."""
        await self.chrome.close()