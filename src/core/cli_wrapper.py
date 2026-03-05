"""
OpenClaw CLI Wrapper Module

Provides Python interface to OpenClaw CLI commands.
Handles subprocess execution, response parsing, and error handling.
"""

import json
import subprocess
import os
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent execution status"""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentResponse:
    """Standardized agent response"""
    success: bool
    data: Any
    error: Optional[str] = None
    agent_id: str = ""
    timestamp: str = ""


class OpenClawCLI:
    """
    Python wrapper for OpenClaw CLI commands.

    Provides methods for:
    - Running agent turns
    - Managing agents
    - Scheduling cron jobs
    - Sending messages
    - Gateway operations
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.base_timeout = self.config.get("timeout", 30)
        self.retry_attempts = self.config.get("retry_attempts", 3)

    def _run_command(
        self,
        args: List[str],
        timeout: int = 30,
        capture_output: bool = True
    ) -> subprocess.CompletedProcess:
        """Execute OpenClaw CLI command"""
        cmd = ["openclaw"] + args

        logger.debug(f"Executing: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                cwd=self.config.get("workspace", os.getcwd())
            )
            return result
        except subprocess.TimeoutExpired as e:
            logger.error(f"Command timeout: {' '.join(cmd)}")
            raise TimeoutError(f"Command timed out after {timeout}s") from e
        except FileNotFoundError as e:
            logger.error("OpenClaw CLI not found. Please install: npm install -g openclaw@latest")
            raise RuntimeError("OpenClaw CLI not installed") from e
        except Exception as e:
            logger.error(f"Command failed: {e}")
            raise

    @staticmethod
    def _parse_json_output(
        result: subprocess.CompletedProcess,
        fallback: Any
    ) -> Any:
        """Parse command stdout as JSON with a typed fallback."""
        if result.returncode != 0:
            return fallback
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return fallback

    def version(self) -> str:
        """Get OpenClaw version"""
        result = self._run_command(["--version"])
        return result.stdout.strip()

    def health_check(self) -> Dict[str, Any]:
        """Check OpenClaw gateway health"""
        result = self._run_command(["health"])
        return {
            "status": "healthy" if result.returncode == 0 else "unhealthy",
            "output": result.stdout
        }

    def run_agent(
        self,
        message: str,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        thinking: str = "medium",
        local: bool = False,
        deliver: bool = False,
        json_output: bool = False
    ) -> AgentResponse:
        """
        Run a single agent turn with OpenClaw.

        Args:
            message: The prompt/message to send to the agent
            agent_id: Optional specific agent to target
            session_id: Optional session ID for continuity
            thinking: Thinking level (off|minimal|low|medium|high|xhigh)
            local: Use embedded mode
            deliver: Enable delivery
            json_output: Request JSON output

        Returns:
            AgentResponse with parsed results
        """
        args = ["agent"]

        if message:
            args.extend(["--message", message])

        if agent_id:
            args.extend(["--agent", agent_id])

        if session_id:
            args.extend(["--session-id", session_id])

        if thinking:
            args.extend(["--thinking", thinking])

        if local:
            args.append("--local")

        if deliver:
            args.append("--deliver")

        if json_output:
            args.append("--json")

        try:
            result = self._run_command(args, timeout=self.base_timeout * 2)

            if result.returncode == 0:
                # Try to parse JSON response
                try:
                    data = json.loads(result.stdout) if result.stdout else {}
                except json.JSONDecodeError:
                    data = {"text": result.stdout}

                return AgentResponse(
                    success=True,
                    data=data,
                    agent_id=agent_id or "default"
                )
            else:
                return AgentResponse(
                    success=False,
                    error=result.stderr or result.stdout,
                    agent_id=agent_id or "default"
                )

        except Exception as e:
            return AgentResponse(
                success=False,
                error=str(e),
                agent_id=agent_id or "default"
            )

    def send_message(
        self,
        target: str,
        message: str,
        channel: Optional[str] = None
    ) -> bool:
        """Send message via OpenClaw channel"""
        args = ["message", "send", "--target", target, "--message", message]

        if channel:
            args.extend(["--channel", channel])

        result = self._run_command(args)
        return result.returncode == 0

    def list_agents(self) -> List[Dict]:
        """List configured OpenClaw agents"""
        result = self._run_command(["agents", "list"])
        return self._parse_json_output(result, [{"raw": result.stdout}] if result.returncode == 0 else [])

    def add_agent(
        self,
        name: str,
        workspace: Optional[str] = None,
        model: Optional[str] = None
    ) -> bool:
        """Add a new agent"""
        args = ["agents", "add", name]

        if workspace:
            args.extend(["--workspace", workspace])
        if model:
            args.extend(["--model", model])

        result = self._run_command(args)
        return result.returncode == 0

    def bind_agent(
        self,
        agent_id: str,
        channel: str,
        account: Optional[str] = None
    ) -> bool:
        """Bind agent to channel"""
        args = ["agents", "bind", "--agent", agent_id, "--bind", channel]

        if account:
            args[args.index("--bind") + 1] = f"{channel}:{account}"

        result = self._run_command(args)
        return result.returncode == 0

    def cron_add(
        self,
        name: str,
        message: str,
        schedule: str,
        enabled: bool = True
    ) -> bool:
        """Add cron job"""
        args = [
            "cron", "add",
            "--name", name,
            "--message", message,
            "--at", schedule
        ]

        result = self._run_command(args)

        if result.returncode == 0 and enabled:
            # Enable the job
            # Need to parse job ID from output
            return True
        return result.returncode == 0

    def cron_list(self) -> List[Dict]:
        """List scheduled cron jobs"""
        result = self._run_command(["cron", "list"])
        return self._parse_json_output(result, [])

    def gateway_status(self) -> Dict[str, Any]:
        """Get gateway status"""
        result = self._run_command(["gateway", "status"])

        return {
            "running": result.returncode == 0,
            "output": result.stdout
        }

    def gateway_start(self, port: int = 18789) -> bool:
        """Start gateway"""
        args = ["gateway", "start", "--port", str(port)]
        result = self._run_command(args)
        return result.returncode == 0

    def gateway_stop(self) -> bool:
        """Stop gateway"""
        result = self._run_command(["gateway", "stop"])
        return result.returncode == 0

    def memory_search(self, query: str) -> List[str]:
        """Search memory"""
        args = ["memory", "search", query]
        result = self._run_command(args)

        if result.returncode == 0:
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return []

    def logs(self, limit: int = 100, follow: bool = False) -> str:
        """Get logs"""
        args = ["logs"]

        if limit:
            args.extend(["--limit", str(limit)])
        if follow:
            args.append("--follow")

        result = self._run_command(args, timeout=5 if not follow else 60)
        return result.stdout

    def security_audit(self, deep: bool = False, fix: bool = False) -> Dict:
        """Run security audit"""
        args = ["security", "audit"]

        if deep:
            args.append("--deep")
        if fix:
            args.append("--fix")

        result = self._run_command(args)

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }


