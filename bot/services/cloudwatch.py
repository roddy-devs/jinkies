"""
AWS CloudWatch Logs integration.
Queries and filters logs from CloudWatch log groups.
"""
import boto3
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from bot.config import config
from bot.models.alert import LogEntry


class CloudWatchService:
    """Service for querying AWS CloudWatch Logs."""
    
    def __init__(self):
        """Initialize CloudWatch client."""
        session_params = {"region_name": config.AWS_REGION}
        
        if config.AWS_ACCESS_KEY_ID and config.AWS_SECRET_ACCESS_KEY:
            session_params["aws_access_key_id"] = config.AWS_ACCESS_KEY_ID
            session_params["aws_secret_access_key"] = config.AWS_SECRET_ACCESS_KEY
        
        self.client = boto3.client("logs", **session_params)
    
    def get_logs(
        self,
        log_group: str,
        log_level: Optional[str] = None,
        since_minutes: int = 60,
        limit: int = 50,
        filter_pattern: Optional[str] = None
    ) -> List[LogEntry]:
        """
        Retrieve logs from CloudWatch.
        
        Args:
            log_group: CloudWatch log group name
            log_level: Filter by log level (INFO, WARNING, ERROR, CRITICAL)
            since_minutes: How many minutes back to search
            limit: Maximum number of log entries to return
            filter_pattern: CloudWatch Logs Insights filter pattern
        
        Returns:
            List of LogEntry objects
        """
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=since_minutes)
            
            # Build filter pattern
            if not filter_pattern:
                if log_level:
                    filter_pattern = f"[{log_level}]"
                else:
                    filter_pattern = ""
            
            # Query parameters
            params = {
                "logGroupName": log_group,
                "startTime": int(start_time.timestamp() * 1000),
                "endTime": int(end_time.timestamp() * 1000),
                "limit": limit,
            }
            
            if filter_pattern:
                params["filterPattern"] = filter_pattern
            
            # Get log streams
            log_entries = []
            
            response = self.client.filter_log_events(**params)
            
            for event in response.get("events", []):
                log_entries.append(
                    LogEntry(
                        timestamp=datetime.fromtimestamp(event["timestamp"] / 1000).isoformat(),
                        level=self._extract_log_level(event["message"]),
                        message=event["message"],
                        stream_name=event.get("logStreamName", ""),
                    )
                )
            
            # Handle pagination if needed
            while "nextToken" in response and len(log_entries) < limit:
                params["nextToken"] = response["nextToken"]
                response = self.client.filter_log_events(**params)
                
                for event in response.get("events", []):
                    if len(log_entries) >= limit:
                        break
                    log_entries.append(
                        LogEntry(
                            timestamp=datetime.fromtimestamp(event["timestamp"] / 1000).isoformat(),
                            level=self._extract_log_level(event["message"]),
                            message=event["message"],
                            stream_name=event.get("logStreamName", ""),
                        )
                    )
            
            return log_entries[:limit]
        
        except Exception as e:
            print(f"Error fetching CloudWatch logs: {e}")
            return []
    
    def get_log_streams(self, log_group: str, limit: int = 10) -> List[str]:
        """Get available log streams in a log group."""
        try:
            response = self.client.describe_log_streams(
                logGroupName=log_group,
                orderBy="LastEventTime",
                descending=True,
                limit=limit
            )
            
            return [stream["logStreamName"] for stream in response.get("logStreams", [])]
        except Exception as e:
            print(f"Error fetching log streams: {e}")
            return []
    
    def tail_logs(
        self,
        log_group: str,
        log_level: Optional[str] = None,
        last_seen_timestamp: Optional[int] = None
    ) -> List[LogEntry]:
        """
        Get new logs since last seen timestamp (for tailing).
        
        Args:
            log_group: CloudWatch log group name
            log_level: Filter by log level
            last_seen_timestamp: Unix timestamp (ms) of last seen log
        
        Returns:
            List of new LogEntry objects
        """
        try:
            # Start from last seen or 1 minute ago
            if last_seen_timestamp:
                start_time = last_seen_timestamp + 1  # +1ms to avoid duplicates
            else:
                start_time = int((datetime.utcnow() - timedelta(minutes=1)).timestamp() * 1000)
            
            end_time = int(datetime.utcnow().timestamp() * 1000)
            
            params = {
                "logGroupName": log_group,
                "startTime": start_time,
                "endTime": end_time,
                "limit": 100,
            }
            
            if log_level:
                params["filterPattern"] = f"[{log_level}]"
            
            response = self.client.filter_log_events(**params)
            
            log_entries = []
            for event in response.get("events", []):
                log_entries.append(
                    LogEntry(
                        timestamp=datetime.fromtimestamp(event["timestamp"] / 1000).isoformat(),
                        level=self._extract_log_level(event["message"]),
                        message=event["message"],
                        stream_name=event.get("logStreamName", ""),
                    )
                )
            
            return log_entries
        
        except Exception as e:
            print(f"Error tailing logs: {e}")
            return []
    
    def _extract_log_level(self, message: str) -> str:
        """Extract log level from message."""
        message_upper = message.upper()
        for level in ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]:
            if level in message_upper:
                return level
        return "INFO"
    
    def test_connection(self, log_group: str) -> bool:
        """Test connection to CloudWatch and verify log group exists."""
        try:
            self.client.describe_log_groups(logGroupNamePrefix=log_group, limit=1)
            return True
        except Exception as e:
            print(f"CloudWatch connection test failed: {e}")
            return False
