"""
Django views for Jinkies webhook integration.
"""
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# Import Jinkies components
import sys
import os
# Adjust path to import from bot directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from bot.models.alert import Alert
from bot.services.alert_store import AlertStore
from bot.config import config


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
    Receive alert from Django application.
    
    This endpoint receives alerts from your Django app's logging handler
    and stores them in the Jinkies alert database.
    
    Note: This is deprecated. Use direct API calls to Jinkies instead.
    
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
        
        return JsonResponse({
            "status": "success",
            "alert_id": alert.alert_id
        }, status=201)
    
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)
