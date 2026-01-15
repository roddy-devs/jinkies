"""
Unit tests for Jinkies bot.
"""
import unittest
from datetime import datetime
from bot.models.alert import Alert, LogEntry
from bot.services.alert_store import AlertStore
import os
import tempfile


class TestAlert(unittest.TestCase):
    """Test Alert model."""
    
    def test_alert_creation(self):
        """Test creating an alert."""
        alert = Alert(
            service_name="test-service",
            exception_type="TestError",
            error_message="Test error message",
            environment="testing"
        )
        
        self.assertEqual(alert.service_name, "test-service")
        self.assertEqual(alert.exception_type, "TestError")
        self.assertIsNotNone(alert.alert_id)
        self.assertFalse(alert.acknowledged)
    
    def test_alert_severity_emoji(self):
        """Test severity emoji mapping."""
        alert_info = Alert(severity="INFO")
        alert_error = Alert(severity="ERROR")
        alert_critical = Alert(severity="CRITICAL")
        
        self.assertEqual(alert_info.get_severity_emoji(), "ℹ️")
        self.assertEqual(alert_error.get_severity_emoji(), "🚨")
        self.assertEqual(alert_critical.get_severity_emoji(), "🔥")
    
    def test_alert_short_id(self):
        """Test short ID generation."""
        alert = Alert()
        short_id = alert.get_short_id()
        
        self.assertEqual(len(short_id), 8)
        self.assertTrue(alert.alert_id.startswith(short_id))
    
    def test_alert_to_dict(self):
        """Test converting alert to dictionary."""
        alert = Alert(
            service_name="test",
            exception_type="Error"
        )
        
        alert_dict = alert.to_dict()
        
        self.assertIsInstance(alert_dict, dict)
        self.assertEqual(alert_dict["service_name"], "test")
        self.assertEqual(alert_dict["exception_type"], "Error")


class TestLogEntry(unittest.TestCase):
    """Test LogEntry model."""
    
    def test_log_entry_creation(self):
        """Test creating a log entry."""
        entry = LogEntry(
            timestamp="2024-01-15T12:00:00",
            level="ERROR",
            message="Test log message"
        )
        
        self.assertEqual(entry.level, "ERROR")
        self.assertEqual(entry.message, "Test log message")
    
    def test_log_entry_formatting(self):
        """Test log entry Discord formatting."""
        entry = LogEntry(
            timestamp="2024-01-15T12:00:00",
            level="ERROR",
            message="Test message"
        )
        
        formatted = entry.format_for_discord()
        
        self.assertIn("ERROR", formatted)
        self.assertIn("Test message", formatted)


class TestAlertStore(unittest.TestCase):
    """Test AlertStore service."""
    
    def setUp(self):
        """Create temporary database for testing."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.store = AlertStore(db_path=self.temp_db.name)
    
    def tearDown(self):
        """Clean up temporary database."""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_save_and_retrieve_alert(self):
        """Test saving and retrieving an alert."""
        alert = Alert(
            service_name="test-service",
            exception_type="TestError",
            error_message="Test error"
        )
        
        # Save alert
        success = self.store.save_alert(alert)
        self.assertTrue(success)
        
        # Retrieve alert
        retrieved = self.store.get_alert(alert.alert_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.service_name, "test-service")
        self.assertEqual(retrieved.exception_type, "TestError")
    
    def test_acknowledge_alert(self):
        """Test acknowledging an alert."""
        alert = Alert(service_name="test")
        self.store.save_alert(alert)
        
        # Acknowledge
        success = self.store.acknowledge_alert(alert.alert_id, "test_user")
        self.assertTrue(success)
        
        # Verify acknowledgement
        retrieved = self.store.get_alert(alert.alert_id)
        self.assertTrue(retrieved.acknowledged)
        self.assertEqual(retrieved.acknowledged_by, "test_user")
    
    def test_get_recent_alerts(self):
        """Test getting recent alerts."""
        # Create multiple alerts
        for i in range(5):
            alert = Alert(
                service_name=f"service-{i}",
                exception_type="TestError"
            )
            self.store.save_alert(alert)
        
        # Get recent alerts
        alerts = self.store.get_recent_alerts(limit=3)
        self.assertEqual(len(alerts), 3)
    
    def test_update_github_links(self):
        """Test updating GitHub links."""
        alert = Alert(service_name="test")
        self.store.save_alert(alert)
        
        # Update PR URL
        pr_url = "https://github.com/test/repo/pull/1"
        success = self.store.update_github_links(alert.alert_id, pr_url=pr_url)
        self.assertTrue(success)
        
        # Verify update
        retrieved = self.store.get_alert(alert.alert_id)
        self.assertEqual(retrieved.github_pr_url, pr_url)


if __name__ == "__main__":
    unittest.main()
