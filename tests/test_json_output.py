import json
from unittest.mock import MagicMock, patch
from astropost.main import cmd_list, cmd_show
from astropost.models import Email


def test_list_json(capsys):
    mock_email = Email(
        id="123",
        threadId="t123",
        sender="test@example.com",
        subject="Test Subject",
        date="2023-01-01",
        snippet="Snippet",
        body="Body",
    )

    with patch("astropost.main.get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_emails.return_value = [mock_email]

        args = MagicMock()
        args.count = 5
        args.json = True

        cmd_list(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert isinstance(output, list)
        assert len(output) == 1
        assert output[0]["id"] == "123"
        assert output[0]["from"] == "test@example.com"


def test_show_json(capsys):
    mock_email = Email(
        id="123",
        threadId="t123",
        sender="test@example.com",
        subject="Test Subject",
        date="2023-01-01",
        snippet="Snippet",
        body="Body",
    )

    with patch("astropost.main.get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_email_details.return_value = mock_email

        args = MagicMock()
        args.id = "123"
        args.json = True

        cmd_show(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert isinstance(output, dict)
        assert output["id"] == "123"
        assert output["from"] == "test@example.com"
