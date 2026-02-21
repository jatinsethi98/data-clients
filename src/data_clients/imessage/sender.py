"""Send messages via AppleScript / osascript through Messages.app."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from data_clients.exceptions import IMessageSendError

logger = logging.getLogger(__name__)


def _sanitize_applescript(text: str) -> str:
    """Sanitize a string for safe inclusion in AppleScript double-quoted strings."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _service_type(service: str) -> str:
    """Map service name to AppleScript service type constant."""
    if service.lower() == "sms":
        return "SMS"
    return "iMessage"


def _run_applescript(script: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """Execute an AppleScript via osascript."""
    logger.debug(f"Running AppleScript: {script[:200]}...")
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            logger.error(f"AppleScript failed: {result.stderr.strip()}")
        return result
    except subprocess.TimeoutExpired as e:
        raise IMessageSendError(
            f"AppleScript timed out after {timeout}s"
        ) from e
    except FileNotFoundError as e:
        raise IMessageSendError(
            "osascript not found — this feature requires macOS"
        ) from e


def send_message(
    recipient: str,
    text: str,
    service: str = "iMessage",
) -> bool:
    """Send a message to a phone number or email via Messages.app."""
    safe_text = _sanitize_applescript(text)
    safe_recipient = _sanitize_applescript(recipient)
    svc = _service_type(service)

    script = (
        f'tell application "Messages"\n'
        f'    set targetService to 1st account whose service type = {svc}\n'
        f'    set targetBuddy to participant "{safe_recipient}" of targetService\n'
        f'    send "{safe_text}" to targetBuddy\n'
        f'end tell'
    )

    result = _run_applescript(script)
    if result.returncode == 0:
        logger.info(f"Sent message to {recipient} via {svc}")
        return True

    raise IMessageSendError(
        f"Failed to send message to {recipient}: {result.stderr.strip()}"
    )


def send_to_group(chat_id: str, text: str) -> bool:
    """Send a message to a group chat by its chat identifier."""
    safe_text = _sanitize_applescript(text)
    safe_chat_id = _sanitize_applescript(chat_id)

    script = (
        f'tell application "Messages"\n'
        f'    set targetChat to chat "{safe_chat_id}"\n'
        f'    send "{safe_text}" to targetChat\n'
        f'end tell'
    )

    result = _run_applescript(script)
    if result.returncode == 0:
        logger.info(f"Sent message to group chat {chat_id}")
        return True

    raise IMessageSendError(
        f"Failed to send to group chat {chat_id}: {result.stderr.strip()}"
    )


def send_attachment(
    recipient: str,
    file_path: str,
    service: str = "iMessage",
) -> bool:
    """Send a file attachment to a recipient via Messages.app."""
    path = Path(file_path).resolve()
    if not path.exists():
        raise IMessageSendError(f"File not found: {file_path}")

    safe_recipient = _sanitize_applescript(recipient)
    safe_path = _sanitize_applescript(str(path))
    svc = _service_type(service)

    script = (
        f'tell application "Messages"\n'
        f'    set targetService to 1st account whose service type = {svc}\n'
        f'    set targetBuddy to participant "{safe_recipient}" of targetService\n'
        f'    set theFile to POSIX file "{safe_path}"\n'
        f'    send theFile to targetBuddy\n'
        f'end tell'
    )

    result = _run_applescript(script)
    if result.returncode == 0:
        logger.info(f"Sent attachment {path.name} to {recipient} via {svc}")
        return True

    raise IMessageSendError(
        f"Failed to send attachment to {recipient}: {result.stderr.strip()}"
    )
