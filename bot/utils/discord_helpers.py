"""
Utility functions for Discord message formatting.
"""
import discord
from typing import List, Optional
from bot.models.alert import Alert, LogEntry
from bot.config import config


def create_alert_embed(alert: Alert) -> discord.Embed:
    """
    Create a rich embed for an alert.
    
    Args:
        alert: Alert object
    
    Returns:
        Discord Embed object
    """
    # Determine color based on severity
    color_map = {
        "INFO": discord.Color.blue(),
        "WARNING": discord.Color.gold(),
        "ERROR": discord.Color.red(),
        "CRITICAL": discord.Color.dark_red(),
    }
    color = color_map.get(alert.severity, discord.Color.red())
    
    # Create embed
    embed = discord.Embed(
        title=f"{alert.get_severity_emoji()} {alert.environment.upper()} {alert.service_name.upper()} ERROR",
        description=f"**{alert.exception_type}**: {alert.error_message[:200]}",
        color=color,
        timestamp=discord.utils.parse_time(alert.timestamp)
    )
    
    # Add fields
    embed.add_field(name="Alert ID", value=f"`{alert.get_short_id()}`", inline=True)
    embed.add_field(name="Severity", value=alert.severity, inline=True)
    embed.add_field(name="Service", value=alert.service_name, inline=True)
    
    if alert.request_path:
        embed.add_field(name="Endpoint", value=f"`{alert.request_path}`", inline=False)
    
    if alert.instance_id:
        embed.add_field(name="Instance", value=alert.instance_id, inline=True)
    
    if alert.commit_sha:
        embed.add_field(name="Commit", value=f"`{alert.commit_sha[:8]}`", inline=True)
    
    # Add stack trace (trimmed)
    if alert.stack_trace:
        stack_preview = alert.get_trimmed_stack_trace(10)
        if len(stack_preview) > 1000:
            stack_preview = stack_preview[:1000] + "..."
        embed.add_field(name="Stack Trace", value=f"```\n{stack_preview}\n```", inline=False)
    
    # Add recent logs
    if alert.related_logs:
        logs_preview = "\n".join(alert.get_trimmed_logs(3))
        if len(logs_preview) > 1000:
            logs_preview = logs_preview[:1000] + "..."
        embed.add_field(name="Recent Logs", value=f"```\n{logs_preview}\n```", inline=False)
    
    # Add status indicators
    if alert.acknowledged:
        embed.add_field(
            name="Status",
            value=f"✅ Acknowledged by {alert.acknowledged_by}",
            inline=False
        )
    
    if alert.github_pr_url:
        embed.add_field(name="GitHub PR", value=alert.github_pr_url, inline=False)
    
    if alert.github_issue_url:
        embed.add_field(name="GitHub Issue", value=alert.github_issue_url, inline=False)
    
    embed.set_footer(text=f"Alert ID: {alert.alert_id}")
    
    return embed


def create_alert_buttons() -> discord.ui.View:
    """
    Create interactive buttons for alert actions.
    
    Returns:
        Discord View with buttons
    """
    view = discord.ui.View(timeout=None)
    
    # Create PR button
    pr_button = discord.ui.Button(
        label="Create PR",
        style=discord.ButtonStyle.primary,
        emoji="🔧",
        custom_id="alert_create_pr"
    )
    
    # Create Issue button
    issue_button = discord.ui.Button(
        label="Create Issue",
        style=discord.ButtonStyle.secondary,
        emoji="🐛",
        custom_id="alert_create_issue"
    )
    
    # View Logs button
    logs_button = discord.ui.Button(
        label="View Logs",
        style=discord.ButtonStyle.secondary,
        emoji="📜",
        custom_id="alert_view_logs"
    )
    
    # Acknowledge button
    ack_button = discord.ui.Button(
        label="Acknowledge",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="alert_acknowledge"
    )
    
    view.add_item(pr_button)
    view.add_item(issue_button)
    view.add_item(logs_button)
    view.add_item(ack_button)
    
    return view


def format_logs_for_discord(logs: List[LogEntry], max_length: int = None) -> str:
    """
    Format log entries for Discord display.
    
    Args:
        logs: List of log entries
        max_length: Maximum message length
    
    Returns:
        Formatted string suitable for Discord
    """
    if not logs:
        return "No logs found."
    
    max_length = max_length or config.MAX_MESSAGE_LENGTH
    
    formatted = "```\n"
    for log in logs:
        line = log.format_for_discord() + "\n"
        
        # Check if adding this line would exceed max length
        if len(formatted) + len(line) + 3 > max_length:  # +3 for closing ```
            formatted += f"... ({len(logs) - logs.index(log)} more entries)\n"
            break
        
        formatted += line
    
    formatted += "```"
    return formatted


def create_log_embed(service: str, logs: List[LogEntry], filters: Optional[dict] = None) -> discord.Embed:
    """
    Create an embed for log display.
    
    Args:
        service: Service name
        logs: List of log entries
        filters: Applied filters
    
    Returns:
        Discord Embed
    """
    embed = discord.Embed(
        title=f"📜 Logs: {service}",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    
    # Add filter info
    if filters:
        filter_text = []
        if filters.get("level"):
            filter_text.append(f"Level: {filters['level']}")
        if filters.get("since"):
            filter_text.append(f"Since: {filters['since']}")
        if filters.get("limit"):
            filter_text.append(f"Limit: {filters['limit']}")
        
        if filter_text:
            embed.add_field(name="Filters", value=" | ".join(filter_text), inline=False)
    
    # Add log count
    embed.add_field(name="Entries", value=str(len(logs)), inline=True)
    
    return embed


def chunk_message(text: str, max_length: int = 1900) -> List[str]:
    """
    Split a long message into Discord-safe chunks.
    
    Args:
        text: Text to split
        max_length: Maximum length per chunk
    
    Returns:
        List of message chunks
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    for line in text.split("\n"):
        if len(current_chunk) + len(line) + 1 > max_length:
            chunks.append(current_chunk)
            current_chunk = line + "\n"
        else:
            current_chunk += line + "\n"
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def has_required_role(interaction: discord.Interaction) -> bool:
    """
    Check if user has required role for bot commands.
    
    Args:
        interaction: Discord interaction
    
    Returns:
        True if user has required role
    """
    if not interaction.user.roles:
        return False
    
    user_roles = [role.name for role in interaction.user.roles]
    allowed_roles = config.DISCORD_ALLOWED_ROLES
    
    return any(role in allowed_roles for role in user_roles)


def format_error_message(error: str) -> str:
    """Format error message for Discord."""
    return f"❌ **Error**: {error}"


def format_success_message(message: str) -> str:
    """Format success message for Discord."""
    return f"✅ **Success**: {message}"
