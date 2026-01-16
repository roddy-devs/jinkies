"""
Feature request and PR creation cog.
"""
import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional
from bot.config import config
from bot.services.github_service import GitHubService
from bot.services.ai_service import AIService
from bot.utils.discord_helpers import has_required_role, format_success_message, format_error_message

logger = logging.getLogger("jinkies.requests")


class RequestCommands(commands.Cog):
    """Commands for creating PRs from feature requests."""
    
    def __init__(self, bot):
        self.bot = bot
        self.github_service = GitHubService()
        self.ai_service = AIService()
    
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
            if not self.ai_service.client:
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

            response = self.ai_service.client.chat.completions.create(
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
            
            # Add Copilot comment
            pr.create_issue_comment("@copilot Please implement the feature described in the PR description.")
            
            await interaction.followup.send(format_success_message(f"Created draft PR: {pr.html_url}"))
            
        except Exception as e:
            logger.error(f"Error creating PR from request: {e}", exc_info=True)
            await interaction.followup.send(format_error_message(f"Error: {str(e)}"))


async def setup(bot: commands.Bot):
    """Load the cog."""
    await bot.add_cog(RequestCommands(bot))
