"""
Deployment monitoring and triggering cog.
"""
import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
from typing import Optional
from github import Github
from bot.config import config
from bot.utils.discord_helpers import has_required_role

logger = logging.getLogger("jinkies.deploy")


class DeploymentCommands(commands.Cog):
    """Commands for deployment monitoring and triggering."""
    
    def __init__(self, bot):
        self.bot = bot
        self.github_client = Github(config.GITHUB_PRIVATE_KEY)
        self.repo = self.github_client.get_repo(f"{config.GITHUB_REPO_OWNER}/{config.GITHUB_REPO_NAME}")
        self.last_run_id = None
        self.monitor_deployments.start()
        self.monitor_copilot_prs.start()
    
    def cog_unload(self):
        """Stop monitoring when cog unloads."""
        self.monitor_deployments.cancel()
        self.monitor_copilot_prs.cancel()
    
    @tasks.loop(minutes=1)
    async def monitor_deployments(self):
        """Monitor GitHub Actions deployments and post updates."""
        try:
            # Get deploy channel
            deploy_channel_id = config.DISCORD_DEPLOY_CHANNEL_ID
            if not deploy_channel_id:
                return
            
            channel = self.bot.get_channel(deploy_channel_id)
            if not channel:
                return
            
            # Get latest workflow runs
            workflow = self.repo.get_workflow("deploy.yml")
            runs = workflow.get_runs()
            
            if runs.totalCount == 0:
                return
            
            latest_run = runs[0]
            
            # Skip if we've already reported this run
            if self.last_run_id == latest_run.id:
                return
            
            self.last_run_id = latest_run.id
            
            # Create embed based on status
            color_map = {
                "completed": discord.Color.green() if latest_run.conclusion == "success" else discord.Color.red(),
                "in_progress": discord.Color.blue(),
                "queued": discord.Color.light_grey(),
            }
            
            color = color_map.get(latest_run.status, discord.Color.grey())
            
            embed = discord.Embed(
                title=f"🚀 Deployment: {latest_run.head_branch}",
                description=latest_run.display_title,
                color=color,
                url=latest_run.html_url
            )
            
            embed.add_field(name="Status", value=latest_run.status.replace("_", " ").title(), inline=True)
            if latest_run.conclusion:
                embed.add_field(name="Result", value=latest_run.conclusion.title(), inline=True)
            embed.add_field(name="Commit", value=f"`{latest_run.head_sha[:8]}`", inline=True)
            embed.add_field(name="Triggered By", value=latest_run.actor.login, inline=True)
            
            embed.set_footer(text=f"Run #{latest_run.run_number}")
            embed.timestamp = latest_run.created_at
            
            await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error monitoring deployments: {e}", exc_info=True)
    
    @tasks.loop(minutes=2)
    async def monitor_copilot_prs(self):
        """Monitor PRs for Copilot completion."""
        try:
            # Get alert channel for notifications
            channel_id = config.DISCORD_ALERT_CHANNEL_ID
            if not channel_id:
                return
            
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return
            
            # Get open PRs
            pulls = self.repo.get_pulls(state='open', sort='updated', direction='desc')
            
            for pr in pulls[:10]:  # Check last 10 updated PRs
                # Check if PR has Copilot comment
                has_copilot_request = False
                copilot_responded = False
                
                for comment in pr.get_issue_comments():
                    if '@copilot' in comment.body and comment.user.login != 'copilot':
                        has_copilot_request = True
                    if comment.user.login == 'copilot':
                        copilot_responded = True
                
                # If Copilot responded and we haven't notified yet
                if has_copilot_request and copilot_responded:
                    # Check if we've already notified (using PR labels or reactions)
                    labels = [label.name for label in pr.labels]
                    if 'copilot-notified' not in labels:
                        # Send notification
                        embed = discord.Embed(
                            title="🤖 Copilot Completed Implementation",
                            description=pr.title,
                            color=discord.Color.green(),
                            url=pr.html_url
                        )
                        embed.add_field(name="PR", value=f"#{pr.number}", inline=True)
                        embed.add_field(name="Branch", value=pr.head.ref, inline=True)
                        
                        await channel.send(embed=embed)
                        
                        # Mark as notified
                        try:
                            pr.add_to_labels('copilot-notified')
                        except:
                            pass  # Label might not exist
                        
        except Exception as e:
            logger.error(f"Error monitoring Copilot PRs: {e}", exc_info=True)
    
    @monitor_deployments.before_loop
    async def before_monitor(self):
        """Wait for bot to be ready before monitoring."""
        await self.bot.wait_until_ready()
    
    @monitor_copilot_prs.before_loop
    async def before_copilot_monitor(self):
        """Wait for bot to be ready before monitoring."""
        await self.bot.wait_until_ready()
    
    @app_commands.command(name="deploy", description="Trigger a deployment")
    @app_commands.describe(
        ref="Branch name or commit hash to deploy",
        environment="Environment to deploy to (default: production)"
    )
    async def deploy(
        self,
        interaction: discord.Interaction,
        ref: str,
        environment: Optional[str] = "production"
    ):
        """Trigger a deployment via GitHub Actions."""
        if not has_required_role(interaction):
            await interaction.response.send_message(
                "❌ Error: You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # Trigger workflow dispatch
            workflow = self.repo.get_workflow("deploy.yml")
            success = workflow.create_dispatch(
                ref=ref,
                inputs={"environment": environment}
            )
            
            if success:
                embed = discord.Embed(
                    title="🚀 Deployment Triggered",
                    description=f"Deploying `{ref}` to **{environment}**",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Triggered By", value=interaction.user.mention, inline=True)
                embed.add_field(name="Repository", value=f"{config.GITHUB_REPO_OWNER}/{config.GITHUB_REPO_NAME}", inline=True)
                embed.set_footer(text="Check deployment status in the deploy channel")
                
                await interaction.followup.send(embed=embed)
                
                # Also post to deploy channel
                deploy_channel_id = config.DISCORD_DEPLOY_CHANNEL_ID
                if deploy_channel_id:
                    deploy_channel = self.bot.get_channel(deploy_channel_id)
                    if deploy_channel:
                        await deploy_channel.send(f"🚀 {interaction.user.mention} triggered deployment of `{ref}` to **{environment}**")
            else:
                await interaction.followup.send("❌ Failed to trigger deployment. Check bot logs.")
                
        except Exception as e:
            logger.error(f"Error triggering deployment: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error: {str(e)}")


async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(DeploymentCommands(bot))
