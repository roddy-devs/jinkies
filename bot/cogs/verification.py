"""
Discord cog for user verification.
"""
import discord
from discord import app_commands
from discord.ext import commands
import requests
import os


class VerificationCommands(commands.Cog):
    """Commands for verifying users from Nomadic Influence platform."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api_url = os.getenv("NOMADIC_API_URL", "https://api.nomadicinfluence.com")
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle DM verification with PIN."""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Only handle DMs
        if not isinstance(message.channel, discord.DMChannel):
            return
        
        pin = message.content.strip()
        
        # Check if it looks like a PIN (6 digits)
        if not pin.isdigit() or len(pin) != 6:
            await message.author.send(
                "Please send your 6-digit verification PIN from https://nomadicinfluence.com/settings"
            )
            return
        
        try:
            # Call API to verify PIN
            response = requests.post(
                f"{self.api_url}/api/discord/verify-pin/",
                json={
                    "pin": pin,
                    "discord_user_id": str(message.author.id),
                    "discord_username": str(message.author)
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                user_data = data.get('user', {})
                tier = user_data.get('tier', 'creator')
                
                # Find user in all guilds and assign role
                verified_count = 0
                for guild in self.bot.guilds:
                    member = guild.get_member(message.author.id)
                    if not member:
                        continue
                    
                    creator_role = discord.utils.get(guild.roles, name="Creator")
                    creator_plus_role = discord.utils.get(guild.roles, name="Creator+")
                    
                    if not creator_role:
                        continue
                    
                    # Remove Nomad role if present
                    nomad_role = discord.utils.get(guild.roles, name="Nomad")
                    if nomad_role and nomad_role in member.roles:
                        await member.remove_roles(nomad_role)
                    
                    # Assign appropriate role
                    if tier == 'creator+' and creator_plus_role:
                        await member.add_roles(creator_plus_role)
                        role_name = "Creator+"
                    else:
                        await member.add_roles(creator_role)
                        role_name = "Creator"
                    
                    verified_count += 1
                
                if verified_count > 0:
                    await message.author.send(
                        f"✅ **Verification Successful!**\n\n"
                        f"Welcome, {user_data.get('first_name', 'Creator')}!\n"
                        f"You now have access to all community channels. Enjoy!"
                    )
                else:
                    await message.author.send(
                        "✅ PIN verified, but you're not in any servers I manage. Join the server first!"
                    )
                    
            elif response.status_code == 404:
                await message.author.send(
                    "❌ Invalid PIN. Generate a new one at https://nomadicinfluence.com/settings"
                )
            elif response.status_code == 400:
                error_msg = response.json().get('error', 'Unknown error')
                await message.author.send(f"❌ {error_msg}")
            else:
                await message.author.send(
                    "❌ Verification failed. Please try again later."
                )
                
        except Exception as e:
            await message.author.send(
                "❌ An error occurred. Please try again or use /verify in the server."
            )
            print(f"DM verification error: {e}")
    
    @app_commands.command(name="verify", description="Verify your Nomadic Influence account")
    @app_commands.describe(pin="6-digit PIN from your dashboard")
    async def verify(self, interaction: discord.Interaction, pin: str):
        """Verify user with PIN from platform."""
        await interaction.response.defer(ephemeral=True)
        
        # Validate PIN format
        if not pin.isdigit() or len(pin) != 6:
            await interaction.followup.send(
                "❌ Invalid PIN format. Please enter a 6-digit PIN from your dashboard.",
                ephemeral=True
            )
            return
        
        try:
            # Call API to verify PIN
            response = requests.post(
                f"{self.api_url}/api/discord/verify-pin/",
                json={
                    "pin": pin,
                    "discord_user_id": str(interaction.user.id),
                    "discord_username": str(interaction.user)
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                user_data = data.get('user', {})
                tier = user_data.get('tier', 'creator')
                
                # Get roles
                guild = interaction.guild
                creator_role = discord.utils.get(guild.roles, name="Creator")
                creator_plus_role = discord.utils.get(guild.roles, name="Creator+")
                
                if not creator_role:
                    await interaction.followup.send(
                        "❌ Server configuration error: Creator role not found. Please contact an admin.",
                        ephemeral=True
                    )
                    return
                
                # Assign appropriate role
                member = interaction.user
                
                # Remove Nomad role if they have it
                nomad_role = discord.utils.get(guild.roles, name="Nomad")
                if nomad_role and nomad_role in member.roles:
                    await member.remove_roles(nomad_role)
                
                # Assign Creator or Creator+ role
                if tier == 'creator+' and creator_plus_role:
                    await member.add_roles(creator_plus_role)
                    role_name = "Creator+"
                else:
                    await member.add_roles(creator_role)
                    role_name = "Creator"
                
                # Success message
                await interaction.followup.send(
                    f"✅ **Verification Successful!**\n\n"
                    f"Welcome, {user_data.get('first_name', 'Creator')}!\n"
                    f"You've been assigned the **{role_name}** role.\n\n"
                    f"You now have access to all community channels. Enjoy!",
                    ephemeral=True
                )
                
                # Log to admin channel (optional)
                log_channel_id = os.getenv("DISCORD_LOG_CHANNEL_ID")
                if log_channel_id:
                    log_channel = self.bot.get_channel(int(log_channel_id))
                    if log_channel:
                        embed = discord.Embed(
                            title="✅ New User Verified",
                            description=f"{interaction.user.mention} verified as {role_name}",
                            color=0x6BCB77
                        )
                        embed.add_field(name="Email", value=user_data.get('email', 'N/A'))
                        embed.add_field(name="Name", value=f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}")
                        embed.add_field(name="Tier", value=tier)
                        await log_channel.send(embed=embed)
                
            elif response.status_code == 404:
                await interaction.followup.send(
                    "❌ Invalid PIN. Please check your dashboard and try again.",
                    ephemeral=True
                )
            elif response.status_code == 400:
                error_msg = response.json().get('error', 'Unknown error')
                await interaction.followup.send(
                    f"❌ {error_msg}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ Verification failed. Please try again later or contact support.",
                    ephemeral=True
                )
                
        except requests.exceptions.RequestException as e:
            await interaction.followup.send(
                "❌ Connection error. Please try again later.",
                ephemeral=True
            )
            print(f"Verification API error: {e}")
        except Exception as e:
            await interaction.followup.send(
                "❌ An error occurred. Please contact an admin.",
                ephemeral=True
            )
            print(f"Verification error: {e}")


async def setup(bot: commands.Bot):
    """Load the verification cog."""
    await bot.add_cog(VerificationCommands(bot))
