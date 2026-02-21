"""Gmail API client — Jarvis Gmail class, migrated from oauth2client to google-auth."""

from __future__ import annotations

import base64
from email.mime.audio import MIMEAudio
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import html as html_module
import logging
import math
import mimetypes
import os
import re
import threading
import time
from typing import List, Optional

from bs4 import BeautifulSoup
import dateutil.parser as parser
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from data_clients.gmail import label
from data_clients.gmail.attachment import Attachment
from data_clients.gmail.label import Label
from data_clients.gmail.message import Message

logger = logging.getLogger(__name__)


class Gmail:
    """The Gmail class which serves as the entrypoint for the Gmail service API.

    Migrated from oauth2client to google-auth. Accepts
    google.oauth2.credentials.Credentials directly via ``_creds``.

    Args:
        client_secret_file: Path to the client secrets JSON (for interactive
            OAuth flows via google-auth-oauthlib).
        creds_file: Path where the token JSON is persisted.
        access_type: 'online' or 'offline'.
        _creds: Pre-built google.oauth2.credentials.Credentials. When
            supplied, ``client_secret_file`` and ``creds_file`` are ignored.
    """

    _SCOPES = [
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/gmail.settings.basic',
    ]

    def __init__(
        self,
        client_secret_file: str = 'credentials.json',
        creds_file: str = 'token.json',
        access_type: str = 'offline',
        _creds=None,
    ) -> None:
        self.client_secret_file = client_secret_file
        self.creds_file = creds_file

        if _creds is not None:
            self.creds = _creds
        else:
            self.creds = self._load_or_authorize(access_type)

        self._service = build(
            'gmail', 'v1', credentials=self.creds,
            cache_discovery=False,
        )

    def _load_or_authorize(self, access_type: str):
        """Load credentials from disk or run interactive OAuth flow."""
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        import json

        creds = None
        if os.path.exists(self.creds_file):
            creds = Credentials.from_authorized_user_file(
                self.creds_file, self._SCOPES
            )

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(self.creds_file, 'w') as f:
                f.write(creds.to_json())

        if not creds or not creds.valid:
            if not os.path.exists(self.client_secret_file):
                raise FileNotFoundError(
                    f"Client secret file '{self.client_secret_file}' not found. "
                    "Download it from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                self.client_secret_file, self._SCOPES,
            )
            creds = flow.run_local_server(port=0)
            with open(self.creds_file, 'w') as f:
                f.write(creds.to_json())

        return creds

    @property
    def service(self) -> 'googleapiclient.discovery.Resource':
        if self.creds.expired and self.creds.refresh_token:
            from google.auth.transport.requests import Request
            self.creds.refresh(Request())
        return self._service

    # -------------------------------------------------------------------------
    # Sending
    # -------------------------------------------------------------------------

    def send_message(
        self,
        sender: str,
        to: str,
        subject: str = '',
        msg_html: Optional[str] = None,
        msg_plain: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        signature: bool = False,
        user_id: str = 'me',
    ) -> Message:
        """Send an email."""
        msg = self._create_message(
            sender, to, subject, msg_html, msg_plain, cc=cc, bcc=bcc,
            attachments=attachments, signature=signature, user_id=user_id,
        )
        try:
            req = self.service.users().messages().send(userId='me', body=msg)
            res = req.execute()
            return self._build_message_from_ref(user_id, res, 'reference')
        except HttpError as error:
            raise error

    # -------------------------------------------------------------------------
    # Convenience getters
    # -------------------------------------------------------------------------

    def get_unread_inbox(
        self,
        user_id: str = 'me',
        labels: Optional[List[Label]] = None,
        query: str = '',
        attachments: str = 'reference',
    ) -> List[Message]:
        if labels is None:
            labels = []
        labels.append(label.INBOX)
        return self.get_unread_messages(user_id, labels, query, attachments)

    def get_starred_messages(
        self, user_id='me', labels=None, query='',
        attachments='reference', include_spam_trash=False,
    ) -> List[Message]:
        if labels is None:
            labels = []
        labels.append(label.STARRED)
        return self.get_messages(user_id, labels, query, attachments, include_spam_trash)

    def get_important_messages(
        self, user_id='me', labels=None, query='',
        attachments='reference', include_spam_trash=False,
    ) -> List[Message]:
        if labels is None:
            labels = []
        labels.append(label.IMPORTANT)
        return self.get_messages(user_id, labels, query, attachments, include_spam_trash)

    def get_unread_messages(
        self, user_id='me', labels=None, query='',
        attachments='reference', include_spam_trash=False,
    ) -> List[Message]:
        if labels is None:
            labels = []
        labels.append(label.UNREAD)
        return self.get_messages(user_id, labels, query, attachments, include_spam_trash)

    def get_drafts(
        self, user_id='me', labels=None, query='',
        attachments='reference', include_spam_trash=False,
    ) -> List[Message]:
        if labels is None:
            labels = []
        labels.append(label.DRAFT)
        return self.get_messages(user_id, labels, query, attachments, include_spam_trash)

    def get_sent_messages(
        self, user_id='me', labels=None, query='',
        attachments='reference', include_spam_trash=False,
    ) -> List[Message]:
        if labels is None:
            labels = []
        labels.append(label.SENT)
        return self.get_messages(user_id, labels, query, attachments, include_spam_trash)

    def get_trash_messages(
        self, user_id='me', labels=None, query='',
        attachments='reference',
    ) -> List[Message]:
        if labels is None:
            labels = []
        labels.append(label.TRASH)
        return self.get_messages(user_id, labels, query, attachments, True)

    def get_spam_messages(
        self, user_id='me', labels=None, query='',
        attachments='reference',
    ) -> List[Message]:
        if labels is None:
            labels = []
        labels.append(label.SPAM)
        return self.get_messages(user_id, labels, query, attachments, True)

    # -------------------------------------------------------------------------
    # Core message retrieval
    # -------------------------------------------------------------------------

    def get_messages(
        self,
        user_id: str = 'me',
        labels: Optional[List[Label]] = None,
        query: str = '',
        attachments: str = 'reference',
        include_spam_trash: bool = False,
    ) -> List[Message]:
        """Get messages from your account."""
        if labels is None:
            labels = []

        labels_ids = [
            lbl.id if isinstance(lbl, Label) else lbl for lbl in labels
        ]

        try:
            response = self.service.users().messages().list(
                userId=user_id,
                q=query,
                labelIds=labels_ids,
                includeSpamTrash=include_spam_trash,
            ).execute()

            message_refs = []
            if 'messages' in response:
                message_refs.extend(response['messages'])

            while 'nextPageToken' in response:
                page_token = response['nextPageToken']
                response = self.service.users().messages().list(
                    userId=user_id,
                    q=query,
                    labelIds=labels_ids,
                    includeSpamTrash=include_spam_trash,
                    pageToken=page_token,
                ).execute()
                message_refs.extend(response.get('messages', []))

            return self._get_messages_from_refs(user_id, message_refs, attachments)

        except HttpError as error:
            raise error

    # -------------------------------------------------------------------------
    # Labels
    # -------------------------------------------------------------------------

    def list_labels(self, user_id: str = 'me') -> List[Label]:
        try:
            res = self.service.users().labels().list(userId=user_id).execute()
        except HttpError as error:
            raise error
        else:
            return [Label(name=x['name'], id=x['id']) for x in res['labels']]

    def create_label(self, name: str, user_id: str = 'me') -> Label:
        body = {"name": name}
        try:
            res = self.service.users().labels().create(
                userId=user_id, body=body,
            ).execute()
        except HttpError as error:
            raise error
        else:
            return Label(res['name'], res['id'])

    def delete_label(self, lbl: Label, user_id: str = 'me') -> None:
        try:
            self.service.users().labels().delete(
                userId=user_id, id=lbl.id,
            ).execute()
        except HttpError as error:
            raise error

    # -------------------------------------------------------------------------
    # Parallel message download
    # -------------------------------------------------------------------------

    def _get_messages_from_refs(
        self,
        user_id: str,
        message_refs: List[dict],
        attachments: str = 'reference',
        parallel: bool = True,
    ) -> List[Message]:
        if not message_refs:
            return []

        if not parallel:
            return [
                self._build_message_from_ref(user_id, ref, attachments)
                for ref in message_refs
            ]

        max_num_threads = 12
        target_msgs_per_thread = 10
        num_threads = min(
            math.ceil(len(message_refs) / target_msgs_per_thread),
            max_num_threads,
        )
        batch_size = math.ceil(len(message_refs) / num_threads)
        message_lists: list[list[Message] | None] = [None] * num_threads

        def thread_download_batch(thread_num):
            gmail = Gmail(_creds=self.creds)
            start = thread_num * batch_size
            end = min(len(message_refs), (thread_num + 1) * batch_size)
            message_lists[thread_num] = [
                gmail._build_message_from_ref(user_id, message_refs[i], attachments)
                for i in range(start, end)
            ]
            gmail.service.close()

        threads = [
            threading.Thread(target=thread_download_batch, args=(i,))
            for i in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        return sum((lst for lst in message_lists if lst is not None), [])

    # -------------------------------------------------------------------------
    # Build Message from API response
    # -------------------------------------------------------------------------

    def _build_message_from_ref(
        self,
        user_id: str,
        message_ref: dict,
        attachments: str = 'reference',
    ) -> Message:
        try:
            message = self.service.users().messages().get(
                userId=user_id, id=message_ref['id'],
            ).execute()
        except HttpError as error:
            raise error

        msg_id = message['id']
        thread_id = message['threadId']
        label_ids = []
        if 'labelIds' in message:
            user_labels = {x.id: x for x in self.list_labels(user_id=user_id)}
            label_ids = [user_labels[x] for x in message['labelIds']]
        snippet = html_module.unescape(message['snippet'])

        payload = message['payload']
        headers = payload['headers']

        date = ''
        sender = ''
        recipient = ''
        subject = ''
        msg_hdrs = {}
        cc = []
        bcc = []
        for hdr in headers:
            if hdr['name'].lower() == 'date':
                try:
                    date = str(parser.parse(hdr['value']).astimezone())
                except Exception:
                    date = hdr['value']
            elif hdr['name'].lower() == 'from':
                sender = hdr['value']
            elif hdr['name'].lower() == 'to':
                recipient = hdr['value']
            elif hdr['name'].lower() == 'subject':
                subject = hdr['value']
            elif hdr['name'].lower() == 'cc':
                cc = hdr['value'].split(', ')
            elif hdr['name'].lower() == 'bcc':
                bcc = hdr['value'].split(', ')
            msg_hdrs[hdr['name']] = hdr['value']

        parts = self._evaluate_message_payload(
            payload, user_id, message_ref['id'], attachments,
        )

        plain_msg = None
        html_msg = None
        attms = []
        for part in parts:
            if part['part_type'] == 'plain':
                if plain_msg is None:
                    plain_msg = part['body']
                else:
                    plain_msg += '\n' + part['body']
            elif part['part_type'] == 'html':
                if html_msg is None:
                    html_msg = part['body']
                else:
                    html_msg += '<br/>' + part['body']
            elif part['part_type'] == 'attachment':
                attm = Attachment(
                    self.service, user_id, msg_id,
                    part['attachment_id'], part['filename'],
                    part['filetype'], part['data'],
                )
                attms.append(attm)

        return Message(
            self.service, self.creds, user_id, msg_id, thread_id,
            recipient, sender, subject, date, snippet,
            plain_msg, html_msg, label_ids, attms, msg_hdrs, cc, bcc,
        )

    def _evaluate_message_payload(
        self,
        payload: dict,
        user_id: str,
        msg_id: str,
        attachments: str = 'reference',
    ) -> List[dict]:
        if 'attachmentId' in payload.get('body', {}):
            if attachments == 'ignore':
                return []

            att_id = payload['body']['attachmentId']
            filename = payload.get('filename') or 'unknown'

            obj = {
                'part_type': 'attachment',
                'filetype': payload['mimeType'],
                'filename': filename,
                'attachment_id': att_id,
                'data': None,
            }

            if attachments == 'reference':
                return [obj]
            else:
                if 'data' in payload['body']:
                    data = payload['body']['data']
                else:
                    res = self.service.users().messages().attachments().get(
                        userId=user_id, messageId=msg_id, id=att_id,
                    ).execute()
                    data = res['data']

                file_data = base64.urlsafe_b64decode(data)
                obj['data'] = file_data
                return [obj]

        elif payload.get('mimeType') == 'text/html':
            data = payload['body'].get('data', '')
            if data:
                data = base64.urlsafe_b64decode(data)
                body = BeautifulSoup(data, 'html.parser', from_encoding='utf-8').body
                return [{'part_type': 'html', 'body': str(body)}]
            return []

        elif payload.get('mimeType') == 'text/plain':
            data = payload['body'].get('data', '')
            if data:
                data = base64.urlsafe_b64decode(data)
                body = data.decode('UTF-8')
                return [{'part_type': 'plain', 'body': body}]
            return []

        elif payload.get('mimeType', '').startswith('multipart'):
            ret = []
            if 'parts' in payload:
                for part in payload['parts']:
                    ret.extend(
                        self._evaluate_message_payload(
                            part, user_id, msg_id, attachments,
                        )
                    )
            return ret

        return []

    # -------------------------------------------------------------------------
    # Create raw MIME message
    # -------------------------------------------------------------------------

    def _create_message(
        self,
        sender: str,
        to: str,
        subject: str = '',
        msg_html: Optional[str] = None,
        msg_plain: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        signature: bool = False,
        user_id: str = 'me',
    ) -> dict:
        msg = MIMEMultipart('mixed' if attachments else 'alternative')
        msg['To'] = to
        msg['From'] = sender
        msg['Subject'] = subject

        if cc:
            msg['Cc'] = ', '.join(cc)
        if bcc:
            msg['Bcc'] = ', '.join(bcc)

        if signature:
            m = re.match(r'.+\s<(?P<addr>.+@.+\..+)>', sender)
            address = m.group('addr') if m else sender
            account_sig = self._get_alias_info(address, user_id)['signature']
            if msg_html is None:
                msg_html = ''
            msg_html += "<br /><br />" + account_sig

        attach_plain = MIMEMultipart('alternative') if attachments else msg
        attach_html = MIMEMultipart('related') if attachments else msg

        if msg_plain:
            attach_plain.attach(MIMEText(msg_plain, 'plain'))
        if msg_html:
            attach_html.attach(MIMEText(msg_html, 'html'))

        if attachments:
            attach_plain.attach(attach_html)
            msg.attach(attach_plain)
            self._ready_message_with_attachments(msg, attachments)

        return {
            'raw': base64.urlsafe_b64encode(msg.as_string().encode()).decode()
        }

    def _ready_message_with_attachments(
        self,
        msg: MIMEMultipart,
        attachments: List[str],
    ) -> None:
        for filepath in attachments:
            content_type, encoding = mimetypes.guess_type(filepath)
            if content_type is None or encoding is not None:
                content_type = 'application/octet-stream'

            main_type, sub_type = content_type.split('/', 1)
            with open(filepath, 'rb') as file:
                raw_data = file.read()

                attm: MIMEBase
                if main_type == 'text':
                    attm = MIMEText(raw_data.decode('UTF-8'), _subtype=sub_type)
                elif main_type == 'image':
                    attm = MIMEImage(raw_data, _subtype=sub_type)
                elif main_type == 'audio':
                    attm = MIMEAudio(raw_data, _subtype=sub_type)
                elif main_type == 'application':
                    attm = MIMEApplication(raw_data, _subtype=sub_type)
                else:
                    attm = MIMEBase(main_type, sub_type)
                    attm.set_payload(raw_data)

            fname = os.path.basename(filepath)
            attm.add_header('Content-Disposition', 'attachment', filename=fname)
            msg.attach(attm)

    def _get_alias_info(self, send_as_email: str, user_id: str = 'me') -> dict:
        req = self.service.users().settings().sendAs().get(
            sendAsEmail=send_as_email, userId=user_id,
        )
        return req.execute()

    # -------------------------------------------------------------------------
    # Bulk / optimized retrieval
    # -------------------------------------------------------------------------

    def get_messages_bulk_optimized(
        self,
        query: str = '',
        max_messages: Optional[int] = None,
        format: str = 'full',
        user_id: str = 'me',
        attachments: str = 'reference',
    ) -> List[Message]:
        """Optimized bulk message retrieval using batch requests."""
        message_refs = self.get_message_ids_optimized(query, max_messages)
        logger.info(f"Found {len(message_refs)} messages to download")
        if not message_refs:
            return []
        return self._get_messages_batch(
            message_refs, format=format, user_id=user_id, attachments=attachments,
        )

    def _get_messages_batch(
        self,
        message_refs: List[dict],
        format: str = 'full',
        user_id: str = 'me',
        attachments: str = 'reference',
        batch_size: int = 25,
        max_retries: int = 3,
    ) -> List[Message]:
        """Batch retrieval with retry logic."""
        all_messages = {}
        batch_size = min(batch_size, 50)
        pending_refs = message_refs.copy()
        retry_count = 0

        while pending_refs and retry_count <= max_retries:
            if retry_count > 0:
                logger.info(
                    f"Retry attempt {retry_count}/{max_retries} "
                    f"for {len(pending_refs)} failed messages"
                )
                time.sleep(min(2 ** retry_count, 30))

            current_total_batches = math.ceil(len(pending_refs) / batch_size)
            failed_refs = []

            for batch_num in range(current_total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(pending_refs))
                batch_refs = pending_refs[start_idx:end_idx]

                logger.info(
                    f"Processing batch {batch_num + 1}/{current_total_batches} "
                    f"({len(batch_refs)} messages)"
                )

                batch_messages = {}
                batch_lock = threading.Lock()
                batch_failed_ids = []

                def batch_callback(request_id, response, exception):
                    idx = int(request_id)
                    ref = batch_refs[idx]
                    msg_id = ref['id']

                    if exception:
                        is_rate_limit = (
                            hasattr(exception, 'resp')
                            and exception.resp.status == 429
                        )
                        if is_rate_limit:
                            logger.warning(
                                f"Rate limit error for message {msg_id}, will retry"
                            )
                        else:
                            logger.error(
                                f"Error in batch request for {msg_id}: {exception}"
                            )
                        with batch_lock:
                            batch_failed_ids.append(ref)
                    else:
                        try:
                            message = self._build_message_from_ref(
                                user_id,
                                {'id': response['id']},
                                attachments=attachments,
                            )
                            with batch_lock:
                                batch_messages[msg_id] = message
                        except Exception as e:
                            logger.error(
                                f"Error building message {msg_id}: {e}"
                            )
                            with batch_lock:
                                batch_failed_ids.append(ref)

                try:
                    batch_request = self.service.new_batch_http_request(
                        callback=batch_callback,
                    )
                    for i, ref in enumerate(batch_refs):
                        request = self.service.users().messages().get(
                            userId=user_id, id=ref['id'], format=format,
                        )
                        batch_request.add(request, request_id=str(i))

                    batch_request.execute()
                    all_messages.update(batch_messages)
                    failed_refs.extend(batch_failed_ids)
                except Exception as e:
                    logger.error(f"Batch request execution failed: {e}")
                    failed_refs.extend(batch_refs)

                if batch_num < current_total_batches - 1:
                    time.sleep(2.0 if batch_failed_ids else 0.5)

            pending_refs = failed_refs
            retry_count += 1

        result_messages = list(all_messages.values())

        if len(result_messages) < len(message_refs):
            missing_refs = [
                ref for ref in message_refs if ref['id'] not in all_messages
            ]
            logger.warning(
                f"Failed to retrieve {len(missing_refs)} messages after "
                f"{max_retries} batch retries. Falling back to sequential..."
            )
            for ref in missing_refs:
                try:
                    message = self._build_message_from_ref(
                        user_id, ref, attachments=attachments,
                    )
                    all_messages[ref['id']] = message
                    result_messages.append(message)
                except Exception as e:
                    logger.error(
                        f"Sequential retrieval also failed for {ref['id']}: {e}"
                    )

        logger.info(
            f"Downloaded {len(result_messages)}/{len(message_refs)} messages total"
        )
        return result_messages

    def get_message_ids_optimized(
        self,
        query: str = '',
        max_results: Optional[int] = None,
        user_id: str = 'me',
        include_spam_trash: bool = False,
    ) -> List[dict]:
        """Efficiently retrieve message IDs with pagination."""
        try:
            all_message_refs = []
            page_token = None

            while True:
                response = self.service.users().messages().list(
                    userId=user_id,
                    q=query,
                    maxResults=500,
                    pageToken=page_token,
                    includeSpamTrash=include_spam_trash,
                ).execute()

                if 'messages' not in response:
                    break

                all_message_refs.extend(response['messages'])

                if max_results and len(all_message_refs) >= max_results:
                    all_message_refs = all_message_refs[:max_results]
                    break

                page_token = response.get('nextPageToken')
                if not page_token:
                    break

            return all_message_refs
        except HttpError as e:
            logger.error(f"Error listing messages: {e}")
            return []

    # -------------------------------------------------------------------------
    # History API
    # -------------------------------------------------------------------------

    def sync_with_history_api(
        self,
        start_history_id: str,
        user_id: str = 'me',
        label_id: Optional[str] = None,
        max_results: Optional[int] = None,
    ) -> tuple[List[dict], List[dict], Optional[str]]:
        """Use History API for incremental sync.

        Returns:
            (added_message_refs, deleted_message_ids, latest_history_id)
        """
        try:
            all_added = []
            all_deleted = []
            page_token = None
            latest_history_id = start_history_id

            while True:
                params = {
                    'userId': user_id,
                    'startHistoryId': start_history_id,
                    'historyTypes': [
                        'messageAdded', 'messageDeleted',
                        'labelAdded', 'labelRemoved',
                    ],
                    'maxResults': 500,
                }
                if label_id:
                    params['labelId'] = label_id
                if page_token:
                    params['pageToken'] = page_token

                response = self.service.users().history().list(**params).execute()

                if 'historyId' in response:
                    latest_history_id = response['historyId']

                if 'history' not in response:
                    logger.info("No new history records - mailbox up to date")
                    break

                for history_record in response['history']:
                    if 'messagesAdded' in history_record:
                        for msg_added in history_record['messagesAdded']:
                            all_added.append(msg_added['message'])
                    if 'messagesDeleted' in history_record:
                        for msg_deleted in history_record['messagesDeleted']:
                            all_deleted.append(msg_deleted['message']['id'])

                if max_results and len(all_added) >= max_results:
                    all_added = all_added[:max_results]
                    break

                page_token = response.get('nextPageToken')
                if not page_token:
                    break

            logger.info(
                f"History sync complete: {len(all_added)} added, "
                f"{len(all_deleted)} deleted, latest history ID: {latest_history_id}"
            )
            return all_added, all_deleted, latest_history_id

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(
                    f"History ID {start_history_id} is too old - full sync required"
                )
                raise
            else:
                logger.error(f"History API error: {e}")
                return [], [], None

    def get_latest_history_id(self, user_id: str = 'me') -> Optional[str]:
        """Get the current history ID for the mailbox."""
        try:
            profile = self.service.users().getProfile(userId=user_id).execute()
            history_id = profile.get('historyId')
            logger.info(f"Current history ID: {history_id}")
            return history_id
        except HttpError as e:
            logger.error(f"Error getting profile: {e}")
            return None
