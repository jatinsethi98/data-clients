"""Tests for iMessage sender."""

from unittest.mock import patch, MagicMock
import subprocess

import pytest

from data_clients.imessage.sender import send_message, send_to_group, send_attachment, _sanitize_applescript
from data_clients.exceptions import IMessageSendError


def test_sanitize_applescript():
    assert _sanitize_applescript('hello "world"') == 'hello \\"world\\"'
    assert _sanitize_applescript("back\\slash") == "back\\\\slash"


@patch("data_clients.imessage.sender._run_applescript")
def test_send_message_success(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    result = send_message("+15551234567", "Hello!")
    assert result is True
    mock_run.assert_called_once()


@patch("data_clients.imessage.sender._run_applescript")
def test_send_message_failure(mock_run):
    mock_run.return_value = MagicMock(returncode=1, stderr="error")
    with pytest.raises(IMessageSendError):
        send_message("+15551234567", "Hello!")


@patch("data_clients.imessage.sender._run_applescript")
def test_send_to_group(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    result = send_to_group("chat123", "Hello group!")
    assert result is True


def test_send_attachment_missing_file():
    with pytest.raises(IMessageSendError, match="File not found"):
        send_attachment("+15551234567", "/nonexistent/file.txt")
