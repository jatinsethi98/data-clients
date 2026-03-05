"""Send WhatsApp messages on macOS via deep links and optional UI automation."""

from __future__ import annotations

import re
import subprocess
import time
from urllib.parse import quote

from data_clients.exceptions import WhatsAppSendError


def _normalize_recipient(recipient: str) -> str:
    """Normalize a recipient into digits expected by WhatsApp deep links."""
    value = recipient.strip()
    if not value:
        raise WhatsAppSendError("Recipient is required.")

    # Accept JID-like values from local DB (e.g. 15551234567@s.whatsapp.net).
    if "@" in value:
        value = value.split("@", 1)[0]

    digits = re.sub(r"\D", "", value)
    if not digits:
        raise WhatsAppSendError(
            f"Invalid recipient '{recipient}'. Provide a phone number with country code."
        )
    return digits


def _open_url(url: str, timeout: int = 20) -> None:
    """Open a URL in the default handler (WhatsApp on this machine)."""
    try:
        result = subprocess.run(
            ["open", url],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as e:
        raise WhatsAppSendError("open command not found — this feature requires macOS.") from e
    except subprocess.TimeoutExpired as e:
        raise WhatsAppSendError(f"Timed out opening WhatsApp URL after {timeout}s.") from e

    if result.returncode != 0:
        raise WhatsAppSendError(
            f"Failed to open WhatsApp deep link: {result.stderr.strip()}"
        )


def _run_applescript(script: str, timeout: int = 15) -> None:
    """Run AppleScript via osascript."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as e:
        raise WhatsAppSendError("osascript not found — this feature requires macOS.") from e
    except subprocess.TimeoutExpired as e:
        raise WhatsAppSendError(f"AppleScript timed out after {timeout}s.") from e

    if result.returncode != 0:
        raise WhatsAppSendError(
            "Failed to auto-send via UI automation. "
            "Grant Accessibility permissions to your terminal and WhatsApp."
        )


def compose_message(recipient: str, text: str) -> str:
    """Open WhatsApp compose UI with a prefilled message."""
    phone = _normalize_recipient(recipient)
    encoded = quote(text, safe="")
    url = f"https://api.whatsapp.com/send?phone={phone}&text={encoded}"
    _open_url(url)
    return f"Opened WhatsApp compose for {phone}."


def send_message(
    recipient: str,
    text: str,
    auto_send: bool = False,
    launch_delay_seconds: float = 1.5,
) -> bool:
    """Compose a WhatsApp message and optionally auto-press send."""
    compose_message(recipient=recipient, text=text)

    if not auto_send:
        return True

    # Allow app/webview to focus before pressing Enter.
    time.sleep(max(0.0, launch_delay_seconds))

    _run_applescript(
        """
        tell application "WhatsApp" to activate
        tell application "System Events"
            keystroke return
        end tell
        """
    )
    return True

