"""
Django views for Jinkies webhook integration.
"""
import json
import asyncio
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import aiohttp
from discord import Webhook

# Import Jinkies components
import sys
import os
# Adjust path to import from bot directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from bot.models.alert import Alert
from bot.services.alert_store import AlertStore
from bot.config import config
from bot.utils.discord_helpers import create_alert_embed


# Initialize alert store
alert_store = AlertStore()


@csrf_exempt
@require_http_methods(["GET"])
def health(request):
    """Health check endpoint."""
    return JsonResponse({"status": "healthy", "service": "jinkies-webhook"})


@csrf_exempt
@require_http_methods(["POST"])
def receive_alert(request):
    """
    Receive alert from Django application and forward to Discord.
    
    This endpoint receives alerts from your Django app's logging handler
    and stores them in the Jinkies alert database, then forwards to Discord.
    
    Expected JSON payload:
    {
        "service_name": "api",
        "exception_type": "IntegrityError",
        "error_message": "duplicate key constraint",
        "stack_trace": "...",
        "related_logs": [...],
        "request_path": "/api/jobs/submit",
        "environment": "production",
        "instance_id": "server-01",
        "commit_sha": "a1b2c3d",
        "severity": "ERROR"
    }
    """
    try:
        data = json.loads(request.body)
        
        # Create alert object
        alert = Alert(
            service_name=data.get("service_name", "unknown"),
            exception_type=data.get("exception_type", ""),
            error_message=data.get("error_message", ""),
            stack_trace=data.get("stack_trace", ""),
            related_logs=data.get("related_logs", []),
            request_path=data.get("request_path"),
            environment=data.get("environment", config.ENVIRONMENT_NAME),
            instance_id=data.get("instance_id"),
            commit_sha=data.get("commit_sha"),
            severity=data.get("severity", "ERROR"),
            additional_context=data.get("additional_context", {})
        )
        
        # Save alert to store
        alert_store.save_alert(alert)
        
        # Post to Discord (run in background)
        try:
            asyncio.run(post_alert_to_discord(alert))
        except Exception as e:
            print(f"Error posting to Discord: {e}")
        
        return JsonResponse({
            "status": "success",
            "alert_id": alert.alert_id
        }, status=201)
    
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)


async def post_alert_to_discord(alert: Alert):
    """
    Post alert to Discord via webhook.
    
    Uses Discord webhook to send alert without requiring the bot to be running.
    The webhook URL should be configured in your Discord channel settings.
    """
    try:
        # Get webhook URL from environment
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
        
        if not webhook_url:
            print("DISCORD_WEBHOOK_URL not configured")
            return
        
        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(webhook_url, session=session)
            embed = create_alert_embed(alert)
            await webhook.send(embed=embed)
            print(f"Alert {alert.get_short_id()} sent to Discord")
    
    except Exception as e:
        print(f"Error posting alert to Discord: {e}")
