"""
Deployment execution service - runs deployments directly without GitHub Actions.
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import subprocess

logger = logging.getLogger("jinkies.deploy_executor")


class DeploymentExecutor:
    """Executes deployments by running deployment scripts."""
    
    def __init__(self, repo_path: str, ssh_key_path: str, ec2_host: str, ec2_user: str = "ubuntu"):
        """
        Initialize deployment executor.
        
        Args:
            repo_path: Path to the repository on local machine
            ssh_key_path: Path to SSH key for EC2 access
            ec2_host: EC2 host address
            ec2_user: EC2 username (default: ubuntu)
        """
        self.repo_path = Path(repo_path)
        self.ssh_key_path = ssh_key_path
        self.ec2_host = ec2_host
        self.ec2_user = ec2_user
        
    async def deploy(self, branch: str = "develop") -> Dict[str, Any]:
        """
        Execute deployment for specified branch.
        
        Args:
            branch: Git branch to deploy
            
        Returns:
            Dict with deployment status and output
        """
        logger.info(f"Starting deployment of branch: {branch}")
        
        try:
            # Pull latest changes
            await self._run_command(f"cd {self.repo_path} && git fetch origin")
            await self._run_command(f"cd {self.repo_path} && git checkout {branch}")
            await self._run_command(f"cd {self.repo_path} && git pull origin {branch}")
            
            # Run Jinkies deployment script (not from the repo)
            import os
            jinkies_path = Path(__file__).parent.parent.parent  # Go up to jinkies root
            deploy_script = jinkies_path / "scripts" / "deploy-nomadic.sh"
            
            if not deploy_script.exists():
                raise FileNotFoundError(f"Deployment script not found: {deploy_script}")
            
            # Set environment variables for deployment
            import os
            env = {
                "DEPLOY_REPO_PATH": str(self.repo_path),
                "DEPLOY_SSH_KEY": self.ssh_key_path,
                "DEPLOY_EC2_HOST": self.ec2_host,
                "DEPLOY_EC2_USER": self.ec2_user,
                "HOME": os.environ.get("HOME", ""),
                "PATH": os.environ.get("PATH", ""),
            }
            
            # Pass AWS credentials if available
            for aws_var in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_DEFAULT_REGION"]:
                if aws_var in os.environ:
                    env[aws_var] = os.environ[aws_var]
            
            result = await self._run_command(
                str(deploy_script),
                env=env,
                timeout=600  # 10 minute timeout
            )
            
            logger.info(f"Deployment completed successfully for branch: {branch}")
            
            return {
                "success": True,
                "branch": branch,
                "output": result["stdout"],
                "error": result["stderr"]
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"Deployment timed out for branch: {branch}")
            return {
                "success": False,
                "branch": branch,
                "error": "Deployment timed out after 10 minutes"
            }
        except Exception as e:
            logger.error(f"Deployment failed for branch {branch}: {e}", exc_info=True)
            return {
                "success": False,
                "branch": branch,
                "error": str(e)
            }
    
    async def _run_command(
        self,
        command: str,
        env: Optional[Dict[str, str]] = None,
        timeout: int = 300
    ) -> Dict[str, str]:
        """
        Run a shell command asynchronously.
        
        Args:
            command: Command to run
            env: Environment variables
            timeout: Command timeout in seconds
            
        Returns:
            Dict with stdout and stderr
        """
        logger.debug(f"Running command: {command}")
        
        # Merge with current environment
        import os
        full_env = os.environ.copy()
        if env:
            full_env.update(env)
        
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=full_env
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                stdout_msg = stdout.decode() if stdout else ""
                logger.error(f"Command failed with exit code {process.returncode}")
                logger.error(f"STDOUT: {stdout_msg[-500:]}")  # Last 500 chars
                logger.error(f"STDERR: {error_msg[-500:]}")  # Last 500 chars
                raise subprocess.CalledProcessError(
                    process.returncode,
                    command,
                    output=stdout,
                    stderr=stderr
                )
            
            return {
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else ""
            }
            
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise subprocess.TimeoutExpired(command, timeout)
    
    async def get_deployment_status(self) -> Dict[str, Any]:
        """
        Get current deployment status from EC2.
        
        Returns:
            Dict with deployment status information
        """
        try:
            # Check if gunicorn is running
            result = await self._run_command(
                f"ssh -i {self.ssh_key_path} {self.ec2_user}@{self.ec2_host} 'pgrep -f gunicorn'",
                timeout=30
            )
            
            is_running = bool(result["stdout"].strip())
            
            # Get last deployment time from git
            git_result = await self._run_command(
                f"ssh -i {self.ssh_key_path} {self.ec2_user}@{self.ec2_host} "
                f"'cd /opt/nomadic-influence/backend && git log -1 --format=\"%H|%an|%ar|%s\"'",
                timeout=30
            )
            
            if git_result["stdout"]:
                commit_hash, author, time_ago, message = git_result["stdout"].strip().split("|", 3)
                
                return {
                    "is_running": is_running,
                    "last_commit": {
                        "hash": commit_hash[:8],
                        "author": author,
                        "time_ago": time_ago,
                        "message": message
                    }
                }
            
            return {"is_running": is_running}
            
        except Exception as e:
            logger.error(f"Error getting deployment status: {e}", exc_info=True)
            return {"error": str(e)}
