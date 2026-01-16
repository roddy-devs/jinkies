"""
Discord cog for alert-related commands.
"""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from bot.config import config
from bot.services.alert_store import AlertStore
from bot.services.github_service import GitHubService
from bot.utils.discord_helpers import (
    create_alert_embed,
    create_alert_buttons,
    has_required_role,
    format_error_message,
    format_success_message,
)


class AlertCommands(commands.Cog):
    """Commands for managing alerts."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.alert_store = AlertStore()
        self.github_service = GitHubService()
    
    @app_commands.command(name="alerts", description="List recent alerts")
    @app_commands.describe(
        limit="Number of alerts to show (default: 10)",
        unacknowledged_only="Show only unacknowledged alerts"
    )
    async def alerts(
        self,
        interaction: discord.Interaction,
        limit: Optional[int] = 10,
        unacknowledged_only: Optional[bool] = False
    ):
        """List recent alerts."""
        if not has_required_role(interaction):
            await interaction.response.send_message(
                format_error_message("You don't have permission to use this command."),
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        # Get alerts
        if unacknowledged_only:
            alerts = self.alert_store.get_recent_alerts(limit=limit, acknowledged=False)
        else:
            alerts = self.alert_store.get_recent_alerts(limit=limit)
        
        if not alerts:
            await interaction.followup.send("No alerts found.")
            return
        
        # Create embed
        embed = discord.Embed(
            title="📋 Recent Alerts",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        for alert in alerts:
            status = "✅" if alert.acknowledged else "🔴"
            value = (
                f"**Service**: {alert.service_name}\n"
                f"**Error**: {alert.exception_type}\n"
                f"**Time**: {alert.timestamp[:19]}\n"
                f"**Status**: {status} {'Acknowledged' if alert.acknowledged else 'Open'}"
            )
            embed.add_field(
                name=f"{alert.get_severity_emoji()} Alert {alert.get_short_id()}",
                value=value,
                inline=False
            )
        
        embed.set_footer(text=f"Showing {len(alerts)} alert(s)")
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="alert", description="View details of a specific alert")
    @app_commands.describe(alert_id="Alert ID (short or full)")
    async def alert(self, interaction: discord.Interaction, alert_id: str):
        """View alert details."""
        if not has_required_role(interaction):
            await interaction.response.send_message(
                format_error_message("You don't have permission to use this command."),
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        # Try to find alert (support both short and full IDs)
        alert = self.alert_store.get_alert(alert_id)
        
        if not alert:
            # Try to find by short ID
            recent_alerts = self.alert_store.get_recent_alerts(limit=100)
            for a in recent_alerts:
                if a.alert_id.startswith(alert_id):
                    alert = a
                    break
        
        if not alert:
            await interaction.followup.send(
                format_error_message(f"Alert not found: {alert_id}")
            )
            return
        
        # Create and send embed with buttons
        embed = create_alert_embed(alert)
        view = create_alert_buttons()
        
        # Store alert ID in view for button handlers
        view.alert_id = alert.alert_id
        
        await interaction.followup.send(embed=embed, view=view)
    
    @app_commands.command(name="ack", description="Acknowledge an alert")
    @app_commands.describe(alert_id="Alert ID to acknowledge")
    async def acknowledge(self, interaction: discord.Interaction, alert_id: str):
        """Acknowledge an alert."""
        if not has_required_role(interaction):
            await interaction.response.send_message(
                format_error_message("You don't have permission to use this command."),
                ephemeral=True
            )
            return
        
        # Find alert
        alert = self.alert_store.get_alert(alert_id)
        
        if not alert:
            # Try short ID
            recent_alerts = self.alert_store.get_recent_alerts(limit=100)
            for a in recent_alerts:
                if a.alert_id.startswith(alert_id):
                    alert = a
                    break
        
        if not alert:
            await interaction.response.send_message(
                format_error_message(f"Alert not found: {alert_id}"),
                ephemeral=True
            )
            return
        
        if alert.acknowledged:
            await interaction.response.send_message(
                format_error_message(f"Alert {alert.get_short_id()} is already acknowledged."),
                ephemeral=True
            )
            return
        
        # Acknowledge
        success = self.alert_store.acknowledge_alert(
            alert.alert_id,
            str(interaction.user)
        )
        
        if success:
            await interaction.response.send_message(
                format_success_message(f"Alert {alert.get_short_id()} acknowledged.")
            )
        else:
            await interaction.response.send_message(
                format_error_message("Failed to acknowledge alert."),
                ephemeral=True
            )
    
    @app_commands.command(name="create-pr", description="Create a GitHub PR from an alert")
    @app_commands.describe(
        alert_id="Alert ID",
        base_branch="Base branch for PR (default: develop)",
        fix_notes="Optional notes about the fix"
    )
    async def create_pr(
        self,
        interaction: discord.Interaction,
        alert_id: str,
        base_branch: Optional[str] = None,
        fix_notes: Optional[str] = None
    ):
        """Create a GitHub PR from an alert."""
        if not has_required_role(interaction):
            await interaction.response.send_message(
                format_error_message("You don't have permission to use this command."),
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        # Find alert
        alert = self.alert_store.get_alert(alert_id)
        
        if not alert:
            # Try short ID
            recent_alerts = self.alert_store.get_recent_alerts(limit=100)
            for a in recent_alerts:
                if a.alert_id.startswith(alert_id):
                    alert = a
                    break
        
        if not alert:
            await interaction.followup.send(
                format_error_message(f"Alert not found: {alert_id}")
            )
            return
        
        # Check if PR already exists
        if alert.github_pr_url:
            await interaction.followup.send(
                format_error_message(f"PR already exists for this alert: {alert.github_pr_url}")
            )
            return
        
        # Create PR
        try:
            pr_url = self.github_service.create_pr_from_alert(
                alert=alert,
                base_branch=base_branch,
                fix_notes=fix_notes
            )
            
            if pr_url:
                # Update alert with PR URL
                self.alert_store.update_github_links(alert.alert_id, pr_url=pr_url)
                
                await interaction.followup.send(
                    format_success_message(f"Created draft PR: {pr_url}")
                )
            else:
                await interaction.followup.send(
                    format_error_message("Failed to create PR. Check bot logs.")
                )
        
        except Exception as e:
            await interaction.followup.send(
                format_error_message(f"Error creating PR: {str(e)}")
            )
    
    @app_commands.command(name="create-issue", description="Create a GitHub issue from an alert")
    @app_commands.describe(alert_id="Alert ID")
    async def create_issue(self, interaction: discord.Interaction, alert_id: str):
        """Create a GitHub issue from an alert."""
        if not has_required_role(interaction):
            await interaction.response.send_message(
                format_error_message("You don't have permission to use this command."),
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        # Find alert
        alert = self.alert_store.get_alert(alert_id)
        
        if not alert:
            # Try short ID
            recent_alerts = self.alert_store.get_recent_alerts(limit=100)
            for a in recent_alerts:
                if a.alert_id.startswith(alert_id):
                    alert = a
                    break
        
        if not alert:
            await interaction.followup.send(
                format_error_message(f"Alert not found: {alert_id}")
            )
            return
        
        # Check if issue already exists
        if alert.github_issue_url:
            await interaction.followup.send(
                format_error_message(f"Issue already exists for this alert: {alert.github_issue_url}")
            )
            return
        
        # Create issue
        try:
            issue_url = self.github_service.create_issue_from_alert(alert)
            
            if issue_url:
                # Update alert with issue URL
                self.alert_store.update_github_links(alert.alert_id, issue_url=issue_url)
                
                await interaction.followup.send(
                    format_success_message(f"Created issue: {issue_url}")
                )
            else:
                await interaction.followup.send(
                    format_error_message("Failed to create issue. Check bot logs.")
                )
        
        except Exception as e:
            await interaction.followup.send(
                format_error_message(f"Error creating issue: {str(e)}")
            )
    
    @app_commands.command(name="request-pr", description="Create a PR from a feature request")
    @app_commands.describe(
        description="Describe what you want to build or fix",
        base_branch="Base branch for PR (default: develop)"
    )
    async def request_pr(
        self,
        interaction: discord.Interaction,
        description: str,
        base_branch: Optional[str] = None
    ):
        """Create a PR from a text description using AI."""
        if not has_required_role(interaction):
            await interaction.response.send_message(
                format_error_message("You don't have permission to use this command."),
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            from bot.services.ai_service import AIService
            ai_service = AIService()
            
            if not ai_service.client:
                await interaction.followup.send(
                    format_error_message("AI service not configured. Set OPENAI_API_KEY.")
                )
                return
            
            # Generate PR content
            system_prompt = """You are a senior software engineer. Create a PR title and implementation instructions."""
            user_prompt = f"""Create a PR for: {description}

