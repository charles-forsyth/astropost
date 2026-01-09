from unittest.mock import patch
from astropost.client import GmailClient


def test_create_html_wrapper_alignment():
    """
    Verify that the HTML wrapper does not center the content (no margin: 0 auto).
    """
    with patch("astropost.client.GmailClient._get_credentials"):
        with patch("astropost.client.build"):
            client = GmailClient("token.json", "creds.json")

            content = "<p>Hello</p>"
            wrapper = client._create_html_wrapper(content)

            # Check that margin: 0 auto is NOT present
            assert "margin: 0 auto" not in wrapper
            # Check that content is present
            assert content in wrapper
            # Check that it's left aligned (default) or explicitly set if we decide to add that.
            # For now, just ensuring the centering style is gone is enough.
