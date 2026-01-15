"""
Data models for alerts and error tracking.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import uuid
import json


@dataclass
class Alert:
    """Represents an error alert with full context."""
    
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    service_name: str = ""
    exception_type: str = ""
    error_message: str = ""
    stack_trace: str = ""
    related_logs: List[str] = field(default_factory=list)
    request_path: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    environment: str = ""
    instance_id: Optional[str] = None
    commit_sha: Optional[str] = None
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None
    github_pr_url: Optional[str] = None
    github_issue_url: Optional[str] = None
    severity: str = "ERROR"  # INFO, WARNING, ERROR, CRITICAL
    additional_context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert alert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Alert":
        """Create alert from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> "Alert":
        """Create alert from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def get_severity_emoji(self) -> str:
        """Get emoji for alert severity."""
        emoji_map = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "🚨",
            "CRITICAL": "🔥",
        }
        return emoji_map.get(self.severity, "❓")
    
    def get_short_id(self) -> str:
        """Get shortened alert ID for display."""
        return self.alert_id[:8]
    
    def get_trimmed_stack_trace(self, max_lines: int = 15) -> str:
        """Get trimmed stack trace for display."""
        if not self.stack_trace:
            return ""
        
        lines = self.stack_trace.split("\n")
        if len(lines) <= max_lines:
            return self.stack_trace
        
        return "\n".join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"
    
    def get_trimmed_logs(self, max_lines: int = 10) -> List[str]:
        """Get trimmed related logs for display."""
        if len(self.related_logs) <= max_lines:
            return self.related_logs
        
        return self.related_logs[:max_lines]


@dataclass
class LogEntry:
    """Represents a single log entry."""
    
    timestamp: str
    level: str
    message: str
    service: str = ""
    stream_name: str = ""
    
    def format_for_discord(self) -> str:
        """Format log entry for Discord display."""
        return f"[{self.level}] {self.timestamp} - {self.message}"
