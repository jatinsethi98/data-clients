"""Gmail Message model — migrated from oauth2client to google-auth."""

from __future__ import annotations

from typing import List, Optional, Union

from data_clients.gmail.attachment import Attachment
from data_clients.gmail.label import Label
from data_clients.gmail import label
from data_clients.exceptions import GmailError


class Message:
    """The Message class for emails in your Gmail mailbox.

    This class should not be manually constructed.

    Args:
        service: the Gmail service object.
        creds: google.oauth2.credentials.Credentials object.
        user_id: the username of the account the message belongs to.
        msg_id: the message id.
        thread_id: the thread id.
        recipient: who the message was addressed to.
        sender: who the message was sent from.
        subject: the subject line of the message.
        date: the date the message was sent.
        snippet: the snippet line for the message.
        plain: the plaintext contents of the message. Default None.
        html: the HTML contents of the message. Default None.
        label_ids: the ids of labels associated with this message. Default [].
        attachments: a list of attachments for the message. Default [].
        headers: a dict of header values. Default {}
        cc: who the message was cc'd on the message.
        bcc: who the message was bcc'd on the message.
    """

    def __init__(
        self,
        service: 'googleapiclient.discovery.Resource',
        creds,
        user_id: str,
        msg_id: str,
        thread_id: str,
        recipient: str,
        sender: str,
        subject: str,
        date: str,
        snippet,
        plain: Optional[str] = None,
        html: Optional[str] = None,
        label_ids: Optional[List] = None,
        attachments: Optional[List[Attachment]] = None,
        headers: Optional[dict] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> None:
        self._service = service
        self.creds = creds
        self.user_id = user_id
        self.id = msg_id
        self.thread_id = thread_id
        self.recipient = recipient
        self.sender = sender
        self.subject = subject
        self.date = date
        self.snippet = snippet
        self.plain = plain
        self.html = html
        self.label_ids = label_ids or []
        self.attachments = attachments or []
        self.headers = headers or {}
        self.cc = cc or []
        self.bcc = bcc or []

    @property
    def service(self) -> 'googleapiclient.discovery.Resource':
        # Refresh token if expired (google-auth)
        if self.creds.expired and self.creds.refresh_token:
            from google.auth.transport.requests import Request
            self.creds.refresh(Request())
        return self._service

    def __repr__(self) -> str:
        return (
            f'Message(to: {self.recipient}, from: {self.sender}, id: {self.id})'
        )

    def to_markdown(
        self,
        include_headers: bool = False,
        include_attachments: bool = False,
    ) -> str:
        """Convert the message to markdown format."""
        markdown_parts = []

        markdown_parts.append(f"# {self.subject or 'No Subject'}")
        markdown_parts.append("")

        markdown_parts.append("## Message Details")
        markdown_parts.append("")

        metadata = []
        if self.sender:
            metadata.append(f"**From:** {self.sender}")
        if self.recipient:
            metadata.append(f"**To:** {self.recipient}")
        if self.cc:
            metadata.append(f"**CC:** {', '.join(self.cc)}")
        if self.bcc:
            metadata.append(f"**BCC:** {', '.join(self.bcc)}")
        if self.date:
            metadata.append(f"**Date:** {self.date}")
        if self.thread_id:
            metadata.append(f"**Thread ID:** {self.thread_id}")
        if self.id:
            metadata.append(f"**Message ID:** {self.id}")

        if self.label_ids:
            label_names = []
            for lbl in self.label_ids:
                if isinstance(lbl, Label):
                    label_names.append(lbl.name)
                else:
                    label_names.append(str(lbl))
            if label_names:
                metadata.append(f"**Labels:** {', '.join(label_names)}")

        for item in metadata:
            markdown_parts.append(item)
        markdown_parts.append("")

        if include_headers and self.headers:
            markdown_parts.append("## Headers")
            markdown_parts.append("")
            for key, value in self.headers.items():
                markdown_parts.append(f"**{key}:** {value}")
            markdown_parts.append("")

        if self.snippet:
            markdown_parts.append("## Snippet")
            markdown_parts.append("")
            markdown_parts.append(f"*{self.snippet}*")
            markdown_parts.append("")

        markdown_parts.append("## Content")
        markdown_parts.append("")

        if self.html:
            markdown_parts.append("> *HTML content available*")
            markdown_parts.append("")
            markdown_parts.append("```html")
            markdown_parts.append(self.html)
            markdown_parts.append("```")
            markdown_parts.append("")
        elif self.plain:
            markdown_parts.append(self.plain)
            markdown_parts.append("")
        else:
            markdown_parts.append("*No content available*")
            markdown_parts.append("")

        if include_attachments and self.attachments:
            markdown_parts.append("## Attachments")
            markdown_parts.append("")
            for i, attachment in enumerate(self.attachments, 1):
                markdown_parts.append(f"{i}. **{attachment.filename}**")
                if hasattr(attachment, 'filetype') and attachment.filetype:
                    markdown_parts.append(f"   - Type: {attachment.filetype}")
                markdown_parts.append("")

        return "\n".join(markdown_parts)

    def mark_as_read(self) -> None:
        self.remove_label(label.UNREAD)

    def mark_as_unread(self) -> None:
        self.add_label(label.UNREAD)

    def mark_as_spam(self) -> None:
        self.add_label(label.SPAM)

    def mark_as_not_spam(self) -> None:
        self.remove_label(label.SPAM)

    def mark_as_important(self) -> None:
        self.add_label(label.IMPORTANT)

    def mark_as_not_important(self) -> None:
        self.remove_label(label.IMPORTANT)

    def star(self) -> None:
        self.add_label(label.STARRED)

    def unstar(self) -> None:
        self.remove_label(label.STARRED)

    def move_to_inbox(self) -> None:
        self.add_label(label.INBOX)

    def archive(self) -> None:
        self.remove_label(label.INBOX)

    def trash(self) -> None:
        from googleapiclient.errors import HttpError

        try:
            res = self._service.users().messages().trash(
                userId=self.user_id, id=self.id,
            ).execute()
        except HttpError as error:
            raise error
        else:
            if label.TRASH not in res['labelIds']:
                raise GmailError('An error occurred in a call to `trash`.')
            self.label_ids = res['labelIds']

    def untrash(self) -> None:
        from googleapiclient.errors import HttpError

        try:
            res = self._service.users().messages().untrash(
                userId=self.user_id, id=self.id,
            ).execute()
        except HttpError as error:
            raise error
        else:
            if label.TRASH in res['labelIds']:
                raise GmailError('An error occurred in a call to `untrash`.')
            self.label_ids = res['labelIds']

    def move_from_inbox(self, to: Union[Label, str]) -> None:
        self.modify_labels(to, label.INBOX)

    def add_label(self, to_add: Union[Label, str]) -> None:
        self.add_labels([to_add])

    def add_labels(self, to_add: Union[List[Label], List[str]]) -> None:
        self.modify_labels(to_add, [])

    def remove_label(self, to_remove: Union[Label, str]) -> None:
        self.remove_labels([to_remove])

    def remove_labels(self, to_remove: Union[List[Label], List[str]]) -> None:
        self.modify_labels([], to_remove)

    def modify_labels(
        self,
        to_add: Union[Label, str, List[Label], List[str]],
        to_remove: Union[Label, str, List[Label], List[str]],
    ) -> None:
        from googleapiclient.errors import HttpError

        if isinstance(to_add, (Label, str)):
            to_add = [to_add]
        if isinstance(to_remove, (Label, str)):
            to_remove = [to_remove]

        try:
            res = self._service.users().messages().modify(
                userId=self.user_id, id=self.id,
                body=self._create_update_labels(to_add, to_remove)
            ).execute()
        except HttpError as error:
            raise error
        else:
            if not (all(lbl in res['labelIds'] for lbl in to_add)
                    and all(lbl not in res['labelIds'] for lbl in to_remove)):
                raise GmailError('An error occurred while modifying message label.')
            self.label_ids = res['labelIds']

    def _create_update_labels(
        self,
        to_add: Union[List[Label], List[str]] = None,
        to_remove: Union[List[Label], List[str]] = None,
    ) -> dict:
        if to_add is None:
            to_add = []
        if to_remove is None:
            to_remove = []

        return {
            'addLabelIds': [
                lbl.id if isinstance(lbl, Label) else lbl for lbl in to_add
            ],
            'removeLabelIds': [
                lbl.id if isinstance(lbl, Label) else lbl for lbl in to_remove
            ],
        }
