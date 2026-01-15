"""
AWS Lambda function to forward CloudWatch Logs to Jinkies webhook.

This function can be triggered by CloudWatch Logs subscriptions to
forward errors to the Jinkies Discord bot in real-time.

Setup:
1. Create Lambda function with this code
2. Set JINKIES_WEBHOOK_URL environment variable
3. Create CloudWatch Logs subscription filter to trigger this Lambda
4. Configure filter pattern to match errors (e.g., "[ERROR]" or "[CRITICAL]")
"""

import json
import gzip
import base64
import os
import urllib3
from typing import Dict, Any, List

# Initialize HTTP client
http = urllib3.PoolManager()

# Jinkies webhook URL from environment
WEBHOOK_URL = os.environ.get("JINKIES_WEBHOOK_URL")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for CloudWatch Logs events.
    
    Args:
        event: CloudWatch Logs event
        context: Lambda context
    
    Returns:
        Response dictionary
    """
    try:
        # Decode and decompress CloudWatch Logs data
        log_data = event.get("awslogs", {}).get("data", "")
        
        if not log_data:
            return {"statusCode": 400, "body": "No log data found"}
        
        # Decode base64 and decompress gzip
        decoded = base64.b64decode(log_data)
        decompressed = gzip.decompress(decoded)
        log_events = json.loads(decompressed)
        
        # Extract log group and stream
        log_group = log_events.get("logGroup", "")
        log_stream = log_events.get("logStream", "")
        
        # Process each log event
        alerts_sent = 0
        
        for log_event in log_events.get("logEvents", []):
            message = log_event.get("message", "")
            
            # Check if this is an error that should be alerted
            if should_alert(message):
                alert = create_alert_from_log(
                    message=message,
                    log_group=log_group,
                    log_stream=log_stream,
                    timestamp=log_event.get("timestamp")
                )
                
                # Send to Jinkies webhook
                if send_alert(alert):
                    alerts_sent += 1
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Processed successfully",
                "alerts_sent": alerts_sent
            })
        }
    
    except Exception as e:
        print(f"Error processing log event: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


def should_alert(message: str) -> bool:
    """
    Determine if a log message should trigger an alert.
    
    Args:
        message: Log message
    
    Returns:
        True if should alert
    """
    # Alert on ERROR and CRITICAL levels
    error_indicators = ["[ERROR]", "[CRITICAL]", "ERROR:", "Exception:", "Traceback"]
    
    return any(indicator in message for indicator in error_indicators)


def create_alert_from_log(
    message: str,
    log_group: str,
    log_stream: str,
    timestamp: int
) -> Dict[str, Any]:
    """
    Create an alert payload from a log message.
    
    Args:
        message: Log message
        log_group: CloudWatch log group
        log_stream: CloudWatch log stream
        timestamp: Log timestamp
    
    Returns:
        Alert dictionary
    """
    # Extract service name from log group
    service_name = extract_service_name(log_group)
    
    # Try to parse exception type
    exception_type = extract_exception_type(message)
    
    # Determine severity
    severity = "CRITICAL" if "CRITICAL" in message else "ERROR"
    
    # Get instance ID from log stream if available
    instance_id = extract_instance_id(log_stream)
    
    return {
        "service_name": service_name,
        "exception_type": exception_type,
        "error_message": message[:500],  # Limit message length
        "stack_trace": message,
        "related_logs": [],
        "request_path": None,
        "environment": os.environ.get("ENVIRONMENT_NAME", "production"),
        "instance_id": instance_id,
        "commit_sha": None,
        "severity": severity,
        "additional_context": {
            "log_group": log_group,
            "log_stream": log_stream,
            "source": "cloudwatch-lambda"
        }
    }


def extract_service_name(log_group: str) -> str:
    """Extract service name from log group."""
    # Example: /aws/ec2/django-api -> django-api
    parts = log_group.split("/")
    return parts[-1] if parts else "unknown"


def extract_exception_type(message: str) -> str:
    """Extract exception type from message."""
    # Look for common exception patterns
    import re
    
    # Pattern: ExceptionName: message
    match = re.search(r"(\w+Error|\w+Exception):", message)
    if match:
        return match.group(1)
    
    return "UnknownError"


def extract_instance_id(log_stream: str) -> str:
    """Extract EC2 instance ID from log stream."""
    # Log stream often contains instance ID
    import re
    
    match = re.search(r"i-[a-z0-9]+", log_stream)
    if match:
        return match.group(0)
    
    return None


def send_alert(alert: Dict[str, Any]) -> bool:
    """
    Send alert to Jinkies webhook.
    
    Args:
        alert: Alert dictionary
    
    Returns:
        True if successful
    """
    if not WEBHOOK_URL:
        print("JINKIES_WEBHOOK_URL not configured")
        return False
    
    try:
        response = http.request(
            "POST",
            WEBHOOK_URL,
            body=json.dumps(alert).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            timeout=5.0
        )
        
        if response.status == 201:
            print(f"Alert sent successfully: {alert.get('exception_type')}")
            return True
        else:
            print(f"Failed to send alert: {response.status}")
            return False
    
    except Exception as e:
        print(f"Error sending alert: {e}")
        return False


# For local testing
if __name__ == "__main__":
    # Example test event
    test_event = {
        "awslogs": {
            "data": "H4sIAAAAAAAAAHWPwQqCQBCGX0Xm7EFtK+smZBEUgXoLEreV1XXpOMOlSt+9Y1kgpN3+j+Hf+f8HXdq9R2HpJtKWKoU7ixREqWjXJd5zEsv2Tw8BhUEVRXPiSWMkQRhCBAIOJ2x0qHqS9VGCuCvk+EKhSQO3K9XBEkkLkMFiKJjCXkqHGy4EwJYTcLgQVwNF7A2CJfHxSr0EFCnHNfV8IiZqXqAoRJYBKsKkBCl/pJSqKjkkqWqpjIR6jJIVYhTxVBj/B/P6lhfnY3+Yd79hHO2MAAAAg=="
        }
    }
    
    print(lambda_handler(test_event, None))
