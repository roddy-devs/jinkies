"""
Alert storage and management.
Stores alerts in a SQLite database for persistence and querying.
"""
import sqlite3
import json
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bot.models.alert import Alert


class AlertStore:
    """Manages alert persistence and retrieval."""
    
    def __init__(self, db_path: str = "alerts.db"):
        """Initialize alert store with database path."""
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id TEXT PRIMARY KEY,
                django_alert_id TEXT NOT NULL,
                service_name TEXT NOT NULL,
                exception_type TEXT,
                error_message TEXT,
                stack_trace TEXT,
                request_path TEXT,
                timestamp TEXT NOT NULL,
                received_at TEXT NOT NULL,
                environment TEXT,
                acknowledged INTEGER DEFAULT 0,
                acknowledged_by TEXT,
                acknowledged_at TEXT,
                github_pr_url TEXT,
                github_issue_url TEXT,
                severity TEXT DEFAULT 'ERROR',
                additional_context TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_django_alert ON alerts(django_alert_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON alerts(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_service ON alerts(service_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_severity ON alerts(severity)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_acknowledged ON alerts(acknowledged)")
        
        conn.commit()
        conn.close()
    
    def save_alert(self, alert: Alert) -> bool:
        """Save an alert to the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO alerts (
                    alert_id, django_alert_id, service_name, exception_type, error_message,
                    stack_trace, request_path, timestamp, received_at,
                    environment, acknowledged, acknowledged_by, acknowledged_at,
                    github_pr_url, github_issue_url, severity, additional_context
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.alert_id,
                alert.django_alert_id,
                alert.service_name,
                alert.exception_type,
                alert.error_message,
                alert.stack_trace,
                alert.request_path,
                alert.timestamp,
                alert.received_at,
                alert.environment,
                int(alert.acknowledged),
                alert.acknowledged_by,
                alert.acknowledged_at,
                alert.github_pr_url,
                alert.github_issue_url,
                alert.severity,
                json.dumps(alert.additional_context)
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving alert: {e}")
            return False
    
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Retrieve an alert by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return self._row_to_alert(row)
    
    def get_recent_alerts(self, limit: int = 10, acknowledged: Optional[bool] = None) -> List[Alert]:
        """Get recent alerts, optionally filtered by acknowledgement status."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if acknowledged is None:
            cursor.execute(
                "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
        else:
            cursor.execute(
                "SELECT * FROM alerts WHERE acknowledged = ? ORDER BY timestamp DESC LIMIT ?",
                (int(acknowledged), limit)
            )
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_alert(row) for row in rows]
    
    def get_alerts_by_service(self, service_name: str, limit: int = 10) -> List[Alert]:
        """Get alerts for a specific service."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM alerts WHERE service_name = ? ORDER BY timestamp DESC LIMIT ?",
            (service_name, limit)
        )
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_alert(row) for row in rows]
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Mark an alert as acknowledged."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE alerts 
                SET acknowledged = 1, 
                    acknowledged_by = ?,
                    acknowledged_at = ?
                WHERE alert_id = ?
            """, (acknowledged_by, datetime.now(timezone.utc).isoformat(), alert_id))
            
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error acknowledging alert: {e}")
            return False
    
    def update_github_links(self, alert_id: str, pr_url: Optional[str] = None, issue_url: Optional[str] = None) -> bool:
        """Update GitHub PR/issue URLs for an alert."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if pr_url:
                updates.append("github_pr_url = ?")
                params.append(pr_url)
            
            if issue_url:
                updates.append("github_issue_url = ?")
                params.append(issue_url)
            
            if not updates:
                return False
            
            params.append(alert_id)
            query = f"UPDATE alerts SET {', '.join(updates)} WHERE alert_id = ?"
            
            cursor.execute(query, params)
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating GitHub links: {e}")
            return False
    
    def cleanup_old_alerts(self, days: int = 30) -> int:
        """Delete alerts older than specified days."""
        try:
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM alerts WHERE timestamp < ?", (cutoff_date,))
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            return deleted_count
        except Exception as e:
            print(f"Error cleaning up alerts: {e}")
            return 0
    
    def _row_to_alert(self, row: sqlite3.Row) -> Alert:
        """Convert a database row to an Alert object."""
        return Alert(
            alert_id=row["alert_id"],
            django_alert_id=row["django_alert_id"],
            service_name=row["service_name"],
            exception_type=row["exception_type"] or "",
            error_message=row["error_message"] or "",
            stack_trace=row["stack_trace"] or "",
            request_path=row["request_path"],
            timestamp=row["timestamp"],
            received_at=row["received_at"],
            environment=row["environment"] or "",
            acknowledged=bool(row["acknowledged"]),
            acknowledged_by=row["acknowledged_by"],
            acknowledged_at=row["acknowledged_at"],
            github_pr_url=row["github_pr_url"],
            github_issue_url=row["github_issue_url"],
            severity=row["severity"] or "ERROR",
            additional_context=json.loads(row["additional_context"]) if row["additional_context"] else {}
        )
