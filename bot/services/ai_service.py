"""
AI service for generating fix prompts from alerts.
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
from bot.models.alert import Alert

logger = logging.getLogger("jinkies.ai")


class AIService:
    """Service for AI-powered fix prompt generation."""
    
    def __init__(self):
        """Initialize OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not configured - AI features disabled")
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key)
    
    def generate_fix_prompt(self, alert: Alert) -> Optional[str]:
        """
        Generate a structured fix prompt from an alert.
        
        Args:
            alert: Alert object with error details
            
        Returns:
            Markdown-formatted fix prompt for Copilot, or None if AI unavailable
        """
        if not self.client:
            logger.warning("OpenAI client not available")
            return None
        
        system_prompt = """You are a senior software engineer analyzing production errors and creating fix instructions for GitHub Copilot.

Your task is to:
1. Analyze the error details, stack trace, and context
2. Identify the root cause
3. Generate clear, actionable fix instructions
4. Provide implementation guidance

Output a structured markdown document that Copilot can use to implement the fix."""

        user_prompt = f"""Analyze this production error and generate fix instructions:

## Error Details
- **Service**: {alert.service_name}
- **Exception**: {alert.exception_type}
- **Message**: {alert.error_message}
- **Environment**: {alert.environment}
- **Timestamp**: {alert.timestamp}
- **Django Alert**: {alert.django_alert_id}

## Stack Trace
```
{alert.stack_trace or 'No stack trace available'}
```

## Request Context
- **Path**: {alert.request_path or 'N/A'}

## Additional Context
```json
{json.dumps(alert.additional_context, indent=2) if alert.additional_context else 'None'}
```

Generate a comprehensive fix prompt with:
1. Root cause analysis
2. Proposed solution
3. Implementation steps
4. Test cases to add
5. Edge cases to consider"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                max_tokens=2000,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            fix_prompt = response.choices[0].message.content
            logger.info(f"Generated fix prompt for alert {alert.get_short_id()}")
            return fix_prompt
            
        except Exception as e:
            logger.error(f"Failed to generate fix prompt: {e}", exc_info=True)
            return None