class FileProtocol:
    """
    File-based communication protocol for agent coordination.

    Implements inbox/outbox pattern for async agent communication.
    """

    def __init__(
        self,
        inbox_dir: str = "data/inbox",
        outbox_dir: str = "data/outbox",
        comms_dir: str = "data/inter_agent_comms"
    ):
        self.inbox_dir = Path(inbox_dir)
        self.outbox_dir = Path(outbox_dir)
        self.comms_dir = Path(comms_dir)

        # Ensure directories exist
        for directory in [self.inbox_dir, self.outbox_dir, self.comms_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def create_task(
        self,
        task_id: str,
        task_type: str,
        payload: Dict[str, Any]
    ) -> Path:
        """Create task file in inbox"""
        task_file = self.inbox_dir / f"{task_id}_task.json"

        task_data = {
            "task_id": task_id,
            "type": task_type,
            "payload": payload,
            "status": "pending",
            "created_at": self._timestamp()
        }

        with open(task_file, "w") as f:
            json.dump(task_data, f, indent=2)

        logger.info(f"Created task: {task_id}")
        return task_file

    def create_proposal(
        self,
        task_id: str,
        agent_id: str,
        proposal: Dict[str, Any]
    ) -> Path:
        """Create proposal file in comms directory"""
        proposal_file = self.comms_dir / f"{task_id}_proposal.json"

        proposal_data = {
            "task_id": task_id,
            "agent_id": agent_id,
            "proposal": proposal,
            "timestamp": self._timestamp()
        }

        with open(proposal_file, "w") as f:
            json.dump(proposal_data, f, indent=2)

        logger.info(f"Created proposal from {agent_id} for task {task_id}")
        return proposal_file

    def create_result(
        self,
        task_id: str,
        result: Dict[str, Any]
    ) -> Path:
        """Create result file in outbox"""
        result_file = self.outbox_dir / f"{task_id}_result.json"

        result_data = {
            "task_id": task_id,
            "result": result,
            "timestamp": self._timestamp()
        }

        with open(result_file, "w") as f:
            json.dump(result_data, f, indent=2)

        logger.info(f"Created result for task {task_id}")
        return result_file

    def update_status(self, agent_id: str, status: Dict) -> Path:
        """Update agent status file"""
        status_file = self.comms_dir / f"{agent_id}_status.json"

        status_data = {
            "agent_id": agent_id,
            "status": status,
            "updated_at": self._timestamp()
        }

        with open(status_file, "w") as f:
            json.dump(status_data, f, indent=2)

        return status_file

    def read_task(self, task_id: str) -> Optional[Dict]:
        """Read task from inbox"""
        task_file = self.inbox_dir / f"{task_id}_task.json"

        if task_file.exists():
            with open(task_file) as f:
                return json.load(f)
        return None

    def read_proposals(self, task_id: str) -> List[Dict]:
        """Read all proposals for a task"""
        proposals = []

        # Look for proposal files
        for file in self.comms_dir.glob(f"{task_id}_proposal*.json"):
            with open(file) as f:
                proposals.append(json.load(f))

        return proposals

    def mark_completed(self, task_id: str) -> None:
        """Mark task as completed"""
        task_file = self.inbox_dir / f"{task_id}_task.json"

        if task_file.exists():
            with open(task_file) as f:
                task_data = json.load(f)

            task_data["status"] = "completed"
            task_data["completed_at"] = self._timestamp()

            with open(task_file, "w") as f:
                json.dump(task_data, f, indent=2)

    def get_pending_tasks(self) -> List[Dict]:
        """Get all pending tasks"""
        tasks = []

        for file in self.inbox_dir.glob("*_task.json"):
            with open(file) as f:
                task_data = json.load(f)
                if task_data.get("status") == "pending":
                    tasks.append(task_data)

        return tasks

    @staticmethod
    def _timestamp() -> str:
        """Generate ISO timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"


# Convenience function
def create_swarm_client(config: Dict = None) -> tuple:
    """
    Create OpenClaw CLI client and file protocol handler.

    Returns:
        Tuple of (OpenClawCLI, FileProtocol)
    """
    cli = OpenClawCLI(config)
    protocol = FileProtocol()

    return cli, protocol
