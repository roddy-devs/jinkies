"""
Discord cog for log-related commands.

NOTE: CloudWatch integration is optional. If boto3 is not installed,
log commands will be disabled but other bot features will work.
"""
import discord
from discord import app_commands
from discord.ext import commands, tasks
from typing import Optional
from datetime import datetime, timezone

from bot.config import config

# Try to import CloudWatch service
try:
    from bot.services.cloudwatch import CloudWatchService
    CLOUDWATCH_AVAILABLE = True
except ImportError:
    CLOUDWATCH_AVAILABLE = False
    CloudWatchService = None

from bot.utils.discord_helpers import (
    format_logs_for_discord,
    create_log_embed,
    chunk_message,
    has_required_role,
    format_error_message,
    format_success_message,
)


class LogCommands(commands.Cog):
    """Commands for viewing and streaming logs."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if CLOUDWATCH_AVAILABLE:
            self.cloudwatch = CloudWatchService()
        else:
            self.cloudwatch = None
        self.active_tails = {}  # Track active tail sessions
    
    @app_commands.command(name="logs", description="Retrieve application logs")
    @app_commands.describe(
        service="Service to get logs from (api, cloudfront, etc.)",
        level="Filter by log level (INFO, WARNING, ERROR, CRITICAL)",
        limit="Number of log entries to retrieve (default: 50, max: 100)",
        since="Time window in minutes (default: 60)"
    )
    async def logs(
        self,
        interaction: discord.Interaction,
        service: str,
        level: Optional[str] = None,
        limit: Optional[int] = 50,
        since: Optional[int] = 60
    ):
        """Retrieve logs from CloudWatch."""
        # Check if CloudWatch is available
        if not CLOUDWATCH_AVAILABLE or self.cloudwatch is None:
            await interaction.response.send_message(
                format_error_message(
                    "CloudWatch integration is not available. "
                    "This feature requires boto3 to be installed. "
                    "Use Django webhooks for alerts instead."
                ),
                ephemeral=True
            )
            return
        
        # Check permissions
        if not has_required_role(interaction):
            await interaction.response.send_message(
                format_error_message("You don't have permission to use this command."),
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        # Get log group for service
        log_group = config.get_log_group_for_service(service)
        if not log_group:
            await interaction.followup.send(
                format_error_message(f"Unknown service: {service}. Available: api, cloudfront")
            )
            return
        
        # Validate parameters
        if limit > 100:
            limit = 100
        if limit < 1:
            limit = 1
        
        # Fetch logs
        try:
            logs = self.cloudwatch.get_logs(
                log_group=log_group,
                log_level=level,
                since_minutes=since,
                limit=limit
            )
            
            if not logs:
                await interaction.followup.send(
                    f"No logs found for **{service}** in the last {since} minutes."
                )
                return
            
            # Create embed
            filters = {
                "level": level,
                "since": f"{since}m",
                "limit": limit
            }
            embed = create_log_embed(service, logs, filters)
            
            # Format logs
            formatted_logs = format_logs_for_discord(logs)
            
            # Send in chunks if needed
            chunks = chunk_message(formatted_logs)
            await interaction.followup.send(embed=embed)
            
            for chunk in chunks:
                await interaction.followup.send(chunk)
        
        except Exception as e:
            await interaction.followup.send(
                format_error_message(f"Failed to retrieve logs: {str(e)}")
            )
    
    @app_commands.command(name="logs-tail", description="Stream logs in real-time")
    @app_commands.describe(
        service="Service to tail logs from",
        level="Filter by log level",
        duration="How long to tail in seconds (default: 60, max: 300)"
    )
    async def logs_tail(
        self,
        interaction: discord.Interaction,
        service: str,
        level: Optional[str] = None,
        duration: Optional[int] = 60
    ):
        """Start tailing logs."""
        # Check if CloudWatch is available
        if not CLOUDWATCH_AVAILABLE or self.cloudwatch is None:
            await interaction.response.send_message(
                format_error_message(
                    "CloudWatch integration is not available. "
                    "Log tailing requires boto3 to be installed."
                ),
                ephemeral=True
            )
            return
        
        # Check permissions
        if not has_required_role(interaction):
            await interaction.response.send_message(
                format_error_message("You don't have permission to use this command."),
                ephemeral=True
            )
            return
        
        # Get log group
        log_group = config.get_log_group_for_service(service)
        if not log_group:
            await interaction.response.send_message(
                format_error_message(f"Unknown service: {service}"),
                ephemeral=True
            )
            return
        
        # Validate duration
        if duration > 300:
            duration = 300
        
        # Start tailing
        session_id = f"{interaction.channel_id}_{service}"
        
        if session_id in self.active_tails:
            await interaction.response.send_message(
                format_error_message(f"Already tailing {service} in this channel. Use /logs-stop first."),
                ephemeral=True
            )
            return
        
        self.active_tails[session_id] = {
            "service": service,
            "log_group": log_group,
            "level": level,
            "channel_id": interaction.channel_id,
            "last_timestamp": None,
            "start_time": datetime.utcnow(),
            "duration": duration,
        }
        
        await interaction.response.send_message(
            format_success_message(f"Started tailing **{service}** logs for {duration} seconds. Use /logs-stop to stop.")
        )
        
        # Start the tail task if not already running
        if not self.tail_task.is_running():
            self.tail_task.start()
    
    @app_commands.command(name="logs-stop", description="Stop tailing logs")
    @app_commands.describe(service="Service to stop tailing")
    async def logs_stop(self, interaction: discord.Interaction, service: str):
        """Stop tailing logs."""
        session_id = f"{interaction.channel_id}_{service}"
        
        if session_id not in self.active_tails:
            await interaction.response.send_message(
                format_error_message(f"Not currently tailing {service} in this channel."),
                ephemeral=True
            )
            return
        
        del self.active_tails[session_id]
        
        await interaction.response.send_message(
            format_success_message(f"Stopped tailing **{service}** logs.")
        )
    
    @tasks.loop(seconds=10)
    async def tail_task(self):
        """Background task to fetch and send new logs."""
        if not self.active_tails:
            self.tail_task.stop()
            return
        
        sessions_to_remove = []
        
        for session_id, session_data in self.active_tails.items():
            try:
                # Check if duration exceeded
                elapsed = (datetime.utcnow() - session_data["start_time"]).total_seconds()
                if elapsed > session_data["duration"]:
                    sessions_to_remove.append(session_id)
                    
                    channel = self.bot.get_channel(session_data["channel_id"])
                    if channel:
                        await channel.send(f"⏱️ Tail session for **{session_data['service']}** has ended.")
                    continue
                
                # Fetch new logs
                logs = self.cloudwatch.tail_logs(
                    log_group=session_data["log_group"],
                    log_level=session_data["level"],
                    last_seen_timestamp=session_data["last_timestamp"]
                )
                
                if logs:
                    # Update last seen timestamp
                    last_log = logs[-1]
                    try:
                        # Parse timestamp and convert to milliseconds
                        log_timestamp = datetime.fromisoformat(last_log.timestamp.replace('Z', '+00:00'))
                        session_data["last_timestamp"] = int(log_timestamp.timestamp() * 1000)
                    except (ValueError, AttributeError) as e:
                        print(f"Error parsing log timestamp: {e}")
                        # Use current time as fallback
                        session_data["last_timestamp"] = int(datetime.now(timezone.utc).timestamp() * 1000)
                    
                    # Send logs to channel
                    channel = self.bot.get_channel(session_data["channel_id"])
                    if channel:
                        formatted = format_logs_for_discord(logs)
                        chunks = chunk_message(formatted)
                        for chunk in chunks:
                            await channel.send(chunk)
            
            except Exception as e:
                print(f"Error in tail task: {e}")
                sessions_to_remove.append(session_id)
        
        # Clean up finished sessions
        for session_id in sessions_to_remove:
            if session_id in self.active_tails:
                del self.active_tails[session_id]
    
    @tail_task.before_loop
    async def before_tail_task(self):
        """Wait for bot to be ready before starting task."""
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    """Load the cog."""
    await bot.add_cog(LogCommands(bot))
