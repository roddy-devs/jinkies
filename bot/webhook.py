"""
Webhook handler for receiving alerts from external systems.
This can be integrated with AWS SNS, Lambda, or custom alerting systems.
"""
from flask import Flask, request, jsonify
import discord
from discord import Webhook
import aiohttp
from datetime import datetime

from bot.config import config
from bot.models.alert import Alert
from bot.services.alert_store import AlertStore
from bot.utils.discord_helpers import create_alert_embed, create_alert_buttons

app = Flask(__name__)
alert_store = AlertStore()


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "jinkies-webhook"}), 200


@app.route("/webhook/alert", methods=["POST"])
async def receive_alert():
    """
    Receive alert webhook and post to Discord.
    
    Expected JSON payload:
    {
        "service_name": "api",
        "exception_type": "IntegrityError",
        "error_message": "duplicate key constraint",
        "stack_trace": "...",
        "related_logs": [...],
        "request_path": "/api/jobs/submit",
        "environment": "production",
        "instance_id": "i-0abc123",
        "commit_sha": "a1b2c3d",
        "severity": "ERROR"
    }
    """
    try:
        data = request.json
        
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
        
        # Post to Discord
        await post_alert_to_discord(alert)
        
        return jsonify({
            "status": "success",
            "alert_id": alert.alert_id
        }), 201
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


async def post_alert_to_discord(alert: Alert):
    """Post alert to Discord alert channel."""
    try:
        webhook_url = get_webhook_url(config.DISCORD_ALERT_CHANNEL_ID)
        
        if not webhook_url:
            print("No webhook URL configured for alert channel")
            return
        
        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(webhook_url, session=session)
            
            embed = create_alert_embed(alert)
            # Note: Buttons don't work with webhooks, need to use bot instance
            # For production, implement button handlers in the bot
            
            await webhook.send(embed=embed)
    
    except Exception as e:
        print(f"Error posting alert to Discord: {e}")


def get_webhook_url(channel_id: int) -> str:
    """
    Get webhook URL for a channel.
    In production, this should be stored in config or retrieved from Discord API.
    """
    # This is a placeholder - in production you would:
    # 1. Create a webhook in your Discord channel
    # 2. Store the webhook URL in environment variables
    # 3. Return it here
    return ""


@app.route("/webhook/sns", methods=["POST"])
async def receive_sns():
    """
    Receive AWS SNS notifications.
    Can be used for CloudWatch Alarms or custom notifications.
    """
    try:
        # Handle SNS message confirmation
        if request.headers.get("x-amz-sns-message-type") == "SubscriptionConfirmation":
            data = request.json
            # In production, you would confirm the subscription here
            return jsonify({"status": "subscription_pending"}), 200
        
        # Handle notification
        data = request.json
        message = data.get("Message", "")
        
        # Parse CloudWatch Alarm format
        if "AlarmName" in message:
            # Create alert from CloudWatch alarm
            alert = Alert(
                service_name="cloudwatch",
                exception_type="CloudWatch Alarm",
                error_message=data.get("AlarmName", ""),
                stack_trace=message,
                environment=config.ENVIRONMENT_NAME,
                severity="WARNING"
            )
            
            alert_store.save_alert(alert)
            await post_alert_to_discord(alert)
        
        return jsonify({"status": "success"}), 200
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == "__main__":
    # For development only - use gunicorn in production
    app.run(host="0.0.0.0", port=8080, debug=False)
