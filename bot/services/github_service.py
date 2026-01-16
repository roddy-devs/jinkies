"""
GitHub integration for PR and issue creation.
"""
from typing import Optional, Dict, Any
from github import Github, GithubException
from bot.config import config
from bot.models.alert import Alert
import logging

logger = logging.getLogger("jinkies.github")


class GitHubService:
    """Service for GitHub API interactions."""
    
    def __init__(self):
        """
        Initialize GitHub client.
        
        Note: In production, use GitHub App authentication instead of personal
        access tokens for better security, higher rate limits, and granular permissions.
        See: https://docs.github.com/en/apps/creating-github-apps
        """
        # Use personal access token (stored in GITHUB_PRIVATE_KEY for simplicity)
        self.client = Github(config.GITHUB_PRIVATE_KEY)
        self.repo = self.client.get_repo(f"{config.GITHUB_REPO_OWNER}/{config.GITHUB_REPO_NAME}")
    
    def create_pr_from_alert(
        self,
        alert: Alert,
        base_branch: Optional[str] = None,
        fix_notes: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a GitHub PR from an alert.
        
        Args:
            alert: Alert object with error details
            base_branch: Target branch (default from config)
            fix_notes: Optional additional notes from user
        
        Returns:
            PR URL if successful, None otherwise
        """
        try:
            base = base_branch or config.DEFAULT_BASE_BRANCH
            branch_name = f"fix/alert-{alert.get_short_id()}"
            
            # Generate PR content
            title = self._generate_pr_title(alert)
            body = self._generate_pr_body(alert, fix_notes)
            
            # Create branch (from base branch)
            try:
                base_ref = self.repo.get_git_ref(f"heads/{base}")
                self.repo.create_git_ref(
                    ref=f"refs/heads/{branch_name}",
                    sha=base_ref.object.sha
                )
            except GithubException as e:
                if e.status != 422:  # Branch already exists
                    raise
            
            # Create PR as draft
            pr = self.repo.create_pull(
                title=title,
                body=body,
                base=base,
                head=branch_name,
                draft=True
            )
            
            # Add labels
            try:
                labels = ["bug", "automated"]
                if alert.severity == "CRITICAL":
                    labels.append("critical")
                pr.add_to_labels(*labels)
            except:
                pass  # Labels might not exist
            
            return pr.html_url
        
        except Exception as e:
            logger.error(f"Error creating PR: {e}", exc_info=True)
            return None
    
    def create_issue_from_alert(self, alert: Alert) -> Optional[str]:
        """
        Create a GitHub issue from an alert.
        
        Args:
            alert: Alert object with error details
        
        Returns:
            Issue URL if successful, None otherwise
        """
        try:
            title = self._generate_issue_title(alert)
            body = self._generate_issue_body(alert)
            
            # Create issue
            issue = self.repo.create_issue(
                title=title,
                body=body,
            )
            
            # Add labels
            try:
                labels = ["bug", "automated"]
                if alert.severity == "CRITICAL":
                    labels.append("critical")
                issue.add_to_labels(*labels)
            except:
                pass
            
            return issue.html_url
        
        except Exception as e:
            logger.error(f"Error creating issue: {e}", exc_info=True)
            return None
    
    def _generate_pr_title(self, alert: Alert) -> str:
        """Generate PR title from alert."""
        return f"Fix: {alert.exception_type} in {alert.service_name}"
    
    def _generate_pr_body(self, alert: Alert, fix_notes: Optional[str] = None) -> str:
        """Generate PR body from alert."""
        body = f"""## 🚨 Auto-generated PR from Alert {alert.get_short_id()}

### What Happened
An error was detected in **{alert.environment}** environment.

### Error Summary
- **Service**: {alert.service_name}
- **Exception**: {alert.exception_type}
- **Message**: {alert.error_message}
- **Endpoint**: {alert.request_path or 'N/A'}
- **Timestamp**: {alert.timestamp}
- **Instance**: {alert.instance_id or 'N/A'}
- **Commit**: {alert.commit_sha or 'N/A'}

### Stack Trace
```
{alert.get_trimmed_stack_trace()}
```

### Related Logs
```
"""
        
        for log in alert.get_trimmed_logs(5):
            body += f"{log}\n"
        
        body += """```

### Expected Behavior
The application should handle this case gracefully without throwing an exception.

### Actual Behavior
The application encountered an unhandled exception.

"""
        
        if fix_notes:
            body += f"""### Proposed Fix
{fix_notes}

"""
        
        body += f"""### Reproduction Steps
1. Monitor the endpoint: `{alert.request_path or 'See logs'}`
2. Review the stack trace above
3. Check related logs in CloudWatch

### Alert Reference
- **Alert ID**: `{alert.alert_id}`
- **Environment**: `{alert.environment}`

---
*This PR was automatically generated by the Jinkies monitoring bot.*
"""
        
        return body
    
    def _generate_issue_title(self, alert: Alert) -> str:
        """Generate issue title from alert."""
        return f"[{alert.severity}] {alert.exception_type}: {alert.error_message[:50]}"
    
    def _generate_issue_body(self, alert: Alert) -> str:
        """Generate issue body from alert."""
        body = f"""## Error Report (Alert {alert.get_short_id()})

### Environment
- **Service**: {alert.service_name}
- **Environment**: {alert.environment}
- **Timestamp**: {alert.timestamp}
- **Severity**: {alert.severity}

### Error Details
**Exception Type**: {alert.exception_type}

**Error Message**:
```
{alert.error_message}
```

**Request Path**: {alert.request_path or 'N/A'}

**Instance ID**: {alert.instance_id or 'N/A'}

**Commit SHA**: {alert.commit_sha or 'N/A'}

### Stack Trace
```
{alert.get_trimmed_stack_trace()}
```

### Related Logs
```
"""
        
        for log in alert.get_trimmed_logs(5):
            body += f"{log}\n"
        
        body += f"""```

### Alert ID
`{alert.alert_id}`

---
*This issue was automatically created by the Jinkies monitoring bot.*
"""
        
        return body
    
    def test_connection(self) -> bool:
        """Test GitHub API connection."""
        try:
            self.repo.get_branches()
            return True
        except Exception as e:
            logger.error(f"GitHub connection test failed: {e}", exc_info=True)
            return False
