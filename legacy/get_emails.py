#!/usr/bin/env python3
"""
This script retrieves a specified number of the latest emails from a user's Gmail inbox.

It uses the Gmail API with OAuth 2.0 for authentication. The first time it runs,
it will open a browser window for the user to authorize access. Subsequent runs
will use the stored credentials in 'token.json'.

Usage:
    python3 get_email.py [number_of_emails]
"""

import os.path
import base64
from email import message_from_bytes

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# To read emails, we need the .readonly scope.
# If you change scopes, you must delete token.json to re-authenticate.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_PATH = "/home/chuck/Scripts/token_read.json"
CREDENTIALS_PATH = "/home/chuck/Scripts/credentials.json"


def get_credentials():
    """
    Gets user credentials from a local file, refreshing them if necessary.
    Initiates the OAuth2 flow if no valid credentials are found.
    """
    creds = None
    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        except ValueError:
            # This can happen if the token file is malformed or has incorrect scopes
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                # Token is revoked or invalid, force re-authentication
                os.remove(TOKEN_PATH)
                return get_credentials()  # Recurse to re-auth
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                print(f"Error: Credentials file not found at {CREDENTIALS_PATH}")
                print(
                    "Please download your credentials from the Google Cloud Console and save it."
                )
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
    return creds


def get_emails(num_emails=10):
    """
    Lists the user's latest emails in their inbox.
    """
    creds = get_credentials()
    if not creds:
        print("Could not retrieve credentials. Exiting.")
        return

    try:
        service = build("gmail", "v1", credentials=creds)

        # Get the list of messages
        results = (
            service.users()
            .messages()
            .list(userId="me", labelIds=["INBOX"], maxResults=num_emails)
            .execute()
        )
        messages = results.get("messages", [])

        if not messages:
            print("No new messages found.")
            return

        print(f"Fetching the latest {len(messages)} emails:")
        print("-" * 30)

        for msg_ref in messages:
            # Get the full message details
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_ref["id"], format="raw")
                .execute()
            )

            # The 'raw' format returns a base64url encoded string
            msg_raw = base64.urlsafe_b64decode(msg["raw"].encode("ASCII"))

            # Parse the raw email into an email message object
            email_message = message_from_bytes(msg_raw)

            # Extract headers
            subject = email_message["subject"]
            sender = email_message["from"]

            print(f"Message ID: {msg_ref['id']}")
            print(f"From: {sender}")
            print(f"Subject: {subject}")
            print("-" * 30)

    except HttpError as error:
        print(f"An error occurred: {error}")
        # Common issue: token scope is insufficient.
        if error.resp.status == 403:
            print(
                "This might be a permissions issue. The script requires 'gmail.readonly' scope."
            )
            print(
                "Try deleting the 'token.json' file and running the script again to re-authorize."
            )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Get the latest emails from your Gmail inbox."
    )
    parser.add_argument(
        "num_emails",
        type=int,
        nargs="?",
        default=5,
        help="The number of emails to retrieve (default: 5).",
    )
    args = parser.parse_args()

    get_emails(args.num_emails)
