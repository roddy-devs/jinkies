"""
Configuration management for the Discord bot.
Loads environment variables and provides validation.
"""
import os
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class BotConfig:
    """Bot configuration from environment variables."""
    
    # Discord
    DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
    DISCORD_ALERT_CHANNEL_ID: int = int(os.getenv("DISCORD_ALERT_CHANNEL_ID", "0"))
    DISCORD_ALERT_CHANNEL_DEV_ID: int = int(os.getenv("DISCORD_ALERT_CHANNEL_DEV_ID", "0"))
    DISCORD_LOG_CHANNEL_ID: int = int(os.getenv("DISCORD_LOG_CHANNEL_ID", "0"))
    DISCORD_DEPLOY_CHANNEL_ID: int = int(os.getenv("DISCORD_DEPLOY_CHANNEL_ID", "0"))
    DISCORD_COPILOT_CHANNEL_ID: int = int(os.getenv("DISCORD_COPILOT_CHANNEL_ID", "0"))
    DISCORD_ALLOWED_ROLES: List[str] = os.getenv("DISCORD_ALLOWED_ROLES", "Admin,DevOps").split(",")
    
    # GitHub
    GITHUB_APP_ID: Optional[str] = os.getenv("GITHUB_APP_ID")
    GITHUB_PRIVATE_KEY: str = os.getenv("GITHUB_PRIVATE_KEY", "")
    GITHUB_REPO_OWNER: str = os.getenv("GITHUB_REPO_OWNER", "")
    GITHUB_REPO_NAME: str = os.getenv("GITHUB_REPO_NAME", "")
    DEFAULT_BASE_BRANCH: str = os.getenv("DEFAULT_BASE_BRANCH", "develop")
    
    # OpenAI (Optional - for AI-generated fix prompts)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # AWS
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    # CloudWatch
    CLOUDWATCH_LOG_GROUP_API: str = os.getenv("CLOUDWATCH_LOG_GROUP_API", "/aws/ec2/django-api")
    CLOUDWATCH_LOG_GROUP_CLOUDFRONT: str = os.getenv("CLOUDWATCH_LOG_GROUP_CLOUDFRONT", "/aws/cloudfront/access-logs")
    
    # Environment
    ENVIRONMENT_NAME: str = os.getenv("ENVIRONMENT_NAME", "production")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Bot settings
    MAX_LOG_LINES: int = int(os.getenv("MAX_LOG_LINES", "50"))
    LOG_TAIL_INTERVAL: int = int(os.getenv("LOG_TAIL_INTERVAL", "10"))
    ALERT_RETENTION_DAYS: int = int(os.getenv("ALERT_RETENTION_DAYS", "30"))
    MAX_MESSAGE_LENGTH: int = int(os.getenv("MAX_MESSAGE_LENGTH", "1900"))
    
    @classmethod
    def validate(cls) -> List[str]:
        """Validate required configuration."""
        errors = []
        
        if not cls.DISCORD_BOT_TOKEN:
            errors.append("DISCORD_BOT_TOKEN is required")
        
        if cls.DISCORD_ALERT_CHANNEL_ID == 0:
            errors.append("DISCORD_ALERT_CHANNEL_ID is required")
        
        if cls.DISCORD_LOG_CHANNEL_ID == 0:
            errors.append("DISCORD_LOG_CHANNEL_ID is required")
        
        if not cls.GITHUB_REPO_OWNER:
            errors.append("GITHUB_REPO_OWNER is required")
        
        if not cls.GITHUB_REPO_NAME:
            errors.append("GITHUB_REPO_NAME is required")
        
        return errors
    
    @classmethod
    def get_alert_channel_id(cls, environment: str = None) -> int:
        """Get the appropriate alert channel ID based on environment."""
        env = environment or cls.ENVIRONMENT_NAME
        
        if env.lower() in ["development", "dev", "local"]:
            return cls.DISCORD_ALERT_CHANNEL_DEV_ID or cls.DISCORD_ALERT_CHANNEL_ID
        
        return cls.DISCORD_ALERT_CHANNEL_ID
    
    @classmethod
    def get_alert_channel_id(cls, environment: str = None) -> int:
        """Get the appropriate alert channel ID based on environment."""
        env = environment or cls.ENVIRONMENT_NAME
        
        if env.lower() in ["development", "dev", "local"]:
            return cls.DISCORD_ALERT_CHANNEL_DEV_ID or cls.DISCORD_ALERT_CHANNEL_ID
        
        return cls.DISCORD_ALERT_CHANNEL_ID
    
    @classmethod
    def get_log_group_for_service(cls, service: str) -> Optional[str]:
        """Get CloudWatch log group for a service."""
        service_map = {
            "api": cls.CLOUDWATCH_LOG_GROUP_API,
            "django": cls.CLOUDWATCH_LOG_GROUP_API,
            "cloudfront": cls.CLOUDWATCH_LOG_GROUP_CLOUDFRONT,
        }
        return service_map.get(service.lower())


config = BotConfig()
