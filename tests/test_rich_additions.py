from unittest.mock import patch, MagicMock
from astropost.main import main


def test_drafts_list():
    with patch("astropost.main.GmailClient") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.list_drafts.return_value = []
        with patch("sys.argv", ["astropost", "drafts", "list", "5"]):
            main()
            mock_instance.list_drafts.assert_called_once_with(max_results=5)


def test_drafts_create():
    with patch("astropost.main.GmailClient") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.create_draft.return_value = "draft_123"
        with patch(
            "sys.argv",
            [
                "astropost",
                "drafts",
                "create",
                "--to",
                "test@example.com",
                "-s",
                "Sub",
                "-b",
                "Body",
            ],
        ):
            main()
            mock_instance.create_draft.assert_called_once_with(
                recipients=["test@example.com"],
                subject="Sub",
                body="Body",
                cc=None,
                bcc=None,
                attachments=None,
                from_address="Charles Forsyth <forsythc@ucr.edu>",
            )


def test_drafts_send():
    with patch("astropost.main.GmailClient") as MockClient:
        mock_instance = MockClient.return_value
        mock_details = MagicMock()
        mock_details.sender = "test@example.com"
        mock_details.subject = "Test Draft Subject"
        mock_details.body = "Test Draft Body"
        mock_instance.list_drafts.return_value = [
            {"id": "draft_123", "message_id": "msg_123", "details": mock_details}
        ]
        mock_instance.send_draft.return_value = "msg_sent"
        with patch("astropost.main.Confirm.ask", return_value=True):
            with patch("sys.argv", ["astropost", "drafts", "send", "draft_123"]):
                main()
                mock_instance.send_draft.assert_called_once_with("draft_123")


def test_labels_list():
    with patch("astropost.main.GmailClient") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.list_labels.return_value = []
        with patch("sys.argv", ["astropost", "labels", "list"]):
            main()
            mock_instance.list_labels.assert_called_once()


def test_labels_create():
    with patch("astropost.main.GmailClient") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.create_label.return_value = "label_123"
        with patch("sys.argv", ["astropost", "labels", "create", "CustomLabel"]):
            main()
            mock_instance.create_label.assert_called_once_with("CustomLabel")


def test_labels_add():
    with patch("astropost.main.GmailClient") as MockClient:
        mock_instance = MockClient.return_value
        with patch(
            "sys.argv", ["astropost", "labels", "add", "msg_123", "CustomLabel"]
        ):
            main()
            mock_instance.add_label_to_email.assert_called_once_with(
                "msg_123", "CustomLabel"
            )


def test_labels_remove():
    with patch("astropost.main.GmailClient") as MockClient:
        mock_instance = MockClient.return_value
        with patch(
            "sys.argv", ["astropost", "labels", "remove", "msg_123", "CustomLabel"]
        ):
            main()
            mock_instance.remove_label_from_email.assert_called_once_with(
                "msg_123", "CustomLabel"
            )


def test_attachments_download():
    with patch("astropost.main.GmailClient") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.download_attachments.return_value = ["/path/to/file.txt"]
        with patch(
            "sys.argv",
            ["astropost", "attachments", "download", "msg_123", "-o", "/output"],
        ):
            main()
            mock_instance.download_attachments.assert_called_once_with(
                "msg_123", output_dir="/output"
            )


def test_thread_show():
    with patch("astropost.main.GmailClient") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.get_thread_details.return_value = []
        with patch("sys.argv", ["astropost", "thread", "show", "thread_123"]):
            main()
            mock_instance.get_thread_details.assert_called_once_with("thread_123")
