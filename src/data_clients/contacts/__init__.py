"""macOS Contacts integration (requires pyobjc)."""

from data_clients.contacts.reader import ContactsReader, Contact, normalize_phone, normalize_email

__all__ = [
    "ContactsReader",
    "Contact",
    "normalize_phone",
    "normalize_email",
]
