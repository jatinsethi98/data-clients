"""Multi-account OAuth2 manager for Gmail API access — decoupled from AppConfig."""

from __future__ import annotations

import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource

from data_clients.exceptions import GmailAuthError


class AuthManager:
    """Manages OAuth2 credentials for multiple Gmail accounts.

    Decoupled from PA's AppConfig — accepts primitives only.

    Args:
        scopes: OAuth2 scopes to request.
        credentials_dir: Directory for storing token files.
        client_secret_file: Path to the client secrets JSON.
    """

    def __init__(
        self,
        scopes: list[str],
        credentials_dir: Path,
        client_secret_file: Path,
    ):
        self.scopes = scopes
        self._credentials_dir = credentials_dir
        self._client_secret = client_secret_file

    def _token_path(self, account_id: str) -> Path:
        return self._credentials_dir / f"token_{account_id}.json"

    def authorize_account(self, account_id: str) -> Credentials:
        """Run interactive OAuth2 flow for a new account. Opens a browser."""
        if not self._client_secret.exists():
            raise GmailAuthError(
                f"Client secret not found at {self._client_secret}. "
                "Download it from Google Cloud Console and place it there."
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(self._client_secret), self.scopes,
        )
        creds = flow.run_local_server(port=0)

        token_path = self._token_path(account_id)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json())

        return creds

    def get_credentials(self, account_id: str) -> Credentials:
        """Load and auto-refresh credentials for an existing account."""
        token_path = self._token_path(account_id)
        if not token_path.exists():
            raise GmailAuthError(
                f"No token found for account '{account_id}'. "
                f"Authorize the account first."
            )

        creds = Credentials.from_authorized_user_file(
            str(token_path), self.scopes,
        )

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json())

        if not creds.valid:
            raise GmailAuthError(
                f"Token for account '{account_id}' is invalid. "
                f"Re-authorize the account."
            )

        return creds

    def get_gmail_service(self, account_id: str) -> Resource:
        """Return an authenticated Gmail API service for the given account."""
        creds = self.get_credentials(account_id)
        return build("gmail", "v1", credentials=creds)

    def remove_token(self, account_id: str) -> bool:
        """Delete the token file for an account. Returns True if deleted."""
        token_path = self._token_path(account_id)
        if token_path.exists():
            token_path.unlink()
            return True
        return False

    def has_token(self, account_id: str) -> bool:
        """Check if a token file exists for the account."""
        return self._token_path(account_id).exists()

    def get_token_info(self, account_id: str) -> dict | None:
        """Return basic token info (without secrets) for display."""
        token_path = self._token_path(account_id)
        if not token_path.exists():
            return None
        try:
            data = json.loads(token_path.read_text())
            return {
                "token_path": str(token_path),
                "has_refresh_token": bool(data.get("refresh_token")),
                "scopes": data.get("scopes", []),
            }
        except (json.JSONDecodeError, OSError):
            return None
