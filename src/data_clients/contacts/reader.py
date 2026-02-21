"""macOS Contacts integration via pyobjc."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from data_clients.exceptions import ContactResolutionError

logger = logging.getLogger(__name__)

try:
    import objc  # noqa: F401
    from Contacts import (
        CNContactStore,
        CNContactFetchRequest,
        CNContactGivenNameKey,
        CNContactFamilyNameKey,
        CNContactOrganizationNameKey,
        CNContactPhoneNumbersKey,
        CNContactEmailAddressesKey,
        CNContactIdentifierKey,
    )
    _PYOBJC_AVAILABLE = True
except ImportError:
    _PYOBJC_AVAILABLE = False


@dataclass
class Contact:
    """A contact record from macOS Contacts."""

    identifier: str
    full_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    organization: str | None = None
    phone_numbers: list[str] = field(default_factory=list)
    email_addresses: list[str] = field(default_factory=list)
    source: str = "macos_contacts"


def normalize_phone(raw: str) -> str:
    """Normalize a phone number to last 10 digits."""
    digits = re.sub(r"\D", "", raw)
    # Strip leading country code (1 for US/CA)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits[-10:] if len(digits) >= 10 else digits


def normalize_email(raw: str) -> str:
    """Normalize an email address."""
    return raw.strip().lower()


class ContactsReader:
    """Read contacts from macOS Contacts.app via CNContactStore."""

    def __init__(self):
        if not _PYOBJC_AVAILABLE:
            raise ImportError(
                "ContactsReader requires macOS and pyobjc-framework-Contacts. "
                "Install with: pip install data-clients[contacts]"
            )

    def fetch_all_contacts(self) -> list[Contact]:
        """Fetch all contacts from macOS Contacts."""
        store = CNContactStore.alloc().init()

        keys_to_fetch = [
            CNContactGivenNameKey,
            CNContactFamilyNameKey,
            CNContactOrganizationNameKey,
            CNContactPhoneNumbersKey,
            CNContactEmailAddressesKey,
            CNContactIdentifierKey,
        ]

        request = CNContactFetchRequest.alloc().initWithKeysToFetch_(keys_to_fetch)
        contacts: list[Contact] = []

        def _handle_contact(contact, stop):
            first = contact.givenName() or ""
            last = contact.familyName() or ""
            full = f"{first} {last}".strip() or None
            org = contact.organizationName() or None

            phones = []
            for phone_value in contact.phoneNumbers():
                number = phone_value.value().stringValue()
                if number:
                    phones.append(number)

            emails = []
            for email_value in contact.emailAddresses():
                email = email_value.value()
                if email:
                    emails.append(str(email))

            contacts.append(
                Contact(
                    identifier=str(contact.identifier()),
                    full_name=full,
                    first_name=first or None,
                    last_name=last or None,
                    organization=org,
                    phone_numbers=phones,
                    email_addresses=emails,
                )
            )

        success, error = store.enumerateContactsWithFetchRequest_error_usingBlock_(
            request, None, _handle_contact
        )

        if not success:
            err_msg = str(error) if error else "Unknown error"
            raise ContactResolutionError(f"Failed to fetch contacts: {err_msg}")

        logger.info(f"Fetched {len(contacts)} contacts from macOS Contacts")
        return contacts

    def build_lookup(self, contacts: list[Contact]) -> dict[str, Contact]:
        """Build a lookup dict mapping normalized phone/email to Contact."""
        lookup: dict[str, Contact] = {}
        for contact in contacts:
            for phone in contact.phone_numbers:
                normalized = normalize_phone(phone)
                if normalized:
                    lookup[normalized] = contact
            for email in contact.email_addresses:
                normalized = normalize_email(email)
                if normalized:
                    lookup[normalized] = contact
        return lookup
