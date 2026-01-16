"""
Webhook listener cog for receiving alerts from Django.
"""
import discord
from discord.ext import commands
from aiohttp import web
import asyncio
import logging
from datetime import datetime, timezone
from bot.config import config
from bot.services.alert_store import AlertStore
from bot.models.alert import Alert
from bot.utils.discord_helpers import create_alert_embed

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
            
            # Create alert object (only use fields that Alert model accepts)
            alert = Alert(
                django_alert_id=data.get('alert_id'),  # UUID from Django
                service_name=data.get('service_name', 'unknown'),
                exception_type=data.get('exception_type', 'UnknownError'),
                error_message=data.get('error_message', 'No message'),
                severity=data.get('severity', 'ERROR'),
                environment=data.get('environment', config.ENVIRONMENT_NAME),
                request_path=data.get('request_path'),
                stack_trace=data.get('stack_trace', ''),
                timestamp=data.get('timestamp', datetime.now(timezone.utc).isoformat()),
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
            
            embed = create_alert_embed(alert)
            message = await channel.send(embed=embed)
            
            # Add reaction emojis for quick actions
            await message.add_reaction('🔧')  # Create PR
            await message.add_reaction('🤖')  # Create PR + Assign to Copilot
            await message.add_reaction('✅')  # Acknowledge
            
            logger.info(f"Sent alert {alert.get_short_id()} to Discord")
            
        except Exception as e:
            logger.error(f"Failed to send alert to Discord: {e}")
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle reactions on alert messages."""
        # Ignore bot's own reactions
        if payload.user_id == self.bot.user.id:
            return
        
        # Only handle reactions in alert channel
        if payload.channel_id != config.DISCORD_ALERT_CHANNEL_ID:
            return
        
        try:
            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            
            # Check if message is from bot and has an embed (alert message)
            if message.author.id != self.bot.user.id or not message.embeds:
                return
            
            embed = message.embeds[0]
            
            # Extract alert ID from embed footer
            if not embed.footer or not embed.footer.text:
                return
            
            # Parse alert ID from footer (format: "Jinkies ID: xxx | Django ID: yyy")
            footer_text = embed.footer.text
            if 'Jinkies ID:' not in footer_text:
                return
            
            jinkies_id = footer_text.split('Jinkies ID:')[1].split('|')[0].strip()
            
            # Get alert from database
            alert = self.alert_store.get_alert(jinkies_id)
            if not alert:
                logger.warning(f"Alert {jinkies_id} not found for reaction")
                return
            
            # Handle different reactions
            emoji = str(payload.emoji)
            user = await self.bot.fetch_user(payload.user_id)
            
            if emoji == '🔧':
                # Create PR
                await self.handle_create_pr_reaction(alert, channel, user)
            elif emoji == '🤖':
                # Create PR and assign to Copilot
                await self.handle_create_pr_with_copilot_reaction(alert, channel, user)
            elif emoji == '📝':
                # Create Issue
                await self.handle_create_issue_reaction(alert, channel, user)
            elif emoji == '✅':
                # Acknowledge
                await self.handle_acknowledge_reaction(alert, channel, user)
                
        except Exception as e:
            logger.error(f"Error handling reaction: {e}", exc_info=True)
    
    async def handle_create_pr_reaction(self, alert, channel, user):
        """Handle PR creation from reaction."""
        from bot.services.github_service import GitHubService
        
        try:
            github_service = GitHubService()
            pr_url = github_service.create_pr_from_alert(alert)
            
            if pr_url:
                self.alert_store.update_github_links(alert.alert_id, pr_url=pr_url)
                await channel.send(f"✅ {user.mention} Created draft PR: {pr_url}")
            else:
                await channel.send(f"❌ {user.mention} Failed to create PR. Check bot logs.")
        except Exception as e:
            logger.error(f"Error creating PR from reaction: {e}")
            await channel.send(f"❌ {user.mention} Error creating PR: {str(e)}")
    
    async def handle_create_pr_with_copilot_reaction(self, alert, channel, user):
        """Handle PR creation with Copilot assignment from reaction."""
        from bot.services.github_service import GitHubService
        
        try:
            github_service = GitHubService()
            pr_url = github_service.create_pr_from_alert(alert)
            
            if pr_url:
                # Extract PR number from URL
                pr_number = int(pr_url.split('/')[-1])
                
                # Assign to Copilot (using a comment)
                try:
                    pr = github_service.repo.get_pull(pr_number)
                    pr.create_issue_comment("@copilot Please implement the fix described in the PR description.")
                    logger.info(f"Assigned PR #{pr_number} to Copilot")
                except Exception as comment_error:
                    logger.warning(f"Could not add copilot comment: {comment_error}")
                
                self.alert_store.update_github_links(alert.alert_id, pr_url=pr_url)
                await channel.send(f"✅ {user.mention} Created draft PR and assigned to Copilot: {pr_url}")
            else:
                await channel.send(f"❌ {user.mention} Failed to create PR. Check bot logs.")
        except Exception as e:
            logger.error(f"Error creating PR with Copilot from reaction: {e}")
            await channel.send(f"❌ {user.mention} Error creating PR: {str(e)}")
    
    async def handle_create_issue_reaction(self, alert, channel, user):
        """Handle issue creation from reaction."""
        from bot.services.github_service import GitHubService
        
        try:
            github_service = GitHubService()
            issue_url = github_service.create_issue_from_alert(alert)
            
            if issue_url:
                self.alert_store.update_github_links(alert.alert_id, issue_url=issue_url)
                await channel.send(f"✅ {user.mention} Created issue: {issue_url}")
            else:
                await channel.send(f"❌ {user.mention} Failed to create issue. Check bot logs.")
        except Exception as e:
            logger.error(f"Error creating issue from reaction: {e}")
            await channel.send(f"❌ {user.mention} Error creating issue: {str(e)}")
    
    async def handle_acknowledge_reaction(self, alert, channel, user):
        """Handle alert acknowledgment from reaction."""
        try:
            success = self.alert_store.acknowledge_alert(alert.alert_id, str(user))
            if success:
                await channel.send(f"✅ {user.mention} Acknowledged alert {alert.get_short_id()}")
            else:
                await channel.send(f"❌ {user.mention} Failed to acknowledge alert.")
        except Exception as e:
            logger.error(f"Error acknowledging alert from reaction: {e}")
            await channel.send(f"❌ {user.mention} Error: {str(e)}")


async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(WebhookListener(bot))
