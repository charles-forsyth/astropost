from unittest.mock import patch
from astropost.main import main


def test_arg_parsing_send():
    with patch("astropost.main.GmailClient") as MockClient:
        with patch(
            "sys.argv",
            [
                "astropost",
                "send",
                "--to",
                "test@example.com",
                "-s",
                "Subject",
                "-b",
                "Body",
            ],
        ):
            main()
            MockClient.return_value.send_email.assert_called_once()
            call_args = MockClient.return_value.send_email.call_args[1]
            assert call_args["recipients"] == ["test@example.com"]
            assert call_args["subject"] == "Subject"
            assert call_args["body"] == "Body"
