"""
Deployment tracking model.
"""
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger("jinkies.deployment_store")


class Deployment:
    """Represents a deployment record."""
    
    def __init__(
        self,
        id: Optional[int] = None,
        branch: str = "",
        commit_hash: str = "",
        triggered_by: str = "",
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        status: str = "in_progress",
        method: str = "direct",
        duration_seconds: Optional[int] = None,
        output_logs: str = "",
        error_message: Optional[str] = None,
        discord_channel_id: Optional[str] = None,
        frontend_deployed: bool = False,
        backend_deployed: bool = False,
        cloudfront_invalidation_id: Optional[str] = None,
    ):
        self.id = id
        self.branch = branch
        self.commit_hash = commit_hash
        self.triggered_by = triggered_by
        self.started_at = started_at or datetime.utcnow()
        self.completed_at = completed_at
        self.status = status
        self.method = method
        self.duration_seconds = duration_seconds
        self.output_logs = output_logs
        self.error_message = error_message
        self.discord_channel_id = discord_channel_id
        self.frontend_deployed = frontend_deployed
        self.backend_deployed = backend_deployed
        self.cloudfront_invalidation_id = cloudfront_invalidation_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "branch": self.branch,
            "commit_hash": self.commit_hash,
            "triggered_by": self.triggered_by,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "method": self.method,
            "duration_seconds": self.duration_seconds,
            "output_logs": self.output_logs,
            "error_message": self.error_message,
            "discord_channel_id": self.discord_channel_id,
            "frontend_deployed": self.frontend_deployed,
            "backend_deployed": self.backend_deployed,
            "cloudfront_invalidation_id": self.cloudfront_invalidation_id,
        }


class DeploymentStore:
    """SQLite storage for deployment records."""
    
    def __init__(self, db_path: str = "deployments.db"):
        """Initialize deployment store."""
        self.db_path = Path(db_path)
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS deployments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    branch TEXT NOT NULL,
                    commit_hash TEXT,
                    triggered_by TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    status TEXT NOT NULL,
                    method TEXT NOT NULL,
                    duration_seconds INTEGER,
                    output_logs TEXT,
                    error_message TEXT,
                    discord_channel_id TEXT,
                    frontend_deployed INTEGER DEFAULT 0,
                    backend_deployed INTEGER DEFAULT 0,
                    cloudfront_invalidation_id TEXT
                )
            """)
            conn.commit()
            logger.info(f"Deployment database initialized at {self.db_path}")
    
    def save_deployment(self, deployment: Deployment) -> int:
        """Save a deployment record."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO deployments (
                    branch, commit_hash, triggered_by, started_at, completed_at,
                    status, method, duration_seconds, output_logs, error_message,
                    discord_channel_id, frontend_deployed, backend_deployed,
                    cloudfront_invalidation_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                deployment.branch,
                deployment.commit_hash,
                deployment.triggered_by,
                deployment.started_at.isoformat() if deployment.started_at else None,
                deployment.completed_at.isoformat() if deployment.completed_at else None,
                deployment.status,
                deployment.method,
                deployment.duration_seconds,
                deployment.output_logs,
                deployment.error_message,
                deployment.discord_channel_id,
                1 if deployment.frontend_deployed else 0,
                1 if deployment.backend_deployed else 0,
                deployment.cloudfront_invalidation_id,
            ))
            conn.commit()
            deployment.id = cursor.lastrowid
            logger.info(f"Saved deployment {deployment.id}")
            return deployment.id
    
    def update_deployment(self, deployment: Deployment):
        """Update an existing deployment record."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE deployments SET
                    branch = ?,
                    commit_hash = ?,
                    triggered_by = ?,
                    started_at = ?,
                    completed_at = ?,
                    status = ?,
                    method = ?,
                    duration_seconds = ?,
                    output_logs = ?,
                    error_message = ?,
                    discord_channel_id = ?,
                    frontend_deployed = ?,
                    backend_deployed = ?,
                    cloudfront_invalidation_id = ?
                WHERE id = ?
            """, (
                deployment.branch,
                deployment.commit_hash,
                deployment.triggered_by,
                deployment.started_at.isoformat() if deployment.started_at else None,
                deployment.completed_at.isoformat() if deployment.completed_at else None,
                deployment.status,
                deployment.method,
                deployment.duration_seconds,
                deployment.output_logs,
                deployment.error_message,
                deployment.discord_channel_id,
                1 if deployment.frontend_deployed else 0,
                1 if deployment.backend_deployed else 0,
                deployment.cloudfront_invalidation_id,
                deployment.id,
            ))
            conn.commit()
            logger.info(f"Updated deployment {deployment.id}")
    
    def get_deployment(self, deployment_id: int) -> Optional[Deployment]:
        """Get a deployment by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM deployments WHERE id = ?",
                (deployment_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_deployment(row)
            return None
    
    def get_recent_deployments(self, limit: int = 10) -> List[Deployment]:
        """Get recent deployments."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM deployments ORDER BY started_at DESC LIMIT ?",
                (limit,)
            )
            return [self._row_to_deployment(row) for row in cursor.fetchall()]
    
    def get_deployments_by_status(self, status: str) -> List[Deployment]:
        """Get deployments by status."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM deployments WHERE status = ? ORDER BY started_at DESC",
                (status,)
            )
            return [self._row_to_deployment(row) for row in cursor.fetchall()]
    
    def get_last_successful_deployment(self) -> Optional[Deployment]:
        """Get the last successful deployment."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM deployments WHERE status = 'success' ORDER BY completed_at DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_deployment(row)
            return None
    
    def _row_to_deployment(self, row: sqlite3.Row) -> Deployment:
        """Convert database row to Deployment object."""
        return Deployment(
            id=row["id"],
            branch=row["branch"],
            commit_hash=row["commit_hash"],
            triggered_by=row["triggered_by"],
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            status=row["status"],
            method=row["method"],
            duration_seconds=row["duration_seconds"],
            output_logs=row["output_logs"],
            error_message=row["error_message"],
            discord_channel_id=row["discord_channel_id"],
            frontend_deployed=bool(row["frontend_deployed"]),
            backend_deployed=bool(row["backend_deployed"]),
            cloudfront_invalidation_id=row["cloudfront_invalidation_id"],
        )
