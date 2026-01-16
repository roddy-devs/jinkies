"""
Main Discord bot for Jinkies monitoring system.
"""
import discord
from discord.ext import commands
import logging
import sys
from pathlib import Path

from bot.config import config

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log")
    ]
)

logger = logging.getLogger("jinkies")


class JinkiesBot(commands.Bot):
    """Custom bot class for Jinkies."""
    
    def __init__(self):
        """Initialize the bot."""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            description="Jinkies - AWS Monitoring & Alert Bot"
        )
    
    async def setup_hook(self):
        """Load cogs and sync commands."""
        logger.info("Loading cogs...")
        
        # Load cogs
        cogs = [
            "bot.cogs.logs",
            "bot.cogs.alerts",
            "bot.cogs.verification",
        ]
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")
        
        # Sync commands
        logger.info("Syncing slash commands...")
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
    async def on_ready(self):
        """Called when bot is ready."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")
        
        # Set status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="AWS CloudWatch logs"
            )
        )
        
        logger.info("Bot is ready!")
    
    async def on_member_join(self, member):
        """Auto-assign Nomad role when someone joins."""
        try:
            guild = member.guild
            nomad_role = discord.utils.get(guild.roles, name="Nomad")
            
            if nomad_role:
                await member.add_roles(nomad_role)
                logger.info(f"Assigned Nomad role to {member.name} ({member.id})")
            else:
                logger.warning(f"Nomad role not found in {guild.name}")
        except Exception as e:
            logger.error(f"Failed to assign Nomad role to {member.name}: {e}")
    
    async def on_command_error(self, ctx, error):
        """Handle command errors."""
        logger.error(f"Command error: {error}")
        
        if isinstance(error, commands.CommandNotFound):
            return
        
        await ctx.send(f"❌ An error occurred: {str(error)}")
    
    async def on_app_command_error(self, interaction: discord.Interaction, error):
        """Handle slash command errors."""
        logger.error(f"Slash command error: {error}")
        
        error_message = f"❌ An error occurred: {str(error)}"
        
        if interaction.response.is_done():
            await interaction.followup.send(error_message, ephemeral=True)
        else:
            await interaction.response.send_message(error_message, ephemeral=True)


def main():
    """Main entry point."""
    # Validate configuration
    errors = config.validate()
    if errors:
        logger.error("Configuration errors:")
        for error in errors:
            logger.error(f"  - {error}")
        sys.exit(1)
    
    logger.info("Configuration validated successfully")
    logger.info(f"Environment: {config.ENVIRONMENT_NAME}")
    logger.info(f"Alert channel: {config.DISCORD_ALERT_CHANNEL_ID}")
    logger.info(f"Log channel: {config.DISCORD_LOG_CHANNEL_ID}")
    
    # Create and run bot
    bot = JinkiesBot()
    
    try:
        bot.run(config.DISCORD_BOT_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
