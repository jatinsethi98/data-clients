"""Look up macOS Contacts via AppleScript."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass

from data_clients.exceptions import IMessageError

logger = logging.getLogger(__name__)


@dataclass
class ContactResult:
    name: str
    phones: list[str]
    emails: list[str]


def search_contacts(query: str, limit: int = 5) -> list[ContactResult]:
    """Search macOS Contacts.app by name and return phone numbers + emails.

    Args:
        query: Name or partial name to search for.
        limit: Max results to return.

    Returns:
        List of ContactResult with name, phone numbers, and emails.
    """
    safe_query = query.replace("\\", "\\\\").replace('"', '\\"')

    script = f'''
tell application "Contacts"
    set matchedPeople to (every person whose name contains "{safe_query}")
    set maxCount to {limit}
    set counter to 0
    set output to ""
    repeat with p in matchedPeople
        if counter >= maxCount then exit repeat
        set pName to name of p
        set pPhones to ""
        repeat with ph in phones of p
            set pPhones to pPhones & value of ph & "|"
        end repeat
        set pEmails to ""
        repeat with em in emails of p
            set pEmails to pEmails & value of em & "|"
        end repeat
        set output to output & pName & "\\t" & pPhones & "\\t" & pEmails & "\\n"
        set counter to counter + 1
    end repeat
    return output
end tell
'''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except subprocess.TimeoutExpired as e:
        raise IMessageError("Contacts lookup timed out") from e
    except FileNotFoundError as e:
        raise IMessageError("osascript not found — requires macOS") from e

    if result.returncode != 0:
        logger.warning(f"Contacts lookup failed: {result.stderr.strip()}")
        return []

    contacts: list[ContactResult] = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        name = parts[0].strip()
        phones = [p.strip() for p in parts[1].split("|") if p.strip()] if len(parts) > 1 else []
        emails = [e.strip() for e in parts[2].split("|") if e.strip()] if len(parts) > 2 else []
        if name:
            contacts.append(ContactResult(name=name, phones=phones, emails=emails))

    return contacts
