"""
Webhook listener cog for receiving alerts from Django.
"""
import discord
from discord.ext import commands
from aiohttp import web
import asyncio
import logging
from datetime import datetime
from bot.config import config
from bot.services.alert_store import AlertStore
from bot.models.alert import Alert
from bot.utils.discord_helpers import format_alert_embed

logger = logging.getLogger("jinkies.webhook")


class WebhookListener(commands.Cog):
    """Cog for handling incoming webhook alerts."""
    
    def __init__(self, bot):
        self.bot = bot
        self.alert_store = AlertStore()
        self.app = web.Application()
        self.app.router.add_post('/alert', self.handle_alert)
        self.runner = None
        self.site = None
    
    async def cog_load(self):
        """Start webhook server when cog loads."""
        await self.start_server()
    
    async def cog_unload(self):
        """Stop webhook server when cog unloads."""
        await self.stop_server()
    
    async def start_server(self):
        """Start the webhook HTTP server."""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, '0.0.0.0', 8765)
            await self.site.start()
            logger.info("Webhook server started on http://0.0.0.0:8765")
        except Exception as e:
            logger.error(f"Failed to start webhook server: {e}")
    
    async def stop_server(self):
        """Stop the webhook HTTP server."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("Webhook server stopped")
    
    async def handle_alert(self, request):
        """Handle incoming alert webhook."""
        try:
            data = await request.json()
            
            # Create alert object
            alert = Alert(
                service_name=data.get('service_name', 'unknown'),
                exception_type=data.get('exception_type', 'UnknownError'),
                error_message=data.get('error_message', 'No message'),
                severity=data.get('severity', 'ERROR'),
                environment=data.get('environment', config.ENVIRONMENT_NAME),
                request_path=data.get('request_path'),
                stack_trace=data.get('stack_trace'),
                instance_id=data.get('instance_id'),
                commit_sha=data.get('commit_sha'),
                user_id=data.get('user_id'),
                related_logs=data.get('related_logs', []),
                additional_context=data.get('additional_context', {})
            )
            
            # Store alert
            self.alert_store.save_alert(alert)
            logger.info(f"Stored alert {alert.get_short_id()}: {alert.exception_type}")
            
            # Send to Discord
            await self.send_to_discord(alert)
            
            return web.json_response({
                'status': 'success',
                'alert_id': alert.alert_id
            })
            
        except Exception as e:
            logger.error(f"Error handling alert webhook: {e}")
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    async def send_to_discord(self, alert: Alert):
        """Send alert to Discord channel."""
        try:
            channel = self.bot.get_channel(config.DISCORD_ALERT_CHANNEL_ID)
            if not channel:
                logger.error(f"Alert channel {config.DISCORD_ALERT_CHANNEL_ID} not found")
                return
            
            embed = format_alert_embed(alert)
            await channel.send(embed=embed)
            logger.info(f"Sent alert {alert.get_short_id()} to Discord")
            
        except Exception as e:
            logger.error(f"Failed to send alert to Discord: {e}")


async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(WebhookListener(bot))
