"""
Deployment monitoring and triggering cog.
"""
import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
import asyncio
from typing import Optional
from github import Github
from bot.config import config
from bot.utils.discord_helpers import has_required_role
from bot.services.deploy_executor import DeploymentExecutor
from bot.services.deployment_store import DeploymentStore, Deployment

logger = logging.getLogger("jinkies.deploy")


class DeploymentCommands(commands.Cog):
    """Commands for deployment monitoring and triggering."""
    
    def __init__(self, bot):
        self.bot = bot
        self.github_client = Github(config.GITHUB_PRIVATE_KEY)
        self.repo = self.github_client.get_repo(f"{config.GITHUB_REPO_OWNER}/{config.GITHUB_REPO_NAME}")
        self.last_run_id = None
        
        # Initialize deployment store
        self.deployment_store = DeploymentStore("deployments.db")
        
        # Initialize deployment executor if configured
        self.executor = None
        if hasattr(config, 'DEPLOY_REPO_PATH') and hasattr(config, 'DEPLOY_SSH_KEY'):
            self.executor = DeploymentExecutor(
                repo_path=config.DEPLOY_REPO_PATH,
                ssh_key_path=config.DEPLOY_SSH_KEY,
                ec2_host=config.DEPLOY_EC2_HOST,
                ec2_user=getattr(config, 'DEPLOY_EC2_USER', 'ubuntu')
            )
            logger.info("Deployment executor initialized")
        else:
            logger.warning("Deployment executor not configured - will use GitHub Actions only")
        
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
            # Get copilot channel for notifications
            channel_id = config.DISCORD_COPILOT_CHANNEL_ID
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
    
    @app_commands.command(name="deploy", description="Deploy develop branch to production")
    @app_commands.describe(
        method="Deployment method: 'direct' (run locally) or 'github' (GitHub Actions)"
    )
    async def deploy(
        self,
        interaction: discord.Interaction,
        method: Optional[str] = None
    ):
        """Trigger a deployment via direct execution or GitHub Actions."""
        # Defer immediately to avoid timeout
        await interaction.response.defer()
        
        if not has_required_role(interaction):
            await interaction.followup.send(
                "❌ Error: You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        # Always deploy develop
        ref = "develop"
        method = method or "direct"
        
        # Get deploy channel
        deploy_channel_id = config.DISCORD_DEPLOY_CHANNEL_ID
        deploy_channel = self.bot.get_channel(deploy_channel_id) if deploy_channel_id else None
        
        # Create temporary deployment channel
        temp_channel = None
        category_id = 1461209527729786890
        category = self.bot.get_channel(category_id)
        
        try:
            if method == "direct" and self.executor:
                # Create deployment record
                deployment = Deployment(
                    branch=ref,
                    triggered_by=f"{interaction.user.name}#{interaction.user.discriminator}",
                    status="in_progress",
                    method="direct"
                )
                deployment_id = self.deployment_store.save_deployment(deployment)
                deployment.id = deployment_id
                
                # Create temporary channel for this deployment
                if category:
                    import datetime
                    timestamp = datetime.datetime.now().strftime("%H%M%S")
                    temp_channel = await category.create_text_channel(
                        name=f"deploy-{ref}-{timestamp}",
                        topic=f"Deployment #{deployment_id} of {ref} by {interaction.user.name}"
                    )
                    deployment.discord_channel_id = str(temp_channel.id)
                    self.deployment_store.update_deployment(deployment)
                
                # Direct deployment execution
                embed = discord.Embed(
                    title="🚀 Deployment Started",
                    description=f"Deploying `{ref}` directly...",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Triggered By", value=interaction.user.mention, inline=True)
                embed.add_field(name="Method", value="Direct Execution", inline=True)
                if temp_channel:
                    embed.add_field(name="Logs", value=temp_channel.mention, inline=True)
                embed.set_footer(text="This may take 5-10 minutes...")
                
                await interaction.followup.send(embed=embed)
                
                # Post to deploy channel
                if deploy_channel:
                    await deploy_channel.send(
                        f"🚀 {interaction.user.mention} started deployment of `{ref}`",
                        embed=embed
                    )
                
                # Execute deployment
                result = await self.executor.deploy(branch=ref)
                
                # Update deployment record
                from datetime import datetime
                deployment.completed_at = datetime.utcnow()
                deployment.duration_seconds = int((deployment.completed_at - deployment.started_at).total_seconds())
                deployment.output_logs = result.get("output", "")
                deployment.frontend_deployed = True  # Assume both deployed if successful
                deployment.backend_deployed = True
                
                if result["success"]:
                    deployment.status = "success"
                    
                    # Extract CloudFront invalidation ID from logs
                    if "Invalidation created:" in deployment.output_logs:
                        import re
                        match = re.search(r'Invalidation created: ([A-Z0-9]+)', deployment.output_logs)
                        if match:
                            deployment.cloudfront_invalidation_id = match.group(1)
                    
                    self.deployment_store.update_deployment(deployment)
                    success_embed = discord.Embed(
                        title="✅ Deployment Successful",
                        description=f"Successfully deployed `{ref}`",
                        color=discord.Color.green()
                    )
                    success_embed.add_field(name="Deployment ID", value=f"#{deployment.id}", inline=True)
                    success_embed.add_field(name="Branch", value=ref, inline=True)
                    success_embed.add_field(name="Duration", value=f"{deployment.duration_seconds}s", inline=True)
                    success_embed.add_field(name="Triggered By", value=interaction.user.mention, inline=True)
                    
                    await interaction.followup.send(embed=success_embed)
                    
                    # Post success to deploy channel
                    if deploy_channel:
                        await deploy_channel.send(
                            f"✅ Deployment of `{ref}` completed successfully",
                            embed=success_embed
                        )
                    
                    # Post full logs to temporary channel
                    if temp_channel:
                        output = result["output"]
                        if output:
                            log_chunks = [output[i:i+1900] for i in range(0, len(output), 1900)]
                            for chunk in log_chunks[:10]:  # Max 10 chunks
                                await temp_channel.send(f"```\n{chunk}\n```")
                        
                        # Delete channel after 30 seconds
                        await asyncio.sleep(30)
                        await temp_channel.delete(reason="Deployment completed successfully")
                else:
                    deployment.status = "failed"
                    deployment.error_message = result.get("error", "Unknown error")
                    self.deployment_store.update_deployment(deployment)
                    
                    error_embed = discord.Embed(
                        title="❌ Deployment Failed",
                        description=f"Failed to deploy `{ref}`",
                        color=discord.Color.red()
                    )
                    error_embed.add_field(name="Error", value=f"```\n{result['error'][:1000]}\n```", inline=False)
                    if temp_channel:
                        error_embed.add_field(name="Logs", value=f"Check {temp_channel.mention} for details", inline=False)
                    
                    await interaction.followup.send(embed=error_embed)
                    
                    # Post error to deploy channel
                    if deploy_channel:
                        await deploy_channel.send(
                            f"❌ Deployment of `{ref}` failed",
                            embed=error_embed
                        )
                    
                    # Post error logs to temporary channel (keep it for debugging)
                    if temp_channel:
                        await temp_channel.send(f"**Error:**\n```\n{result['error']}\n```")
                    
            elif method == "github":
                # GitHub Actions deployment
                workflow = self.repo.get_workflow("deploy.yml")
                success = workflow.create_dispatch(
                    ref=ref,
                    inputs={}
                )
                
                if success:
                    embed = discord.Embed(
                        title="🚀 Deployment Triggered",
                        description=f"Deploying `{ref}` via GitHub Actions",
                        color=discord.Color.blue()
                    )
                    embed.add_field(name="Triggered By", value=interaction.user.mention, inline=True)
                    embed.add_field(name="Method", value="GitHub Actions", inline=True)
                    embed.set_footer(text="Check deployment status in the deploy channel")
                    
                    await interaction.followup.send(embed=embed)
                    
                    if deploy_channel:
                        await deploy_channel.send(
                            f"🚀 {interaction.user.mention} triggered GitHub Actions deployment of `{ref}`"
                        )
                else:
                    await interaction.followup.send("❌ Failed to trigger GitHub Actions deployment.")
            else:
                await interaction.followup.send(
                    "❌ Direct deployment not configured. Use `method='github'` for GitHub Actions."
                )
                
        except Exception as e:
            logger.error(f"Error triggering deployment: {e}", exc_info=True)
            error_msg = f"❌ Error: {str(e)}"
            await interaction.followup.send(error_msg)
            if deploy_channel:
                await deploy_channel.send(error_msg)
            # Keep temp channel on error for debugging
    
    @app_commands.command(name="deploy-status", description="Check deployment status")
    async def deploy_status(self, interaction: discord.Interaction):
        """Check current deployment status on production."""
        if not has_required_role(interaction):
            await interaction.response.send_message(
                "❌ Error: You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            if not self.executor:
                await interaction.followup.send("❌ Direct deployment not configured.")
                return
            
            status = await self.executor.get_deployment_status()
            
            if "error" in status:
                embed = discord.Embed(
                    title="❌ Error Getting Status",
                    description=status["error"],
                    color=discord.Color.red()
                )
            else:
                color = discord.Color.green() if status.get("is_running") else discord.Color.orange()
                embed = discord.Embed(
                    title="📊 Deployment Status",
                    color=color
                )
                
                embed.add_field(
                    name="Service Status",
                    value="🟢 Running" if status.get("is_running") else "🔴 Stopped",
                    inline=True
                )
                
                if "last_commit" in status:
                    commit = status["last_commit"]
                    embed.add_field(name="Last Commit", value=f"`{commit['hash']}`", inline=True)
                    embed.add_field(name="Author", value=commit["author"], inline=True)
                    embed.add_field(name="Time", value=commit["time_ago"], inline=True)
                    embed.add_field(name="Message", value=commit["message"], inline=False)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting deployment status: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error: {str(e)}")


async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(DeploymentCommands(bot))
