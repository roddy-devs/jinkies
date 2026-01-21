"""
Discord commands for CRUD operations on Nomadic Influence models.
"""
import discord
from discord import app_commands
from discord.ext import commands
import requests
from typing import Optional
import logging

from bot.config import config

logger = logging.getLogger(__name__)


class NomadCRUD(commands.Cog):
    """CRUD operations for Nomadic Influence models."""
    
    def __init__(self, bot):
        self.bot = bot
        self.api_base = config.NOMADIC_API_URL
        self.headers = {"X-API-Key": config.NOMADIC_API_KEY}
    
    # ==================== USER COMMANDS ====================
    
    @app_commands.command(name="user-get", description="Get user details by email or ID")
    @app_commands.describe(
        email="User email address",
        user_id="User ID (UUID)"
    )
    async def user_get(
        self, 
        interaction: discord.Interaction,
        email: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """Get user details."""
        await interaction.response.defer()
        
        if not email and not user_id:
            await interaction.followup.send("❌ Provide either email or user_id")
            return
        
        try:
            # Search by email or ID
            params = {"email": email} if email else {"id": user_id}
            response = requests.get(f"{self.api_base}/admin/users/", params=params, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                user = response.json()
                embed = discord.Embed(title="👤 User Details", color=discord.Color.blue())
                embed.add_field(name="ID", value=user.get("id", "N/A"), inline=False)
                embed.add_field(name="Email", value=user.get("email", "N/A"), inline=True)
                embed.add_field(name="Name", value=f"{user.get('first_name', '')} {user.get('last_name', '')}", inline=True)
                embed.add_field(name="Is Creator", value="✅" if user.get("is_creator") else "❌", inline=True)
                embed.add_field(name="Is Business", value="✅" if user.get("is_business") else "❌", inline=True)
                embed.add_field(name="Created", value=user.get("created_at", "N/A")[:10], inline=True)
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f"❌ User not found: {response.text}")
        
        except Exception as e:
            logger.exception(f"Error getting user: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    @app_commands.command(name="user-update", description="Update user details")
    @app_commands.describe(
        email="User email address",
        first_name="First name",
        last_name="Last name",
        is_creator="Set creator status",
        is_business="Set business status"
    )
    async def user_update(
        self,
        interaction: discord.Interaction,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        is_creator: Optional[bool] = None,
        is_business: Optional[bool] = None
    ):
        """Update user details."""
        await interaction.response.defer()
        
        try:
            data = {}
            if first_name: data["first_name"] = first_name
            if last_name: data["last_name"] = last_name
            if is_creator is not None: data["is_creator"] = is_creator
            if is_business is not None: data["is_business"] = is_business
            
            response = requests.patch(
                f"{self.api_base}/admin/users/{email}/",
                json=data,
                timeout=10, headers=self.headers
            )
            
            if response.status_code == 200:
                await interaction.followup.send(f"✅ User `{email}` updated successfully")
            else:
                await interaction.followup.send(f"❌ Failed to update user: {response.text}")
        
        except Exception as e:
            logger.exception(f"Error updating user: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    @app_commands.command(name="user-delete", description="Delete a user")
    @app_commands.describe(email="User email address")
    async def user_delete(self, interaction: discord.Interaction, email: str):
        """Delete a user."""
        await interaction.response.defer()
        
        try:
            response = requests.delete(f"{self.api_base}/admin/users/{email}/", headers=self.headers, timeout=10)
            
            if response.status_code == 204:
                await interaction.followup.send(f"✅ User `{email}` deleted successfully")
            else:
                await interaction.followup.send(f"❌ Failed to delete user: {response.text}")
        
        except Exception as e:
            logger.exception(f"Error deleting user: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    # ==================== BUSINESS COMMANDS ====================
    
    @app_commands.command(name="business-get", description="Get business details")
    @app_commands.describe(business_id="Business ID (UUID)")
    async def business_get(self, interaction: discord.Interaction, business_id: str):
        """Get business details."""
        await interaction.response.defer()
        
        try:
            response = requests.get(f"{self.api_base}/admin/businesses/{business_id}/", headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                business = response.json()
                embed = discord.Embed(title="🏢 Business Details", color=discord.Color.green())
                embed.add_field(name="ID", value=business.get("id", "N/A"), inline=False)
                embed.add_field(name="Name", value=business.get("name", "N/A"), inline=True)
                embed.add_field(name="Type", value=business.get("business_type", "N/A"), inline=True)
                embed.add_field(name="Owner", value=business.get("owner_email", "N/A"), inline=True)
                embed.add_field(name="Website", value=business.get("website", "N/A"), inline=True)
                embed.add_field(name="Created", value=business.get("created_at", "N/A")[:10], inline=True)
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f"❌ Business not found: {response.text}")
        
        except Exception as e:
            logger.exception(f"Error getting business: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    @app_commands.command(name="business-update", description="Update business details")
    @app_commands.describe(
        business_id="Business ID (UUID)",
        name="Business name",
        website="Website URL",
        description="Business description"
    )
    async def business_update(
        self,
        interaction: discord.Interaction,
        business_id: str,
        name: Optional[str] = None,
        website: Optional[str] = None,
        description: Optional[str] = None
    ):
        """Update business details."""
        await interaction.response.defer()
        
        try:
            data = {}
            if name: data["name"] = name
            if website: data["website"] = website
            if description: data["description"] = description
            
            response = requests.patch(
                f"{self.api_base}/admin/businesses/{business_id}/",
                json=data,
                timeout=10, headers=self.headers
            )
            
            if response.status_code == 200:
                await interaction.followup.send(f"✅ Business updated successfully")
            else:
                await interaction.followup.send(f"❌ Failed to update business: {response.text}")
        
        except Exception as e:
            logger.exception(f"Error updating business: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    @app_commands.command(name="business-delete", description="Delete a business")
    @app_commands.describe(business_id="Business ID (UUID)")
    async def business_delete(self, interaction: discord.Interaction, business_id: str):
        """Delete a business."""
        await interaction.response.defer()
        
        try:
            response = requests.delete(f"{self.api_base}/admin/businesses/{business_id}/", headers=self.headers, timeout=10)
            
            if response.status_code == 204:
                await interaction.followup.send(f"✅ Business deleted successfully")
            else:
                await interaction.followup.send(f"❌ Failed to delete business: {response.text}")
        
        except Exception as e:
            logger.exception(f"Error deleting business: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    # ==================== CREATOR PROFILE COMMANDS ====================
    
    @app_commands.command(name="creator-get", description="Get creator profile details")
    @app_commands.describe(profile_id="Creator Profile ID (UUID)")
    async def creator_get(self, interaction: discord.Interaction, profile_id: str):
        """Get creator profile details."""
        await interaction.response.defer()
        
        try:
            response = requests.get(f"{self.api_base}/admin/creator-profiles/{profile_id}/", headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                profile = response.json()
                embed = discord.Embed(title="🎨 Creator Profile", color=discord.Color.purple())
                embed.add_field(name="ID", value=profile.get("id", "N/A"), inline=False)
                embed.add_field(name="Display Name", value=profile.get("display_name", "N/A"), inline=True)
                embed.add_field(name="User", value=profile.get("user_email", "N/A"), inline=True)
                embed.add_field(name="Primary", value="✅" if profile.get("is_primary") else "❌", inline=True)
                embed.add_field(name="Instagram", value=profile.get("instagram", "N/A"), inline=True)
                embed.add_field(name="YouTube", value=profile.get("youtube", "N/A"), inline=True)
                embed.add_field(name="Created", value=profile.get("created_at", "N/A")[:10], inline=True)
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f"❌ Creator profile not found: {response.text}")
        
        except Exception as e:
            logger.exception(f"Error getting creator profile: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    @app_commands.command(name="creator-update", description="Update creator profile")
    @app_commands.describe(
        profile_id="Creator Profile ID (UUID)",
        display_name="Display name",
        bio="Bio/description",
        instagram="Instagram handle",
        youtube="YouTube channel"
    )
    async def creator_update(
        self,
        interaction: discord.Interaction,
        profile_id: str,
        display_name: Optional[str] = None,
        bio: Optional[str] = None,
        instagram: Optional[str] = None,
        youtube: Optional[str] = None
    ):
        """Update creator profile."""
        await interaction.response.defer()
        
        try:
            data = {}
            if display_name: data["display_name"] = display_name
            if bio: data["bio"] = bio
            if instagram: data["instagram"] = instagram
            if youtube: data["youtube"] = youtube
            
            response = requests.patch(
                f"{self.api_base}/admin/creator-profiles/{profile_id}/",
                json=data,
                timeout=10, headers=self.headers
            )
            
            if response.status_code == 200:
                await interaction.followup.send(f"✅ Creator profile updated successfully")
            else:
                await interaction.followup.send(f"❌ Failed to update profile: {response.text}")
        
        except Exception as e:
            logger.exception(f"Error updating creator profile: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    @app_commands.command(name="creator-delete", description="Delete a creator profile")
    @app_commands.describe(profile_id="Creator Profile ID (UUID)")
    async def creator_delete(self, interaction: discord.Interaction, profile_id: str):
        """Delete a creator profile."""
        await interaction.response.defer()
        
        try:
            response = requests.delete(f"{self.api_base}/admin/creator-profiles/{profile_id}/", headers=self.headers, timeout=10)
            
            if response.status_code == 204:
                await interaction.followup.send(f"✅ Creator profile deleted successfully")
            else:
                await interaction.followup.send(f"❌ Failed to delete profile: {response.text}")
        
        except Exception as e:
            logger.exception(f"Error deleting creator profile: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}")


async def setup(bot):
    await bot.add_cog(NomadCRUD(bot))