Output format:
TITLE: [concise title]
BRANCH: [kebab-case-name]

[Implementation instructions]"""

            response = ai_service.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                max_tokens=1000,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            ai_response = response.choices[0].message.content
            lines = ai_response.split('\n')
            title = branch = None
            body_lines = []
            
            for line in lines:
                if line.startswith('TITLE:'):
                    title = line.replace('TITLE:', '').strip()
                elif line.startswith('BRANCH:'):
                    branch = line.replace('BRANCH:', '').strip()
                else:
                    body_lines.append(line)
            
            title = title or f"Feature: {description[:50]}"
            branch = branch or f"feature/request-{interaction.id}"
            body = '\n'.join(body_lines).strip()
            
            # Create PR
            base = base_branch or config.DEFAULT_BASE_BRANCH
            base_ref = self.github_service.repo.get_git_ref(f"heads/{base}")
            
            try:
                existing = self.github_service.repo.get_git_ref(f"heads/{branch}")
                existing.delete()
            except:
                pass
            
            self.github_service.repo.create_git_ref(f"refs/heads/{branch}", base_ref.object.sha)
            self.github_service.repo.create_file(
                f"IMPLEMENTATION_{interaction.id}.md",
                f"Add implementation instructions",
                f"# {title}\n\n{body}\n\n---\n*Requested by {interaction.user.name}*",
                branch=branch
            )
            
            pr = self.github_service.repo.create_pull(
                title=title,
                body=f"## Feature Request\n\n{body}\n\n### Requested By\n{interaction.user.mention}\n\n### Original Request\n> {description}",
                head=branch,
                base=base,
                draft=True
            )
            
            await interaction.followup.send(format_success_message(f"Created draft PR: {pr.html_url}"))
            
        except Exception as e:
            logger.error(f"Error creating PR from request: {e}", exc_info=True)
            await interaction.followup.send(format_error_message(f"Error: {str(e)}"))


async def setup(bot: commands.Bot):
    """Load the cog."""
    await bot.add_cog(AlertCommands(bot))
