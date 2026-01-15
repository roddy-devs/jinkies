"""
Example Django logging configuration for integration with Jinkies.

Add this to your Django settings.py file.
"""

import os
import logging
import json
import requests
from datetime import datetime

# Jinkies webhook URL (set this in your environment)
JINKIES_WEBHOOK_URL = os.getenv("JINKIES_WEBHOOK_URL", "http://localhost:8080/webhook/alert")


class JinkiesAlertHandler(logging.Handler):
    """Custom logging handler that sends ERROR and CRITICAL logs to Jinkies."""
    
    def __init__(self, webhook_url=None):
        super().__init__()
        self.webhook_url = webhook_url or JINKIES_WEBHOOK_URL
    
    def emit(self, record):
        """Send log record to Jinkies webhook."""
        if record.levelno < logging.ERROR:
            return  # Only send errors and critical
        
        try:
            # Extract exception info
            exception_type = ""
            stack_trace = ""
            
            if record.exc_info:
                import traceback
                exception_type = record.exc_info[0].__name__
                stack_trace = "".join(traceback.format_exception(*record.exc_info))
            
            # Get EC2 instance ID (if available)
            instance_id = None
            try:
                import requests
                response = requests.get(
                    "http://169.254.169.254/latest/meta-data/instance-id",
                    timeout=0.1
                )
                instance_id = response.text
            except:
                pass
            
            # Get git commit SHA (from environment or git)
            commit_sha = os.getenv("GIT_COMMIT_SHA")
            if not commit_sha:
                try:
                    import subprocess
                    commit_sha = subprocess.check_output(
                        ["git", "rev-parse", "HEAD"],
                        stderr=subprocess.DEVNULL
                    ).decode().strip()
                except:
                    pass
            
            # Build alert payload
            payload = {
                "service_name": "django-api",
                "exception_type": exception_type or record.levelname,
                "error_message": record.getMessage(),
                "stack_trace": stack_trace or self.format(record),
                "related_logs": [],  # Could be populated from recent logs
                "request_path": getattr(record, "request_path", None),
                "environment": os.getenv("ENVIRONMENT_NAME", "production"),
                "instance_id": instance_id,
                "commit_sha": commit_sha,
                "severity": record.levelname,
                "additional_context": {
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                }
            }
            
            # Send to webhook (non-blocking)
            try:
                requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=2
                )
            except requests.exceptions.RequestException:
                pass  # Don't let webhook failures affect the application
        
        except Exception as e:
            # Don't let logging errors crash the application
            print(f"Error in JinkiesAlertHandler: {e}")


# Django logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} {module} {message}",
            "style": "{",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "cloudwatch": {
            "class": "watchtower.CloudWatchLogHandler",
            "log_group": "/aws/ec2/django-api",
            "stream_name": "{strftime:%Y-%m-%d}-{hostname}",
            "formatter": "json",
        },
        "jinkies": {
            "class": "path.to.JinkiesAlertHandler",  # Update with actual path
            "level": "ERROR",
        },
    },
    "root": {
        "handlers": ["console", "cloudwatch", "jinkies"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "cloudwatch", "jinkies"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "cloudwatch", "jinkies"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}


# Middleware to add request context to logs
class RequestLoggingMiddleware:
    """Middleware to add request information to log records."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Store request in thread-local storage for logging
        import threading
        _request_local = threading.local()
        _request_local.request = request
        
        response = self.get_response(request)
        return response
    
    def process_exception(self, request, exception):
        """Log exceptions with request context."""
        logger = logging.getLogger("django.request")
        
        # Add request path to log record
        extra = {"request_path": request.path}
        
        logger.error(
            f"Exception on {request.method} {request.path}",
            exc_info=True,
            extra=extra
        )


# Add this middleware to your MIDDLEWARE setting:
# MIDDLEWARE = [
#     ...
#     'path.to.RequestLoggingMiddleware',
#     ...
# ]
